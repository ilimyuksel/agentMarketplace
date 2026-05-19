"""Job endpoints.

Notes:
    - POST /jobs fires `orchestrator.run_job` via `asyncio.create_task`
      wrapped in a safe-runner that logs exceptions. The HTTP response
      returns immediately with `job_id` + `websocket_url`; the client
      subscribes to /ws/jobs/{job_id} for live progress.
    - `refund_amount` and `pm_profit_realized` aren't persisted on the
      Job row — they're computed at read time from the ledger so the
      values reflect actual cash movement.
"""

from __future__ import annotations

import asyncio
import uuid
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import desc, func, select

from backend.api.rest.envelope import envelope
from backend.constants import DEMO_USER_ID
from backend.core.database import session_scope
from backend.core.event_bus import get_event_bus
from backend.core.logger import get_logger
from backend.enums.budget_tier import BudgetTier, determine_budget_tier
from backend.enums.job_state import JobState
from backend.enums.task_state import TaskState
from backend.enums.transaction_type import TransactionType
from backend.exceptions import BudgetTooLowError, JobNotFoundError
from backend.models.orm.bid import Bid
from backend.models.orm.event import Event
from backend.models.orm.job import Job
from backend.models.orm.job_output import JobOutput
from backend.models.orm.judge_evaluation import JudgeEvaluation
from backend.models.orm.task import Task
from backend.models.orm.transaction import Transaction
from backend.models.schemas.rest import (
    BidSummary,
    JobCreatedResponse,
    JobCreateRequest,
    JobDetailResponse,
    JobEventsResponse,
    JobListItem,
    JobListResponse,
    JobOutputResponse,
    JobTasksResponse,
    JudgeEvalResponse,
    TaskDetailResponse,
    TaskSummary,
)
from backend.orchestrator.pipeline import run_job

logger = get_logger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


_REFUND_NOTE_COMPLETED = (
    "Per spec §7.8: refund equals whatever remained in escrow after "
    "manager funding (i.e., budget − manager_bid_amount)."
)
_REFUND_NOTE_FAILED = (
    "Per spec §7.8 (Phase 9 deviation, worker-protecting): refund equals "
    "80% of the unspent escrow remainder, not 80% of the original budget. "
    "Already-released milestone payments are not clawed back from worker wallets."
)
_REFUND_NOTE_NONE = "No refund applicable for this state."


# ---------------------------------------------------------------------------
# Background-task safety wrapper
# ---------------------------------------------------------------------------


async def _safe_run_job(job_id: str) -> None:
    try:
        await run_job(job_id=job_id, event_bus=get_event_bus())
    except Exception:
        logger.exception("api.background.run_job_failed", job_id=job_id)


# ---------------------------------------------------------------------------
# POST /jobs
# ---------------------------------------------------------------------------


@router.post("")
async def create_job(payload: JobCreateRequest):
    if payload.budget <= Decimal("0.00"):
        raise BudgetTooLowError(
            f"budget must be positive, got {payload.budget}",
            details={"budget": str(payload.budget)},
        )

    user_id = payload.user_id or DEMO_USER_ID
    job_id = f"job_{uuid.uuid4().hex[:16]}"
    tier = determine_budget_tier(float(payload.budget))

    async with session_scope() as session:
        session.add(
            Job(
                id=job_id,
                user_id=user_id,
                user_prompt=payload.prompt,
                budget=payload.budget,
                state=JobState.CREATED.value,
                budget_tier=tier.value,
            )
        )

    # Fire-and-forget background orchestration. The client subscribes to
    # /ws/jobs/{job_id} for live updates rather than polling.
    asyncio.create_task(_safe_run_job(job_id))

    return envelope(
        JobCreatedResponse(
            job_id=job_id,
            state=JobState.CREATED.value,
            budget=payload.budget,
            budget_tier=tier.value,
            websocket_url=f"/ws/jobs/{job_id}",
            estimated_duration_seconds=180,
        ),
        status_code=202,  # accepted; orchestration runs asynchronously
    )


# ---------------------------------------------------------------------------
# GET /jobs (list)
# ---------------------------------------------------------------------------


@router.get("")
async def list_jobs(limit: int = Query(default=20, ge=1, le=100)):
    async with session_scope() as session:
        rows = (
            await session.execute(
                select(Job).order_by(desc(Job.created_at)).limit(limit)
            )
        ).scalars().all()
    items = [JobListItem.model_validate(j) for j in rows]
    return envelope(JobListResponse(jobs=items, count=len(items)))


# ---------------------------------------------------------------------------
# GET /jobs/{id}
# ---------------------------------------------------------------------------


def _refund_note_for(state: str) -> str:
    if state == JobState.COMPLETED.value:
        return _REFUND_NOTE_COMPLETED
    if state == JobState.FAILED.value:
        return _REFUND_NOTE_FAILED
    return _REFUND_NOTE_NONE


async def _compute_refund_amount(job_id: str, session) -> Decimal:
    stmt = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
        Transaction.job_id == job_id,
        Transaction.transaction_type == TransactionType.REFUND.value,
    )
    return Decimal(str((await session.execute(stmt)).scalar() or 0))


async def _compute_pm_profit(job: Job, session) -> Decimal:
    """Per-job PM net = accepted_bid − (milestones + judge fees)."""
    if job.manager_bid_amount is None:
        return Decimal("0.00")
    stmt = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
        Transaction.job_id == job.id,
        Transaction.transaction_type.in_(
            [
                TransactionType.MILESTONE_RELEASE.value,
                TransactionType.JUDGE_FEE.value,
            ]
        ),
    )
    spent = Decimal(str((await session.execute(stmt)).scalar() or 0))
    return (job.manager_bid_amount - spent).quantize(Decimal("0.01"))


