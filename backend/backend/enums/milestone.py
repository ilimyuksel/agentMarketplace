"""Per-task payment milestones (25 / 25 / 50). See spec §7.5."""

from __future__ import annotations

from enum import StrEnum


class Milestone(StrEnum):
    START = "START"
    MID = "MID"
    COMPLETION = "COMPLETION"
