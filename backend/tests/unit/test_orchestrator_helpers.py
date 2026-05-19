"""Pure-function helpers used by the orchestrator: budget tier + refund."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from backend.config import settings
from backend.enums.budget_tier import BudgetTier, determine_budget_tier
from backend.enums.job_state import JobState
from backend.orchestrator.pipeline import _residual_after_pm_funding
from backend.payments.refund_service import calculate_refund


# ---------------------------------------------------------------------------
# Budget tier
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "budget,expected",
    [
        (0, BudgetTier.REJECTED),
        (30, BudgetTier.REJECTED),
        (49.99, BudgetTier.REJECTED),
        (50, BudgetTier.MINIMAL),
        (149.99, BudgetTier.MINIMAL),
        (150, BudgetTier.STANDARD),
        (499.99, BudgetTier.STANDARD),
        (500, BudgetTier.PREMIUM),
        (10_000, BudgetTier.PREMIUM),
    ],
)
def test_budget_tier_boundaries(budget, expected):
    assert determine_budget_tier(budget) == expected


# ---------------------------------------------------------------------------
# Refund calculator (spec §7.8)
# ---------------------------------------------------------------------------


def _job_stub(state: JobState, budget: Decimal) -> SimpleNamespace:
    return SimpleNamespace(state=state.value, budget=budget)


def test_refund_rejected_returns_full_budget():
    job = _job_stub(JobState.REJECTED, Decimal("200.00"))
    assert calculate_refund(job=job, total_paid=Decimal("0.00")) == Decimal("200.00")


def test_refund_completed_returns_unused_remainder():
    job = _job_stub(JobState.COMPLETED, Decimal("200.00"))
    assert calculate_refund(job=job, total_paid=Decimal("182.00")) == Decimal("18.00")


def test_refund_completed_clamps_to_zero_when_overspent():
    """Defensive — if total_paid somehow exceeds budget, refund stays 0."""
    job = _job_stub(JobState.COMPLETED, Decimal("100.00"))
    assert calculate_refund(job=job, total_paid=Decimal("200.00")) == Decimal("0.00")


def test_refund_failed_returns_configured_percent_of_budget():
    job = _job_stub(JobState.FAILED, Decimal("200.00"))
    expected = Decimal("200.00") * Decimal(str(settings.refund_failed_pct))
    expected = expected.quantize(Decimal("0.01"))
    assert calculate_refund(job=job, total_paid=Decimal("0.00")) == expected


def test_refund_cancelled_returns_remaining():
    job = _job_stub(JobState.CANCELLED, Decimal("200.00"))
    assert calculate_refund(job=job, total_paid=Decimal("50.00")) == Decimal("150.00")


def test_refund_for_non_terminal_state_is_zero():
    """A job in CREATED / PLANNING / EXECUTING etc. has no refund to issue yet."""
    for state in (JobState.CREATED, JobState.PLANNING, JobState.EXECUTING):
        job = _job_stub(state, Decimal("100.00"))
        assert calculate_refund(job=job, total_paid=Decimal("0.00")) == Decimal("0.00")


# ---------------------------------------------------------------------------
# Pipeline helper
# ---------------------------------------------------------------------------


def test_residual_after_pm_funding_is_two_decimal():
    """budget=$200, accepted_bid=$182 → escrow keeps $18 for refund."""
    assert _residual_after_pm_funding(Decimal("200"), Decimal("182")) == Decimal("18.00")


def test_residual_after_pm_funding_clamps_to_zero():
    """Defensive — PM bid can't exceed budget, but if it did refund stays 0."""
    assert _residual_after_pm_funding(Decimal("100"), Decimal("120")) == Decimal("0.00")
