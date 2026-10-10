from typing import Literal
from pydantic import BaseModel


class FlagConfig(BaseModel):
    decision: str
    mode: Literal["off", "shadow", "live"] = "live"
    tau: float = 0.80


class FlagStoreConfig(BaseModel):
    flags: dict[str, FlagConfig] = {}
