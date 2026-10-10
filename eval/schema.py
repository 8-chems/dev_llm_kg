from typing import Literal
from pydantic import BaseModel


class GoldItem(BaseModel):
    id: str
    question: str
    lang: Literal["fr", "en"]
    type: Literal[
        "lookup",
        "1hop",
        "2hop",
        "3hop",
        "unanswerable",
        "ambiguous",
        "adversarial",
    ]
    gold_start_id: str | None = None  # None for unanswerable
    gold_path: list[tuple[str, str, str]] = []  # (from_id, rel, to_id)
    gold_answer: str | None = None
    split: Literal["dev", "test"]
    notes: str = ""
