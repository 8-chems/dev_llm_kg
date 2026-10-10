from pydantic import BaseModel


class NodeRecord(BaseModel):
    node_id: str
    name: str
    labels: list[str]
    summary: str = ""
    degree: int = 0


class EdgeRecord(BaseModel):
    cid: str
    from_id: str
    to_id: str
    rel: str
    target_name: str
    target_labels: list[str]
    confidence: float = 1.0
    degree: int = 0
