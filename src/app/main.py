from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.app.config import Settings
from src.app.obs.logging import setup_logging
from src.app.obs.tracing import setup_tracing
from src.app.clients.breaker import Breaker
from src.app.clients.jev import JevClient
from src.app.clients.graph import GraphClient
from src.app.clients.llm import LLMClient
from src.app.flags.store import FlagStore
from src.app.review.store import ReviewStore
from src.app.review.queue import ReviewQueue
from src.app.obs.decision_log import DecisionLogger
from src.app.pipeline.orchestrator import Orchestrator
from src.app.api.ask import router as ask_router
from src.app.api.review import router as review_router
from src.app.api.admin import router as admin_router
from src.app.api.health import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize settings and observability
    settings = Settings()
    setup_logging(env=settings.env)
    setup_tracing(env=settings.env)
    
    # Log startup event
    import json
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Application started", extra={"event": "startup", "level": "INFO"})

    # Initialize resilience & clients
    breaker = Breaker()
    jev_client = JevClient(settings, breaker)
    graph_client = GraphClient(settings)
    llm_client = LLMClient(settings)

    # Initialize stores & logging
    flag_store = FlagStore(settings)
    review_store = ReviewStore()
    review_queue = ReviewQueue(settings, review_store)
    decision_logger = DecisionLogger(settings)

    # Initialize pipeline orchestrator
    orchestrator = Orchestrator(
        settings=settings,
        jev=jev_client,
        graph=graph_client,
        llm=llm_client,
        flags=flag_store,
        review_queue=review_queue,
        decision_logger=decision_logger,
    )

    # Store in app state for dependencies
    app.state.settings = settings
    app.state.jev_client = jev_client
    app.state.graph_client = graph_client
    app.state.llm_client = llm_client
    app.state.flag_store = flag_store
    app.state.review_store = review_store
    app.state.review_queue = review_queue
    app.state.orchestrator = orchestrator

    yield

    # Cleanup connections
    await graph_client.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Jev + LLM + Neo4j GraphRAG Service",
        version="0.1.0",
        description="Production GraphRAG pipeline using Jev for bounded decisions, LLM for text, and Python code policy.",
        lifespan=lifespan,
    )

    app.include_router(ask_router)
    app.include_router(review_router)
    app.include_router(admin_router)
    app.include_router(health_router)

    return app


app = create_app()
