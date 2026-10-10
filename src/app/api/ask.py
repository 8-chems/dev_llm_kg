from fastapi import APIRouter, HTTPException, Depends, Request
from src.app.api.security import validate_token
from src.app.models.ask import AskRequest, AskResponse
from src.app.models.trace import Trace
from src.app.pipeline.orchestrator import Orchestrator

router = APIRouter(prefix="/v1", tags=["ask"])

# In-memory request trace cache for trace retrieval API
trace_cache: dict[str, Trace] = {}


def get_orchestrator(request: Request) -> Orchestrator:
    return request.app.state.orchestrator


@router.post("/ask", response_model=AskResponse, dependencies=[Depends(validate_token)])
async def ask_question(
    req: AskRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> AskResponse:
    """Submit a question to the GraphRAG pipeline."""
    try:
        res = await orchestrator.ask(req)
        trace_cache[res.request_id] = res.trace
        return res
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Internal pipeline error: {str(e)}"
        )


@router.get("/trace/{request_id}", response_model=Trace)
async def get_trace(request_id: str) -> Trace:
    """Retrieve detailed execution trace by request_id."""
    if request_id not in trace_cache:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace_cache[request_id]
