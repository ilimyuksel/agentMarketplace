"""Aggregator router for all REST endpoints under /api/v1."""

from fastapi import APIRouter

from backend.api.rest.agents import router as agents_router
from backend.api.rest.jobs import router as jobs_router
from backend.api.rest.ledger import router as ledger_router
from backend.api.rest.system import router as system_router
from backend.api.rest.wallets import router as wallets_router

rest_router = APIRouter(prefix="/api/v1")
rest_router.include_router(system_router)
rest_router.include_router(jobs_router)
rest_router.include_router(agents_router)
rest_router.include_router(ledger_router)
rest_router.include_router(wallets_router)

__all__ = ["rest_router"]
