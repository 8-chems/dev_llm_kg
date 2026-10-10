from typing import Any
from fastapi import APIRouter, Request
from pydantic import BaseModel
from src.app.flags.store import FlagStore

router = APIRouter(prefix="/v1/admin", tags=["admin"])


class FlagUpdateRequest(BaseModel):
    decision: str
    mode: str
    tau: float


@router.get("/flags")
async def get_flags(request: Request) -> dict[str, Any]:
    """Get current decision mode & threshold configuration."""
    flag_store: FlagStore = request.app.state.flag_store
    return flag_store.get_all_flags()


@router.put("/flags")
async def update_flag(
    payload: FlagUpdateRequest, request: Request
) -> dict[str, Any]:
    """Update decision mode & threshold configuration dynamically."""
    flag_store: FlagStore = request.app.state.flag_store
    updated = flag_store.set_flag(
        decision=payload.decision, mode=payload.mode, tau=payload.tau
    )
    return updated.model_dump()
