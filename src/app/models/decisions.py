from typing import Literal
from pydantic import BaseModel

DecisionName = Literal["resolve", "hop", "goal", "ground", "dedupe"]
Mode = Literal["off", "shadow", "live"]


class JevDecision(BaseModel):
    name: DecisionName
    choice: str | None = None  # winning label (Choice) or None
    p: float  # probability of winning label / noul prob
    probs: dict[str, float] = {}  # full distribution for Choice
    model_version: str
    latency_ms: int


class Candidate(BaseModel):
    cid: str  # opaque id: "c0".."cN" (NOT the node name)
    node_id: str  # Neo4j elementId / id
    name: str
    labels: list[str]
    summary: str = ""


class Hop(BaseModel):
    from_node: str
    rel_type: str
    to_node: str
    decision: JevDecision
    goal_p: float | None = None
