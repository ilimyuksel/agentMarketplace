"""FastAPI application entry point.

Run locally with:
    uvicorn backend.main:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.rest import rest_router
from backend.api.rest.errors import register as register_error_handlers
from backend.api.websocket.global_feed import router as global_ws_router
from backend.api.websocket.job_feed import router as job_ws_router
from backend.config import settings
from backend.core.connection_manager import get_connection_manager
from backend.core.database import dispose_engine
from backend.core.event_bus import get_event_bus
from backend.core.event_types import SYSTEM_HEARTBEAT
from backend.core.logger import configure_logging, get_logger
from backend.core.redis_client import close_redis

configure_logging()
logger = get_logger("main")


HEARTBEAT_INTERVAL_SECONDS = 30


async def _heartbeat_loop() -> None:
    """Periodic `system.heartbeat` on the global channel.

    Not persisted — heartbeats are advisory liveness signals only.
    """
    bus = get_event_bus()
    while True:
        try:
            await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)
            await bus.publish(
                SYSTEM_HEARTBEAT,
                {"ts": datetime.now(timezone.utc).isoformat()},
                persist=False,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("heartbeat.failed", error=str(exc)[:200])


@asynccontextmanager
async def lifespan(app: FastAPI):
    bus = get_event_bus()
    cm = get_connection_manager()
    bus.attach_connection_manager(cm)
    heartbeat = asyncio.create_task(_heartbeat_loop(), name="heartbeat")
    logger.info("app.started", port=settings.app_port)
    try:
        yield
    finally:
        heartbeat.cancel()
        try:
            await heartbeat
        except asyncio.CancelledError:
            pass
        await dispose_engine()
        await close_redis()
        logger.info("app.shutdown")


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "AI Agent Marketplace — autonomous agent-to-agent task economy.\n\n"
        "All REST endpoints live under `/api/v1`. Live event feed is on "
        "`/ws/global` and `/ws/jobs/{job_id}`."
    ),
    lifespan=lifespan,
)

# Demo only — auth + tight CORS are explicitly out of scope per §14.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Backwards-compatible un-prefixed /health (kept for Phase 5 contract).
@app.get("/health", include_in_schema=False)
async def root_health() -> dict[str, object]:
    return {
        "status": "ok",
        "app": settings.app_name,
        "model": settings.gemini_model,
        "embedding_model": settings.gemini_embedding_model,
    }


# Central error handlers for the REST surface (returns the §8 envelope).
register_error_handlers(app)

# Routes
app.include_router(rest_router)
app.include_router(global_ws_router)
app.include_router(job_ws_router)
