from typing import Literal
from pydantic import BaseModel, Field
from src.app.models.decisions import Mode
from src.app.models.trace import Trace


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    max_hops: int = Field(3, ge=1, le=5)
    lang: Literal["fr", "en"] | None = None


class AskResponse(BaseModel):
    request_id: str
    answer: str | None = None
    trace: Trace
    mode: Mode
    pending_review: bool = False
