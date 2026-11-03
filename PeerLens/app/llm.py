import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.config import Settings, get_settings


class LLMError(RuntimeError):
    pass


class LLMClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _headers(self) -> dict[str, str]:
        if not self.settings.llm_api_key:
            raise LLMError("LLM_API_KEY must be configured before using model endpoints.")
        return {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json",
        }

    def _models(self, requested: str | None = None) -> list[str]:
        primary = requested or self.settings.llm_model
        models = [primary]
        fallback = self.settings.fallback_model
        if fallback and fallback != primary:
            models.append(fallback)
        return models

    async def _post(self, endpoint: str, payload: dict[str, Any], model: str) -> dict[str, Any]:
        headers = self._headers()
        url = f"{self.settings.llm_base_url.rstrip('/')}/{endpoint}"
        last_error: Exception | None = None
        for attempt in range(self.settings.llm_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.settings.llm_timeout_seconds) as client:
                    response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                body = response.json()
                if not isinstance(body, dict):
                    raise LLMError("The model provider returned an invalid response.")
                return body
            except httpx.HTTPStatusError as error:
                last_error = error
                if error.response.status_code < 500 and error.response.status_code != 429:
                    break
            except (httpx.RequestError, json.JSONDecodeError) as error:
                last_error = error
            if attempt < self.settings.llm_retries:
                continue
        raise LLMError(f"Model provider request failed for model {model}.") from last_error

    async def chat(
        self, messages: list[dict[str, str]], requested_model: str | None = None
    ) -> dict[str, Any]:
        last_error: LLMError | None = None
        for model in self._models(requested_model):
            try:
                body = await self._post(
                    "chat/completions",
                    {"model": model, "messages": messages},
                    model,
                )
                choice = body.get("choices", [{}])[0]
                message = choice.get("message", {})
                content = message.get("content")
                if not isinstance(content, str):
                    raise LLMError("The model provider returned no text response.")
                usage = body.get("usage") or {}
                return {
                    "answer": content,
                    "model": body.get("model", model),
                    "input_tokens": int(usage.get("prompt_tokens", 0)),
                    "output_tokens": int(usage.get("completion_tokens", 0)),
                }
            except (LLMError, IndexError, KeyError, TypeError, ValueError) as error:
                last_error = (
                    error
                    if isinstance(error, LLMError)
                    else LLMError("The model provider returned an invalid response.")
                )
        raise last_error or LLMError("No model is configured.")

    async def embeddings(self, texts: list[str]) -> tuple[list[list[float]], dict[str, int]]:
        body = await self._post(
            "embeddings",
            {"model": self.settings.embedding_model, "input": texts},
            self.settings.embedding_model,
        )
        try:
            items = sorted(body["data"], key=lambda item: item["index"])
            vectors = [item["embedding"] for item in items]
            usage = body.get("usage") or {}
            return vectors, {
                "input_tokens": int(usage.get("prompt_tokens", 0)),
                "output_tokens": 0,
            }
        except (IndexError, KeyError, TypeError, ValueError) as error:
            raise LLMError("The model provider returned invalid embeddings.") from error

    async def stream_chat(
        self, messages: list[dict[str, str]], requested_model: str | None = None
    ) -> AsyncIterator[dict[str, Any]]:
        headers = self._headers()
        url = f"{self.settings.llm_base_url.rstrip('/')}/chat/completions"
        last_error: Exception | None = None
        for model in self._models(requested_model):
            for attempt in range(self.settings.llm_retries + 1):
                received_delta = False
                try:
                    async with httpx.AsyncClient(timeout=self.settings.llm_timeout_seconds) as client:
                        async with client.stream(
                            "POST",
                            url,
                            headers=headers,
                            json={
                                "model": model,
                                "messages": messages,
                                "stream": True,
                                "stream_options": {"include_usage": True},
                            },
                        ) as response:
                            response.raise_for_status()
                            async for line in response.aiter_lines():
                                if not line.startswith("data: "):
                                    continue
                                data = line[6:]
                                if data == "[DONE]":
                                    return
                                event = json.loads(data)
                                usage = event.get("usage")
                                if usage:
                                    yield {
                                        "type": "usage",
                                        "model": event.get("model", model),
                                        "input_tokens": int(usage.get("prompt_tokens", 0)),
                                        "output_tokens": int(usage.get("completion_tokens", 0)),
                                    }
                                for choice in event.get("choices", []):
                                    content = choice.get("delta", {}).get("content")
                                    if content:
                                        received_delta = True
                                        yield {"type": "delta", "content": content}
                    return
                except (httpx.RequestError, httpx.HTTPStatusError, json.JSONDecodeError) as error:
                    last_error = error
                    if received_delta:
                        raise LLMError("Model streaming failed after the response began.") from error
                    if isinstance(error, httpx.HTTPStatusError):
                        status = error.response.status_code
                        if status < 500 and status != 429:
                            break
                    if attempt < self.settings.llm_retries:
                        continue
                    break
        raise LLMError("Model streaming failed for all configured models.") from last_error


def estimate_cost(
    settings: Settings,
    request_type: str,
    input_tokens: int,
    output_tokens: int,
) -> float | None:
    if request_type == "embedding":
        rate = settings.embedding_cost_per_1m
        return input_tokens * rate / 1_000_000 if rate is not None else None
    input_rate = settings.llm_input_cost_per_1m
    output_rate = settings.llm_output_cost_per_1m
    if input_rate is None or output_rate is None:
        return None
    return (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000
