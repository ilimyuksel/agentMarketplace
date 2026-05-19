"""System endpoints: /health, /stats."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter
from sqlalchemy import func, select

from backend.api.rest.envelope import envelope
from backend.config import settings
from backend.core.database import session_scope
from backend.enums.job_state import JobState
from backend.models.orm.agent import Agent
from backend.models.orm.job import Job
from backend.models.orm.transaction import Transaction
from backend.models.schemas.rest import HealthResponse, StatsResponse

router = APIRouter(tags=["system"])


@router.get("/health")
async def health():
    return envelope(
        HealthResponse(
            status="ok",
            app=settings.app_name,
            model=settings.gemini_model,
            embedding_model=settings.gemini_embedding_model,
        )
    )


@router.get("/stats")
async def stats():
    async with session_scope() as session:
        total_jobs = int(
            (await session.execute(select(func.count(Job.id)))).scalar_one() or 0
        )
        completed_jobs = int(
            (
                await session.execute(
                    select(func.count(Job.id)).where(Job.state == JobState.COMPLETED.value)
                )
            ).scalar_one()
            or 0
        )
        failed_jobs = int(
            (
                await session.execute(
                    select(func.count(Job.id)).where(Job.state == JobState.FAILED.value)
                )
            ).scalar_one()
            or 0
        )
        active_jobs = int(
            (
                await session.execute(
                    select(func.count(Job.id)).where(
                        Job.state.notin_(
                            [
                                JobState.COMPLETED.value,
                                JobState.FAILED.value,
                                JobState.REJECTED.value,
                                JobState.CANCELLED.value,
                            ]
                        )
                    )
                )
            ).scalar_one()
            or 0
        )
        total_agents = int(
            (await session.execute(select(func.count(Agent.id)))).scalar_one() or 0
        )
        active_agents = int(
            (
                await session.execute(
                    select(func.count(Agent.id)).where(Agent.is_active.is_(True))
                )
            ).scalar_one()
            or 0
        )
        ledger_length = int(
            (await session.execute(select(func.count(Transaction.id)))).scalar_one() or 0
        )
        total_volume = (
            await session.execute(select(func.coalesce(func.sum(Transaction.amount), 0)))
        ).scalar_one() or Decimal("0.00")

    return envelope(
        StatsResponse(
            total_jobs=total_jobs,
            completed_jobs=completed_jobs,
            failed_jobs=failed_jobs,
            active_jobs=active_jobs,
            total_agents=total_agents,
            active_agents=active_agents,
            ledger_length=ledger_length,
            total_volume=Decimal(str(total_volume)),
        )
    )
