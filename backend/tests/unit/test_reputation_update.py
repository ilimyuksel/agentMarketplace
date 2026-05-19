"""Reputation lifecycle (§7.7) — delta thresholds, clamping, history row."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import delete, select

from backend.config import settings
from backend.core.database import session_scope
from backend.core.event_bus import EventBus
from backend.marketplace.reputation_service import (
    apply_delta,
    reputation_delta,
    update_reputation,
)
from backend.models.orm.agent import Agent
from backend.models.orm.reputation_history import ReputationHistory


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "judge_score,expected",
    [
        (0.95, settings.rep_delta_excellent),  # +0.02
        (0.85, settings.rep_delta_excellent),  # boundary
        (0.75, settings.rep_delta_approved),   # +0.01
        (0.70, settings.rep_delta_approved),   # boundary
        (0.55, settings.rep_delta_revision),   # -0.01
        (0.50, settings.rep_delta_revision),   # boundary
        (0.30, settings.rep_delta_rejected),   # -0.05
        (0.00, settings.rep_delta_rejected),
    ],
)
def test_reputation_delta_thresholds(judge_score, expected):
    assert reputation_delta(judge_score) == expected


def test_apply_delta_clamps_upper_bound():
    """0.99 + 0.02 should clamp to 0.99, not overshoot to 1.01."""
    delta, new = apply_delta(0.99, judge_score=0.95)
    assert delta == settings.rep_delta_excellent
    assert new == settings.rep_max  # 0.99


def test_apply_delta_clamps_lower_bound():
    """0.11 + (-0.05) should clamp to 0.10, not undershoot to 0.06."""
    delta, new = apply_delta(0.11, judge_score=0.20)
    assert delta == settings.rep_delta_rejected
    assert new == settings.rep_min  # 0.10


# ---------------------------------------------------------------------------
# Full DB-backed flow
# ---------------------------------------------------------------------------


@pytest.fixture
async def restorable_agent():
    """Yield (agent_id, original_reputation). Restore reputation after test
    and delete any reputation_history rows the test produced."""
    agent_id = "MarketResearcher_001"
    async with session_scope() as session:
        agent = await session.get(Agent, agent_id)
        original = agent.reputation
        original_float = float(original)
    yield agent_id, original_float

    # Restore the seeded reputation and remove any rep history added by the test.
    async with session_scope() as session:
        agent = await session.get(Agent, agent_id)
        agent.reputation = original
        await session.execute(
            delete(ReputationHistory).where(ReputationHistory.agent_id == agent_id)
        )


@pytest.mark.asyncio
async def test_update_reputation_persists_history_and_returns_old_new(restorable_agent):
    agent_id, original = restorable_agent
    bus = EventBus()  # no WS attached — events still publish (persist=True default for non-job)
    async with session_scope() as session:
        old, new = await update_reputation(
            session=session,
            event_bus=bus,
            agent_id=agent_id,
            judge_score=0.92,  # excellent → +0.02
        )
    assert abs(old - original) < 1e-6
    assert abs(new - (original + settings.rep_delta_excellent)) < 1e-3

    # Agent row reflects the new value.
    async with session_scope() as session:
        agent = await session.get(Agent, agent_id)
        assert abs(float(agent.reputation) - new) < 1e-3

        rows = (
            await session.execute(
                select(ReputationHistory).where(ReputationHistory.agent_id == agent_id)
            )
        ).scalars().all()

    assert len(rows) == 1
    row = rows[0]
    assert abs(float(row.old_reputation) - original) < 1e-3
    assert abs(float(row.new_reputation) - new) < 1e-3
    assert abs(float(row.delta) - settings.rep_delta_excellent) < 1e-3
    assert abs(float(row.judge_score) - 0.92) < 1e-3
    assert row.reason == "excellent_score"


@pytest.mark.asyncio
async def test_update_reputation_clamps_lower_bound_in_db(restorable_agent):
    """Even if the agent is already near the floor, repeated rejections stop at 0.10."""
    agent_id, original = restorable_agent
    bus = EventBus()
    # Move the agent to just above the floor first.
    async with session_scope() as session:
        agent = await session.get(Agent, agent_id)
        agent.reputation = Decimal("0.12")

    async with session_scope() as session:
        # rejected delta is -0.05, would push to 0.07 — but clamped to 0.10.
        _, new = await update_reputation(
            session=session,
            event_bus=bus,
            agent_id=agent_id,
            judge_score=0.20,
        )

    assert abs(new - settings.rep_min) < 1e-3
    async with session_scope() as session:
        agent = await session.get(Agent, agent_id)
        assert abs(float(agent.reputation) - settings.rep_min) < 1e-3
