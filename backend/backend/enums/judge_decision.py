"""QA Judge verdicts. See spec §4 (Agent #6) and §6 (transitions)."""

from __future__ import annotations

from enum import StrEnum


class JudgeDecision(StrEnum):
    APPROVED = "APPROVED"
    REVISION_REQUESTED = "REVISION_REQUESTED"
    REJECTED = "REJECTED"
