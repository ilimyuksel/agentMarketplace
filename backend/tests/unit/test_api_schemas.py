"""Phase 10 — REST schema validation + Money serialization."""

from __future__ import annotations

import json
from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.models.schemas.common import Money
from backend.models.schemas.rest import (
    JobCreatedResponse,
    JobCreateRequest,
    JobDetailResponse,
    TaskSummary,
)


# ---------------------------------------------------------------------------
# JobCreateRequest
# ---------------------------------------------------------------------------


def test_job_create_request_accepts_valid_payload():
    req = JobCreateRequest(prompt="Build a landing page", budget=Decimal("200.00"))
    assert req.prompt == "Build a landing page"
    assert req.budget == Decimal("200.00")
    assert req.user_id is None


def test_job_create_request_accepts_numeric_budget():
    """Float / int / string inputs all coerce to Decimal via the Money alias."""
    for value in (200, 200.0, "200", "200.00"):
        req = JobCreateRequest(prompt="x", budget=value)
        assert req.budget == Decimal("200.00")


def test_job_create_request_rejects_zero_budget():
    with pytest.raises(ValidationError):
        JobCreateRequest(prompt="x", budget=Decimal("0"))


def test_job_create_request_rejects_negative_budget():
    with pytest.raises(ValidationError):
        JobCreateRequest(prompt="x", budget=Decimal("-1.00"))


def test_job_create_request_rejects_empty_prompt():
    with pytest.raises(ValidationError):
        JobCreateRequest(prompt="", budget=Decimal("100.00"))


def test_job_create_request_rejects_too_many_decimals():
    """Money enforces `decimal_places=2`."""
    with pytest.raises(ValidationError):
        JobCreateRequest(prompt="x", budget=Decimal("200.123"))


# ---------------------------------------------------------------------------
# Money JSON serialization
# ---------------------------------------------------------------------------


def test_money_json_output_is_a_number_not_a_string():
    """Frontend ergonomics: budget is `200.00`, not `"200.00"`."""
    resp = JobCreatedResponse(
        job_id="job_x",
        state="CREATED",
        budget=Decimal("200.00"),
        budget_tier="STANDARD",
        websocket_url="/ws/jobs/job_x",
        estimated_duration_seconds=180,
    )
    raw = json.loads(resp.model_dump_json())
    assert isinstance(raw["budget"], (int, float)), (
        f"budget should serialize as number, got {type(raw['budget']).__name__}"
    )
    assert raw["budget"] == 200.0


def test_money_python_dict_keeps_decimal():
    """Internal representation (model_dump in python mode) preserves Decimal."""
    resp = JobCreatedResponse(
        job_id="job_x",
        state="CREATED",
        budget=Decimal("200.00"),
        budget_tier="STANDARD",
        websocket_url="/ws/jobs/job_x",
        estimated_duration_seconds=180,
    )
    data = resp.model_dump(mode="python")
    assert isinstance(data["budget"], Decimal)


# ---------------------------------------------------------------------------
# Optional Money fields stay optional
# ---------------------------------------------------------------------------


def test_task_summary_accepts_null_final_cost():
    summary = TaskSummary(
        id="task_x",
        title="t",
        description="d",
        required_skills=["copywriting"],
        budget=Decimal("25.00"),
        state="PENDING",
    )
    assert summary.final_cost is None
    raw = json.loads(summary.model_dump_json())
    assert raw["final_cost"] is None
