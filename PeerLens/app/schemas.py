from pydantic import BaseModel, Field, field_validator


def _not_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("must not be blank")
    return value


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)

    _validate_message = field_validator("message")(_not_blank)


class ChatResponse(BaseModel):
    answer: str
    model: str
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float | None


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=5, ge=1, le=10)

    _validate_question = field_validator("question")(_not_blank)


class Citation(BaseModel):
    document: str
    page: int
    heading: str
    similarity: float


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]
    model: str | None
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float | None


class UsageItem(BaseModel):
    request_type: str
    model: str
    requests: int
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float | None


class UsageResponse(BaseModel):
    days: int
    usage: list[UsageItem]
