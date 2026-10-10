import time
from typing import Any
from pydantic import BaseModel


class ReviewTask(BaseModel):
    task_id: str
    request_id: str
    decision: str
    question: str
    options: list[dict[str, Any]]
    status: str = "open"  # "open", "completed"
    verdict: str | None = None
    note: str | None = None
    created_at: float


class ReviewStore:

    def __init__(self):
        self._tasks: dict[str, ReviewTask] = {}

    def create_task(
        self,
        task_id: str,
        request_id: str,
        decision: str,
        question: str,
        options: list[dict[str, Any]],
    ) -> ReviewTask:
        task = ReviewTask(
            task_id=task_id,
            request_id=request_id,
            decision=decision,
            question=question,
            options=options,
            created_at=time.time(),
        )
        self._tasks[task_id] = task
        return task

    def get_open_tasks(self) -> list[ReviewTask]:
        return [t for t in self._tasks.values() if t.status == "open"]

    def complete_task(
        self, task_id: str, verdict: str, note: str | None = None
    ) -> ReviewTask | None:
        task = self._tasks.get(task_id)
        if not task:
            return None
        task.status = "completed"
        task.verdict = verdict
        task.note = note
        return task

    def get_task(self, task_id: str) -> ReviewTask | None:
        return self._tasks.get(task_id)
