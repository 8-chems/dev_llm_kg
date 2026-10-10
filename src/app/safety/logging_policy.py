from typing import Any
from src.app.models.decisions import JevDecision


def sanitize_decision_for_log(
    request_id: str,
    decision: JevDecision,
    mode: str,
    tau: float,
    outcome: str,
) -> dict[str, Any]:
    """Sanitizes decision log entries according to data privacy policies.

    Excludes raw question text, node labels/text, and LLM text output.
    """
    return {
        "request_id": request_id,
        "decision": decision.name,
        "label_id": decision.choice,
        "p": decision.p,
        "probs": decision.probs,
        "model_version": decision.model_version,
        "latency_ms": decision.latency_ms,
        "mode": mode,
        "tau": tau,
        "outcome": outcome,
    }
