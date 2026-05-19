"""Task-state transition validator + helper that applies + persists + emits.

Legal transitions encoded from spec §6:

    PENDING   → READY
    READY     → BIDDING
    BIDDING   → ASSIGNED | FAILED
    ASSIGNED  → RUNNING
    RUNNING   → DONE | FAILED
    DONE      → VERIFYING
    VERIFYING → VERIFIED | REVISION | REJECTED
    VERIFIED  → PAID
    REVISION  → RUNNING
    REJECTED  → FAILED
    PAID, FAILED — terminal

`transition_task` enforces these, sets `started_at` / `completed_at`
timestamps where appropriate, and emits `task.state_changed`. Callers
are responsible for emitting any *additional* semantic events (e.g.
`task.execution_started`) at the appropriate moments.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Final

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.event_bus import EventBus
from backend.core.event_types import TASK_STATE_CHANGED
from backend.core.logger import get_logger
from backend.enums.task_state import TaskState
from backend.exceptions import InvalidStateTransitionError
from backend.models.orm.task import Task

logger = get_logger(__name__)


LEGAL_TRANSITIONS: Final[dict[TaskState, frozenset[TaskState]]] = {
    TaskState.PENDING: frozenset({TaskState.READY}),
    TaskState.READY: frozenset({TaskState.BIDDING}),
    TaskState.BIDDING: frozenset({TaskState.ASSIGNED, TaskState.FAILED}),
    TaskState.ASSIGNED: frozenset({TaskState.RUNNING}),
    TaskState.RUNNING: frozenset({TaskState.DONE, TaskState.FAILED}),
    TaskState.DONE: frozenset({TaskState.VERIFYING}),
    TaskState.VERIFYING: frozenset(
        {TaskState.VERIFIED, TaskState.REVISION, TaskState.REJECTED}
    ),
    TaskState.VERIFIED: frozenset({TaskState.PAID}),
    TaskState.REVISION: frozenset({TaskState.RUNNING}),
    TaskState.REJECTED: frozenset({TaskState.FAILED}),
    TaskState.PAID: frozenset(),  # terminal
    TaskState.FAILED: frozenset(),  # terminal
}


def is_valid_transition(from_state: TaskState, to_state: TaskState) -> bool:
    return to_state in LEGAL_TRANSITIONS.get(from_state, frozenset())


async def transition_task(
    *,
    task: Task,
    new_state: TaskState,
    session: AsyncSession,
    event_bus: EventBus,
    reason: str | None = None,
) -> None:
    """Validate, persist, emit. Raises `InvalidStateTransitionError` if illegal."""
    try:
        from_state = TaskState(task.state)
    except ValueError as exc:
        raise InvalidStateTransitionError(
            f"task {task.id} has unknown state {task.state!r}"
        ) from exc

    if from_state == new_state:
        return  # idempotent no-op

    if not is_valid_transition(from_state, new_state):
        raise InvalidStateTransitionError(
            f"task {task.id}: illegal transition {from_state.value} → {new_state.value}",
            details={"from": from_state.value, "to": new_state.value},
        )

    now = datetime.now(timezone.utc)
    task.state = new_state.value
    if new_state == TaskState.RUNNING and task.started_at is None:
        task.started_at = now
    if new_state in (TaskState.PAID, TaskState.FAILED) and task.completed_at is None:
        task.completed_at = now
    if new_state == TaskState.FAILED and reason and not task.judge_feedback:
        # Stash the failure reason somewhere visible to the API layer.
        task.judge_feedback = f"FAILED: {reason}"
    await session.flush()

    await event_bus.publish(
        TASK_STATE_CHANGED,
        {
            "task_id": task.id,
            "from_state": from_state.value,
            "to_state": new_state.value,
            "reason": reason,
        },
        job_id=task.job_id,
        task_id=task.id,
    )

    logger.info(
        "task.state_changed",
        task_id=task.id,
        from_state=from_state.value,
        to_state=new_state.value,
    )
