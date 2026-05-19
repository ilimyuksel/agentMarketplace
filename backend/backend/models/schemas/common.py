"""Shared response envelopes and small DTOs. See spec §8."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated, Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

T = TypeVar("T")

# Monetary amount type.
#  * Input  : accepts numbers / strings, validated as a non-negative Decimal
#             with at most 2 decimal places.
#  * Output : `PlainSerializer` converts to `float` for JSON so the API
#             emits `200.00` (a number) instead of `"200.00"` (a string),
#             which is more ergonomic for the frontend without sacrificing
#             internal precision — model fields stay `Decimal`.
Money = Annotated[
    Decimal,
    Field(decimal_places=2, ge=0),
    PlainSerializer(lambda v: float(v), return_type=float, when_used="json"),
]


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class _CamelMixin(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class SuccessEnvelope(BaseModel, Generic[T]):
    success: bool = True
    data: T
    timestamp: str = Field(default_factory=_utcnow_iso)


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorEnvelope(BaseModel):
    success: bool = False
    error: ErrorDetail
    timestamp: str = Field(default_factory=_utcnow_iso)


def response_envelope(data: Any) -> dict[str, Any]:
    """Quick helper for ad-hoc dict-shaped success envelopes."""
    return {
        "success": True,
        "data": data,
        "timestamp": _utcnow_iso(),
    }


class StatsResponse(_CamelMixin):
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    active_jobs: int
    total_agents: int
    active_agents: int
    total_transactions: int
    total_ledger_volume: float
