from typing import Literal


def gate(
    decision: str,
    label: str | None,
    p: float,
    taus: dict[str, float],
) -> Literal["accept", "escalate"]:
    """Evaluate decision outcome against confidence threshold (tau).

    Rules:
    1. If winning label is None or "none", always escalate.
    2. If tau for decision is missing from configuration, default to escalate.
    3. Accept if p >= tau, otherwise escalate.
    """
    if label in (None, "none"):
        return "escalate"
    if decision not in taus:
        return "escalate"
    tau = taus[decision]
    return "accept" if p >= tau else "escalate"
