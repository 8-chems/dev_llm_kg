from typing import Any
from fastapi import APIRouter, HTTPException, Request, Depends, status
from pydantic import BaseModel
from src.app.review.store import ReviewStore, ReviewTask

router = APIRouter(prefix="/v1/review", tags=["review"])


class ReviewSubmission(BaseModel):
    verdict: str  # node_id or "none"
    note: str | None = None


def get_review_store(request: Request) -> ReviewStore:
    return request.app.state.review_store


@router.get("/tasks", response_model=list[ReviewTask])
async def list_open_tasks(
    status: str = "open",
    review_store: ReviewStore = Depends(get_review_store),
) -> list[ReviewTask]:
    """Retrieve open tasks in human review queue."""
    if status == "open":
        return review_store.get_open_tasks()
    return list(review_store._tasks.values())


@router.post("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def submit_review(
    task_id: str,
    submission: ReviewSubmission,
    review_store: ReviewStore = Depends(get_review_store),
):
    """Submit human review verdict for an escalated task."""
    task = review_store.complete_task(
        task_id=task_id, verdict=submission.verdict, note=submission.note
    )
    if not task:
        raise HTTPException(status_code=404, detail="Review task not found")
    return None
