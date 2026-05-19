"""Bid response models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BidResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_id: str
    agent_id: str
    bid_amount: float
    reasoning: str | None
    confidence: float | None
    estimated_time_seconds: int | None
    scope_assumption: str | None
    is_winner: bool
    selection_score: float | None
    submitted_at: datetime