@router.get("/{job_id}")
async def get_job(job_id: str):
    async with session_scope() as session:
        job = await session.get(Job, job_id)
        if job is None:
            raise JobNotFoundError(f"job not found: {job_id}")
        tasks = (
            await session.execute(
                select(Task).where(Task.job_id == job_id).order_by(Task.created_at.asc())
            )
        ).scalars().all()
        refund = await _compute_refund_amount(job_id, session)
        pm_profit = await _compute_pm_profit(job, session)

    return envelope(
        JobDetailResponse(
            job_id=job.id,
            user_id=job.user_id,
            user_prompt=job.user_prompt,
            budget=job.budget,
            budget_tier=job.budget_tier,
            state=job.state,
            assigned_manager_id=job.assigned_manager_id,
            manager_bid_amount=job.manager_bid_amount,
            manager_profit_margin=float(job.manager_profit_margin)
            if job.manager_profit_margin is not None
            else None,
            escrow_wallet_id=job.escrow_wallet_id,
            final_output_id=job.final_output_id,
            failure_reason=job.failure_reason,
            pm_profit_realized=pm_profit,
            refund_amount=refund,
            refund_explanation=_refund_note_for(job.state),
            sub_tasks=[TaskSummary.model_validate(t) for t in tasks],
            created_at=job.created_at,
            completed_at=job.completed_at,
        )
    )


# ---------------------------------------------------------------------------
# GET /jobs/{id}/output
# ---------------------------------------------------------------------------


@router.get("/{job_id}/output")
async def get_job_output(job_id: str):
    async with session_scope() as session:
        # Confirm the job exists (gives a tighter 404 message than just "no output").
        job = await session.get(Job, job_id)
        if job is None:
            raise JobNotFoundError(f"job not found: {job_id}")
        output = (
            await session.execute(
                select(JobOutput).where(JobOutput.job_id == job_id).limit(1)
            )
        ).scalars().first()
    if output is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "OUTPUT_NOT_READY", "message": "Job has no aggregated output yet."},
        )

    fallback = (
        bool(output.content.get("fallback_html_used"))
        if isinstance(output.content, dict)
        else False
    )
    by_skill = (
        list(output.content.get("by_skill", {}).keys())
        if isinstance(output.content, dict)
        else []
    )
    return envelope(
        JobOutputResponse(
            output_id=output.id,
            job_id=output.job_id,
            output_type=output.output_type,
            html_artifact=output.html_artifact or "",
            contributing_agents=list(output.contributing_agents or []),
            total_cost=output.total_cost or Decimal("0.00"),
            fallback_html_used=fallback,
            by_skill_keys=by_skill,
            created_at=output.created_at,
        )
    )


# ---------------------------------------------------------------------------
# GET /jobs/{id}/tasks  (detailed: bids + evaluations)
# ---------------------------------------------------------------------------


@router.get("/{job_id}/tasks")
async def get_job_tasks(job_id: str):
    async with session_scope() as session:
        job = await session.get(Job, job_id)
        if job is None:
            raise JobNotFoundError(f"job not found: {job_id}")
        tasks = (
            await session.execute(
                select(Task).where(Task.job_id == job_id).order_by(Task.created_at.asc())
            )
        ).scalars().all()
        result_tasks: list[TaskDetailResponse] = []
        for t in tasks:
            bids = (
                await session.execute(
                    select(Bid).where(Bid.task_id == t.id).order_by(Bid.submitted_at.asc())
                )
            ).scalars().all()
            evals = (
                await session.execute(
                    select(JudgeEvaluation)
                    .where(JudgeEvaluation.task_id == t.id)
                    .order_by(JudgeEvaluation.created_at.asc())
                )
            ).scalars().all()
            detail = TaskDetailResponse(
                id=t.id,
                job_id=t.job_id,
                title=t.title,
                description=t.description,
                required_skills=list(t.required_skills or []),
                budget=t.budget,
                final_cost=t.final_cost,
                state=t.state,
                assigned_agent_id=t.assigned_agent_id,
                judge_verdict=t.judge_verdict,
                judge_score=float(t.judge_score) if t.judge_score is not None else None,
                judge_feedback=t.judge_feedback,
                revision_count=int(t.revision_count or 0),
                dependencies=list(t.dependencies or []),
                output_json=t.output_json,
                created_at=t.created_at,
                started_at=t.started_at,
                completed_at=t.completed_at,
                bids=[BidSummary.model_validate(b) for b in bids],
                evaluations=[JudgeEvalResponse.model_validate(e) for e in evals],
            )
            result_tasks.append(detail)
    return envelope(JobTasksResponse(job_id=job_id, tasks=result_tasks))


# ---------------------------------------------------------------------------
# GET /jobs/{id}/events
# ---------------------------------------------------------------------------


@router.get("/{job_id}/events")
async def get_job_events(
    job_id: str,
    limit: int = Query(default=200, ge=1, le=1000),
    since_event_id: int | None = Query(default=None, ge=0),
):
    async with session_scope() as session:
        job = await session.get(Job, job_id)
        if job is None:
            raise JobNotFoundError(f"job not found: {job_id}")
        stmt = select(Event).where(Event.job_id == job_id)
        if since_event_id is not None:
            stmt = stmt.where(Event.id > since_event_id)
        stmt = stmt.order_by(Event.id.asc()).limit(limit)
        events = (await session.execute(stmt)).scalars().all()
    return envelope(
        JobEventsResponse(
            job_id=job_id,
            events=[
                {
                    "id": e.id,
                    "event_type": e.event_type,
                    "job_id": e.job_id,
                    "task_id": e.task_id,
                    "payload": e.payload,
                    "created_at": e.created_at,
                }
                for e in events
            ],
            count=len(events),
        )
    )
