"""Job lifecycle states. See spec §6 + Phase 9 ESCROW_LOCK addition.

Spec §6 originally listed 7 active states + CANCELLED. Phase 9 added an
explicit ESCROW_LOCK state between CREATED and MANAGER_BIDDING so the
demo UI can show "locking escrow…" as a distinct phase (one extra DB
write, no behavioral change).

`REJECTED` is retained for back-compat with `refund_service.calculate_refund`
and the spec §7.8 refund branches, but the Phase 9 orchestrator routes
"PM declined low budget" through FAILED with `reason='pm_rejected'` — see
`backend/orchestrator/pipeline.py`.
"""

from __future__ import annotations

from enum import StrEnum


class JobState(StrEnum):
    CREATED = "CREATED"
    ESCROW_LOCK = "ESCROW_LOCK"
    MANAGER_BIDDING = "MANAGER_BIDDING"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


TERMINAL_JOB_STATES: frozenset[JobState] = frozenset(
    {JobState.COMPLETED, JobState.FAILED, JobState.REJECTED, JobState.CANCELLED}
)
