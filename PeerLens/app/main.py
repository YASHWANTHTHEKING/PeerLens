import json
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from app.config import Settings, get_settings
from app.llm import LLMClient, LLMError, estimate_cost
from app.schemas import (
    AskRequest,
    AskResponse,
    ChatRequest,
    ChatResponse,
    Citation,
    UsageItem,
    UsageResponse,
)
from app.store import StoreError, log_usage, search_chunks, usage_summary

app = FastAPI(title="Examate RAG starter", version="0.1.0")

SettingsDep = Annotated[Settings, Depends(get_settings)]


@app.get("/health")
def health(settings: SettingsDep) -> dict:
    """Liveness: the process is up. Must be fast and must not call the LLM or the DB."""
    return {"status": "ok", "app": settings.app_name, "environment": settings.environment}


def _log_usage_best_effort(
    request_type: str, model: str, input_tokens: int, output_tokens: int, cost: float | None
) -> None:
    # Usage logging must never break a response that otherwise succeeded.
    try:
        log_usage(request_type, model, input_tokens, output_tokens, cost)
    except StoreError:
        pass


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, settings: SettingsDep) -> ChatResponse:
    client = LLMClient(settings)
    try:
        result = await client.chat([{"role": "user", "content": request.message}])
    except LLMError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    cost = estimate_cost(settings, "chat", result["input_tokens"], result["output_tokens"])
    _log_usage_best_effort("chat", result["model"], result["input_tokens"], result["output_tokens"], cost)

    return ChatResponse(
        answer=result["answer"],
        model=result["model"],
        input_tokens=result["input_tokens"],
        output_tokens=result["output_tokens"],
        estimated_cost_usd=cost,
    )


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest, settings: SettingsDep) -> StreamingResponse:
    if not settings.llm_api_key:
        raise HTTPException(
            status_code=503, detail="LLM_API_KEY must be configured before using model endpoints."
        )
    client = LLMClient(settings)

    async def event_source():
        try:
            async for event in client.stream_chat([{"role": "user", "content": request.message}]):
                if event["type"] == "usage":
                    cost = estimate_cost(settings, "chat", event["input_tokens"], event["output_tokens"])
                    _log_usage_best_effort(
                        "chat", event["model"], event["input_tokens"], event["output_tokens"], cost
                    )
                    event = {**event, "estimated_cost_usd": cost}
                yield f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"
        except LLMError as error:
            yield f"event: error\ndata: {json.dumps({'error': str(error)})}\n\n"

    return StreamingResponse(event_source(), media_type="text/event-stream")


@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest, settings: SettingsDep) -> AskResponse:
    client = LLMClient(settings)
    try:
        [question_embedding], _usage = await client.embeddings([request.question])
        matches = search_chunks(question_embedding, limit=request.top_k)
        context = "\n\n".join(
            f"[{match['source']} p.{match['page']}] {match['content']}" for match in matches
        )
        prompt = (
            "Answer the question using only the excerpts below. "
            "Cite the document and page for each fact you use.\n\n"
            f"{context}\n\nQuestion: {request.question}"
        )
        result = await client.chat([{"role": "user", "content": prompt}])
    except LLMError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except StoreError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    cost = estimate_cost(settings, "chat", result["input_tokens"], result["output_tokens"])
    _log_usage_best_effort("chat", result["model"], result["input_tokens"], result["output_tokens"], cost)

    return AskResponse(
        answer=result["answer"],
        citations=[
            Citation(
                document=match["source"],
                page=match["page"],
                heading=match["heading"],
                similarity=match["similarity"],
            )
            for match in matches
        ],
        model=result["model"],
        input_tokens=result["input_tokens"],
        output_tokens=result["output_tokens"],
        estimated_cost_usd=cost,
    )


@app.get("/usage", response_model=UsageResponse)
def usage(days: int = 30) -> UsageResponse:
    try:
        rows = usage_summary(days)
    except StoreError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return UsageResponse(days=days, usage=[UsageItem(**row) for row in rows])
