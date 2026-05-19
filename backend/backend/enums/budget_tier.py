"""Budget tier for incoming jobs. See spec §7.1."""

from __future__ import annotations

from enum import StrEnum

from backend.config import settings


class BudgetTier(StrEnum):
    REJECTED = "REJECTED"
    MINIMAL = "MINIMAL"
    STANDARD = "STANDARD"
    PREMIUM = "PREMIUM"


def determine_budget_tier(budget: float) -> BudgetTier:
    """Map a numeric budget to a tier per spec §7.1."""
    if budget < settings.budget_min:
        return BudgetTier.REJECTED
    if budget < settings.budget_minimal_threshold:
        return BudgetTier.MINIMAL
    if budget < settings.budget_premium_threshold:
        return BudgetTier.STANDARD
    return BudgetTier.PREMIUM
