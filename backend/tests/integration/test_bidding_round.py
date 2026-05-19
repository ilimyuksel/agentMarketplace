"""End-to-end bidding round + selection.

Real Gemini bids, real DB, real selection. Verifies:
    - bidding fans out and persists,
    - ghost is filtered before rerank,
    - winner is `ContentWriter_001` (premium copywriter on a copywriting task),
    - exactly one `is_winner=True` row exists for the task,
    - the events table records the expected sequence,
    - the ledger remains untouched after a bidding round (Phase 6 doesn't
      move money).
"""

from __future__ import annotations

import json
import uuid
from decimal import Decimal

import pytest
from sqlalchemy import delete, func, select

from backend.agents.registry import get_agent_registry
from backend.constants import DEMO_USER_ID
from backend.core.database import session_scope
from backend.core.event_bus import EventBus, get_event_bus, reset_event_bus
from backend.core.event_types import (
    BIDDING_BID_SUBMITTED,
    BIDDING_ROUND_STARTED,
    BIDDING_WINNER_SELECTED,
)
from backend.enums.job_state import JobState
from backend.enums.task_state import TaskState
from backend.llm.embedding_service import embed_text
from backend.marketplace.bidding_engine import run_bidding_round
from backend.marketplace.eligibility_filter import filter_eligible
from backend.marketplace.selection_engine import select_winner
from backend.models.orm.bid import Bid
from backend.models.orm.event import Event
from backend.models.orm.job import Job
from backend.models.orm.task import Task
from backend.models.orm.transaction import Transaction


@pytest.fixture
async def copy_task():
    """Yield a persisted Task ready for the marketplace. Cleans up after."""
    job_id = f"job_test_{uuid.uuid4().hex[:8]}"
    task_id = f"task_test_{uuid.uuid4().hex[:16]}"

    # Real Gemini embedding for the task — same path as the seed uses.
    skill_text = (
        "copywriting, landing page copy, hero headline, value propositions, "
        "conversion copy, developer audience"
    )
    embedding = await embed_text(skill_text)

    async with session_scope() as session:
        session.add(
            Job(
                id=job_id,
                user_id=DEMO_USER_ID,
                user_prompt="bidding round integration test",
                budget=Decimal("200.00"),
                state=JobState.EXECUTING.value,
            )
        )
        session.add(
            Task(
                id=task_id,
                job_id=job_id,
                title="Landing page copy",
                description=(
                    "Write hero headline, subheadline, three value propositions, "
                    "and primary CTA for a developer-focused AI tool."
                ),
                required_skills=["copywriting", "landing_page_copy"],
                skill_embedding=embedding,
                budget=Decimal("35.00"),
                state=TaskState.BIDDING.value,
            )
        )

    async with session_scope() as session:
        task = await session.get(Task, task_id)

    yield task

    # Cleanup respects FK order: events → bids → task → job.
    async with session_scope() as session:
        await session.execute(delete(Event).where(Event.task_id == task_id))
        await session.execute(delete(Event).where(Event.job_id == job_id))
        await session.execute(delete(Bid).where(Bid.task_id == task_id))
        await session.execute(delete(Task).where(Task.id == task_id))
        await session.execute(delete(Job).where(Job.id == job_id))


@pytest.mark.live_gemini
@pytest.mark.asyncio
async def test_bidding_round_and_selection_end_to_end(copy_task):
    task = copy_task
    reset_event_bus()
    bus = get_event_bus()

    # Snapshot ledger count BEFORE — Phase 6 must not write to it.
    async with session_scope() as session:
        ledger_before = (
            await session.execute(select(func.count(Transaction.id)))
        ).scalar_one()

    # Load the registry (DB-backed) and run eligibility.
    registry = get_agent_registry()
    workers = await registry.list_workers()
    eligible = filter_eligible(task, workers)

    print("\n--- eligible bidders ---")
    for a in eligible:
        print(f"  {a.id}  tier={a.tier}  ghost={a.is_ghost}  min={a.min_acceptance}")

    assert len(eligible) >= 2, "need at least 2 eligible bidders to make this meaningful"

    # Run bidding (real Gemini calls for non-ghost agents).
    async with session_scope() as session:
        bids = await run_bidding_round(
            task=task, eligible_agents=eligible, session=session, event_bus=bus
        )

    print(f"\n--- {len(bids)} accepted bid(s) ---")
    for b in bids:
        print(
            f"  {b.agent_id:24}  amount=${float(b.bid_amount):>7.2f}  "
            f"conf={float(b.confidence) if b.confidence is not None else 'NA':>5}  "
            f"eta={b.estimated_time_seconds}s"
        )

    assert len(bids) >= 2

    # Refresh the bids list with up-to-date task ref before selection.
    async with session_scope() as session:
        fresh_task = await session.get(Task, task.id)
        bid_rows = (
            await session.execute(
                select(Bid).where(Bid.task_id == task.id).order_by(Bid.submitted_at)
            )
        ).scalars().all()
        winner = await select_winner(
            task=fresh_task, bids=list(bid_rows), session=session, event_bus=bus
        )
        winner_id = winner.agent_id
        winner_score = float(winner.selection_score) if winner.selection_score else None

    print(f"\n--- winner: {winner_id}  score={winner_score:.4f} ---")

    # Premium reputation should beat the ghost's cheaper price.
    assert winner_id == "ContentWriter_001", (
        f"expected ContentWriter_001 to win, got {winner_id}"
    )

    # Exactly one is_winner row for this task.
    async with session_scope() as session:
        winning_rows = (
            await session.execute(
                select(Bid).where(Bid.task_id == task.id, Bid.is_winner.is_(True))
            )
        ).scalars().all()
    assert len(winning_rows) == 1
    assert winning_rows[0].agent_id == "ContentWriter_001"

    # Event sequence: round_started → bid_submitted*N → winner_selected.
    async with session_scope() as session:
        events = (
            await session.execute(
                select(Event)
                .where(Event.task_id == task.id)
                .order_by(Event.id.asc())
            )
        ).scalars().all()

    types = [e.event_type for e in events]
    print("\n--- event sequence ---")
    for e in events:
        agent = e.payload.get("agent_id") or e.payload.get("winner_id") or ""
        print(f"  {e.id:>5}  {e.event_type:30} agent={agent}")

    assert types[0] == BIDDING_ROUND_STARTED, types
    assert types[-1] == BIDDING_WINNER_SELECTED, types
    bid_events = [t for t in types if t == BIDDING_BID_SUBMITTED]
    assert len(bid_events) == len(bids), (len(bid_events), len(bids))

    # Envelope sanity on every event.
    for e in events:
        assert e.event_type
        assert e.job_id == task.job_id
        assert e.task_id == task.id
        assert isinstance(e.payload, dict)

    # The selection event payload includes runner_up_id (per §16-A12, event only).
    final = events[-1].payload
    assert final["winner_id"] == "ContentWriter_001"
    assert "runner_up_id" in final
    assert "shortlist" in final

    # Gate (d): no ledger writes from a bidding round.
    async with session_scope() as session:
        ledger_after = (
            await session.execute(select(func.count(Transaction.id)))
        ).scalar_one()
    assert ledger_after == ledger_before, (
        f"phase 6 must not write to the ledger; before={ledger_before}, after={ledger_after}"
    )

    # Dump full winner-selected payload for the human reviewer.
    print("\n--- winner_selected payload ---")
    print(json.dumps(final, indent=2, default=str))
