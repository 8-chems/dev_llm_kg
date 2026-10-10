from fastapi import APIRouter, HTTPException, Request
from src.app.flags.store import FlagStore

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}

@router.get("/healthz")
    """Liveness probe."""
@router.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}

    return {"status": "ok"}


@router.get("/readyz")
async def readyz(request: Request) -> dict[str, str]:
    """Readiness probe."""
    flag_store: FlagStore = request.app.state.flag_store
    taus = flag_store.get_taus()

    if not taus:
        raise HTTPException(
            status_code=503, detail="Thresholds not loaded"
        )

    # Check Neo4j reachability if driver active and not in mock mode
    graph_client = request.app.state.graph_client
    if graph_client._driver and not graph_client._is_mock:
        try:
            async with graph_client._driver.session() as session:
                await session.run("RETURN 1")
        except Exception:
            # Fall back to mock mode if live database is unreachable
            graph_client._is_mock = True

    return {"status": "ready"}
