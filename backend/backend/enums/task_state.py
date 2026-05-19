"""Task lifecycle states (11 total). See spec §6."""

from __future__ import annotations

from enum import StrEnum


class TaskState(StrEnum):
    PENDING = "PENDING"
    READY = "READY"
    BIDDING = "BIDDING"
    ASSIGNED = "ASSIGNED"
    RUNNING = "RUNNING"
    DONE = "DONE"
    VERIFYING = "VERIFYING"
    VERIFIED = "VERIFIED"
    PAID = "PAID"
    REVISION = "REVISION"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


TERMINAL_TASK_STATES: frozenset[TaskState] = frozenset(
    {TaskState.PAID, TaskState.FAILED}
)
