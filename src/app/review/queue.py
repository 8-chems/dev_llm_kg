import uuid
import json
from typing import Any
from src.app.config import Settings
from src.app.review.store import ReviewStore, ReviewTask


class ReviewQueue:

    def __init__(self, settings: Settings, store: ReviewStore):
        self._settings = settings
        self._store = store

    async def enqueue_escalation(
        self,
        request_id: str,
        decision: str,
        question: str,
        options: list[dict[str, Any]],
    ) -> str:
        """Enqueue an escalation task for human review.

        Returns task_id.
        """
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        self._store.create_task(
            task_id=task_id,
            request_id=request_id,
            decision=decision,
            question=question,
            options=options,
        )

        # Attempt Pub/Sub publishing if configured
        try:
            from google.cloud import pubsub_v1

            publisher = pubsub_v1.PublisherClient()
            topic_path = publisher.topic_path(
                self._settings.gcp_project, self._settings.pubsub_topic
            )
            payload = json.dumps(
                {
                    "task_id": task_id,
                    "request_id": request_id,
                    "decision": decision,
                    "question": question,
                }
            ).encode("utf-8")
            publisher.publish(topic_path, payload)
        except Exception:
            pass  # Fallback to local store in dev / non-GCP environment

        return task_id
