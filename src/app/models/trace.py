from typing import Literal
from pydantic import BaseModel
from src.app.models.decisions import Candidate, Hop


class Trace(BaseModel):
    request_id: str
    start: Candidate | None = None
    hops: list[Hop] = []
    min_p: float | None = None
    escalated_to: Literal["none", "llm", "human"] = "none"
    outcome: Literal["accepted", "escalated", "no_answer", "fallback"] = "accepted"
