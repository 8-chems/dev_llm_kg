from typing import Any
from pydantic import BaseModel
from src.app.clients.llm import LLMClient
from src.app.review.queue import ReviewQueue


class EscalationOutcome(BaseModel):
    choice_cid: str | None = None
    escalated_to: str = "none"  # "none", "llm", "human"
    pending_review: bool = False
    task_id: str | None = None


async def handle_escalation(
    request_id: str,
    stage: str,
    question: str,
    options: list[dict[str, Any]],
    llm_client: LLMClient,
    review_queue: ReviewQueue,
) -> EscalationOutcome:
    """Handle low confidence Jev decision by escalating to LLM review, then human queue."""
    # 1. LLM review
    llm_choice = await llm_client.review_escalation(question, options)
    valid_cids = {opt.get("cid") for opt in options}

    if llm_choice in valid_cids and llm_choice != "none":
        return EscalationOutcome(
            choice_cid=llm_choice, escalated_to="llm", pending_review=False
        )

    # 2. Human review queue
    task_id = await review_queue.enqueue_escalation(
        request_id=request_id,
        decision=stage,
        question=question,
        options=options,
    )

    return EscalationOutcome(
        choice_cid=None,
        escalated_to="human",
        pending_review=True,
        task_id=task_id,
    )
