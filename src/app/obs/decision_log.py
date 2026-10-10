import json
import time
from typing import Any
from src.app.config import Settings
from src.app.models.decisions import JevDecision
from src.app.safety.logging_policy import sanitize_decision_for_log


class DecisionLogger:

    def __init__(self, settings: Settings):
        self._settings = settings

    def log_decision(
        self,
        request_id: str,
        decision: JevDecision,
        mode: str,
        tau: float,
        outcome: str,
        escalated_to: str = "none",
    ) -> None:
        record = sanitize_decision_for_log(
            request_id=request_id,
            decision=decision,
            mode=mode,
            tau=tau,
            outcome=outcome,
        )
        record["ts"] = time.time()
        record["escalated_to"] = escalated_to
        record["env"] = self._settings.env
        record["probs"] = json.dumps(decision.probs)

        # In prod, stream to BigQuery
        if self._settings.env == "prod":
            try:
                from google.cloud import bigquery

                client = bigquery.Client(project=self._settings.gcp_project)
                table_id = f"{self._settings.gcp_project}.{self._settings.bq_dataset}.decision_log"
                client.insert_rows_json(table_id, [record])
            except Exception:
                pass
