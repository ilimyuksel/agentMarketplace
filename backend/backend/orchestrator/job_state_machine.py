"""Job-level transition validator + helper.

Mirrors `workflow/state_machine.py` at the job grain. Eight active
states, three terminal:

    CREATED → ESCROW_LOCK → MANAGER_BIDDING → PLANNING → EXECUTING → COMPLETED
       │            │              │              │           │
       └────────────┴──────────────┴──────────────┴───────────┴─→ FAILED
       └──────────  any non-terminal  ──────────────────────────→ CANCELLED

`REJECTED` exists in `JobState` for back-compat with §7.8 refund branches,
but the v1 orchestrator routes "PM declined" through FAILED instead, so
REJECTED is not in the active transition table.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Final

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.logger import get_logger
from backend.enums.job_state import JobState
from backend.exceptions import InvalidStateTransitionError
from backend.models.orm.job import Job

logger = get_logger(__name__)


LEGAL_TRANSITIONS: Final[dict[JobState, frozenset[JobState]]] = {
    JobState.CREATED: frozenset(
        {JobState.ESCROW_LOCK, JobState.FAILED, JobState.CANCELLED}
    ),
    JobState.ESCROW_LOCK: frozenset(
        {JobState.MANAGER_BIDDING, JobState.FAILED, JobState.CANCELLED}
    ),
    JobState.MANAGER_BIDDING: frozenset(
        {JobState.PLANNING, JobState.FAILED, JobState.CANCELLED}
    ),
    JobState.PLANNING: frozenset(
        {JobState.EXECUTING, JobState.FAILED, JobState.CANCELLED}
    ),
    JobState.EXECUTING: frozenset(
        {JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED}
    ),
    JobState.COMPLETED: frozenset(),  # terminal
    JobState.FAILED: frozenset(),  # terminal
    JobState.CANCELLED: frozenset(),  # terminal
    # REJECTED has no outbound; only the legacy refund path inspects it.
    JobState.REJECTED: frozenset(),
}


def is_valid_transition(from_state: JobState, to_state: JobState) -> bool:
    return to_state in LEGAL_TRANSITIONS.get(from_state, frozenset())


async def transition_job(
    *,
    job: Job,
    new_state: JobState,
    session: AsyncSession,
    reason: str | None = None,
) -> JobState:
    """Validate, persist, return prior state.

    Does NOT emit any event — the orchestrator emits the specific
    `job.<verb>` event (per spec §8) at each transition point. Keeping
    state-machine concerns and event-emission concerns separate avoids
    the noise of a generic `job.state_changed` that the spec doesn't list.
    """
    try:
        from_state = JobState(job.state)
    except ValueError as exc:
        raise InvalidStateTransitionError(
            f"job {job.id} has unknown state {job.state!r}"
        ) from exc

    if from_state == new_state:
        return from_state  # idempotent no-op

    if not is_valid_transition(from_state, new_state):
        raise InvalidStateTransitionError(
            f"job {job.id}: illegal transition {from_state.value} → {new_state.value}",
            details={"from": from_state.value, "to": new_state.value},
        )

    job.state = new_state.value
    if new_state in (JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED, JobState.REJECTED):
        if job.completed_at is None:
            job.completed_at = datetime.now(timezone.utc)
    if new_state == JobState.FAILED and reason and not job.failure_reason:
        job.failure_reason = reason
    await session.flush()

    logger.info(
        "job.state_changed",
        job_id=job.id,
        from_state=from_state.value,
        to_state=new_state.value,
        reason=reason,
    )
    return from_state
