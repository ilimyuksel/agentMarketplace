"""EventBus: subscribe → publish → callback fires + event row persisted."""

from __future__ import annotations

import asyncio
import uuid

import pytest
from sqlalchemy import delete, select

from backend.core.database import session_scope
from backend.core.event_bus import EventBus, reset_event_bus
from backend.core.event_types import CHANNEL_GLOBAL, channel_for_job
from backend.models.orm.event import Event


@pytest.mark.asyncio
async def test_subscribe_and_publish_fires_callback_and_persists():
    reset_event_bus()
    bus = EventBus()

    received: list[dict] = []

    async def cb(envelope: dict) -> None:
        received.append(envelope)

    bus.subscribe(CHANNEL_GLOBAL, cb)

    event_type = f"test.bus.{uuid.uuid4().hex[:8]}"
    # No job_id: `events.job_id` has a FK to `jobs.id`. Job-scoped publish
    # is exercised in test_publish_with_job_id_fans_out_..., which avoids
    # persistence to sidestep the same constraint.
    await bus.publish(event_type, {"hello": "world"})

    assert len(received) == 1
    envelope = received[0]
    assert envelope["event_type"] == event_type
    assert envelope["payload"] == {"hello": "world"}
    assert envelope["job_id"] is None
    assert envelope["task_id"] is None
    assert "timestamp" in envelope

    async with session_scope() as session:
        rows = (
            await session.execute(
                select(Event).where(Event.event_type == event_type)
            )
        ).scalars().all()
    assert len(rows) == 1
    assert rows[0].payload == {"hello": "world"}
    assert rows[0].job_id is None

    async with session_scope() as session:
        await session.execute(delete(Event).where(Event.event_type == event_type))


@pytest.mark.asyncio
async def test_publish_with_job_id_fans_out_to_global_and_job_channels():
    reset_event_bus()
    bus = EventBus()

    global_received: list[dict] = []
    job_received: list[dict] = []

    async def gcb(envelope: dict) -> None:
        global_received.append(envelope)

    async def jcb(envelope: dict) -> None:
        job_received.append(envelope)

    job_id = f"job_test_{uuid.uuid4().hex[:8]}"
    bus.subscribe(CHANNEL_GLOBAL, gcb)
    bus.subscribe(channel_for_job(job_id), jcb)

    event_type = f"test.fanout.{uuid.uuid4().hex[:8]}"
    # persist=False sidesteps the events.job_id FK to jobs.id; this test
    # focuses on routing, not persistence.
    await bus.publish(event_type, {"k": 1}, job_id=job_id, persist=False)

    assert len(global_received) == 1
    assert len(job_received) == 1
    assert global_received[0]["event_type"] == event_type
    assert job_received[0]["event_type"] == event_type


@pytest.mark.asyncio
async def test_persist_false_skips_row_insert():
    reset_event_bus()
    bus = EventBus()

    event_type = f"test.heartbeat.{uuid.uuid4().hex[:8]}"
    await bus.publish(event_type, {"x": 1}, persist=False)

    async with session_scope() as session:
        rows = (
            await session.execute(select(Event).where(Event.event_type == event_type))
        ).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_failing_subscriber_does_not_break_others():
    reset_event_bus()
    bus = EventBus()
    received: list[dict] = []

    async def bad(envelope: dict) -> None:
        raise RuntimeError("subscriber went sideways")

    async def good(envelope: dict) -> None:
        received.append(envelope)

    bus.subscribe(CHANNEL_GLOBAL, bad)
    bus.subscribe(CHANNEL_GLOBAL, good)

    event_type = f"test.tolerant.{uuid.uuid4().hex[:8]}"
    await bus.publish(event_type, {}, persist=False)

    assert len(received) == 1  # good subscriber still fired
