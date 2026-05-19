"""Pure formula tests for the composite selection score (§7.3).

The selection function is split so the math is unit-testable without DB
or LLM. We compute the expected value by hand and assert engine output
matches within 1e-4.
"""

from __future__ import annotations

import math

import pytest

from backend.config import settings
from backend.marketplace.selection_engine import (
    compute_composite_score,
    cosine_similarity,
)


def _by_hand(
    skill_similarity: float,
    agent_reputation: float,
    price_score: float,
    confidence: float,
    speed_score: float,
) -> float:
    return (
        settings.weight_skill_similarity * skill_similarity
        + settings.weight_reputation * agent_reputation
        + settings.weight_price * price_score
        + settings.weight_confidence * confidence
        + settings.weight_speed * speed_score
    )


def test_canonical_example_matches_by_hand_within_tolerance():
    """Sample case from the spec example: ContentWriter on a $35 copy task."""
    skill_sim = 0.9
    rep = 0.88
    bid_amount = 33.25
    budget = 35.0
    confidence = 0.92
    eta = 30

    expected_price = 1.0 - (bid_amount / budget) * 0.5
    expected_speed = max(0.0, 1.0 - eta / 60.0)
    expected = _by_hand(skill_sim, rep, expected_price, confidence, expected_speed)

    actual = compute_composite_score(
        skill_similarity=skill_sim,
        agent_reputation=rep,
        bid_amount=bid_amount,
        task_budget=budget,
        confidence=confidence,
        estimated_time_seconds=eta,
    )
    assert math.isclose(actual, expected, rel_tol=0, abs_tol=1e-4)


def test_bid_over_budget_zeros_price_score():
    """Edge case: bid > budget → price_score = 0."""
    actual = compute_composite_score(
        skill_similarity=1.0,
        agent_reputation=1.0,
        bid_amount=100.0,  # >> budget
        task_budget=50.0,
        confidence=1.0,
        estimated_time_seconds=1,
    )
    # No price_score contribution; the other 4 terms are still in play.
    expected_speed = max(0.0, 1.0 - 1 / 60.0)
    expected = _by_hand(1.0, 1.0, 0.0, 1.0, expected_speed)
    assert math.isclose(actual, expected, abs_tol=1e-4)


def test_slow_agent_yields_low_speed_score():
    """estimated_time >= 60s → speed_score == 0."""
    actual = compute_composite_score(
        skill_similarity=0.5,
        agent_reputation=0.5,
        bid_amount=10.0,
        task_budget=20.0,
        confidence=0.5,
        estimated_time_seconds=90,  # past the 60s ceiling
    )
    expected_price = 1.0 - (10.0 / 20.0) * 0.5  # 0.75
    expected = _by_hand(0.5, 0.5, expected_price, 0.5, 0.0)
    assert math.isclose(actual, expected, abs_tol=1e-4)


def test_null_confidence_defaults_to_half():
    """confidence=None → defaults to 0.5 per spec §7.3 prose."""
    actual = compute_composite_score(
        skill_similarity=0.7,
        agent_reputation=0.7,
        bid_amount=10.0,
        task_budget=20.0,
        confidence=None,
        estimated_time_seconds=30,
    )
    expected_price = 1.0 - (10.0 / 20.0) * 0.5
    expected = _by_hand(0.7, 0.7, expected_price, 0.5, 0.5)
    assert math.isclose(actual, expected, abs_tol=1e-4)


def test_null_eta_falls_back_to_60s_floor():
    """estimated_time_seconds=None → speed_score == 0 (treated as 60s)."""
    actual = compute_composite_score(
        skill_similarity=0.5,
        agent_reputation=0.5,
        bid_amount=10.0,
        task_budget=20.0,
        confidence=0.5,
        estimated_time_seconds=None,
    )
    expected_price = 1.0 - (10.0 / 20.0) * 0.5
    expected = _by_hand(0.5, 0.5, expected_price, 0.5, 0.0)
    assert math.isclose(actual, expected, abs_tol=1e-4)


# ---------------------------------------------------------------------------
# Cosine similarity primitive
# ---------------------------------------------------------------------------


def test_cosine_similarity_identical_vectors_is_one():
    assert math.isclose(cosine_similarity([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]), 1.0, abs_tol=1e-9)


def test_cosine_similarity_orthogonal_vectors_is_zero():
    assert math.isclose(cosine_similarity([1.0, 0.0], [0.0, 1.0]), 0.0, abs_tol=1e-9)


def test_cosine_similarity_missing_vector_returns_zero():
    assert cosine_similarity(None, [1.0, 0.0]) == 0.0
    assert cosine_similarity([1.0, 0.0], None) == 0.0
    assert cosine_similarity([], [1.0]) == 0.0


def test_cosine_similarity_zero_vector_returns_zero():
    """Avoid the division-by-zero booby trap."""
    assert cosine_similarity([0.0, 0.0, 0.0], [1.0, 1.0, 1.0]) == 0.0
