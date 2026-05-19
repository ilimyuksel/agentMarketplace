"""WebSocket integration: real uvicorn + real `websockets` client + real EventBus.

Two gates exercised:
    (c) /ws/global receives events published through the in-process bus.
    (d) /ws/jobs/{id} replays historical events on connect, then streams live.

Both run uvicorn inside the test's own asyncio loop so the EventBus singleton
is shared with the request handlers (no cross-loop reach-around).
"""

from __future__ import annotations

import asyncio
import json
import socket
import uuid

import pytest
import uvicorn
import websockets
from sqlalchemy import delete

from decimal import Decimal

from backend.constants import DEMO_USER_ID
from backend.core.database import session_scope
from backend.core.event_bus import get_event_bus, reset_event_bus
from backend.core.connection_manager import reset_connection_manager
from backend.enums.job_state import JobState
from backend.models.orm.event import Event
from backend.models.orm.job import Job
from backend.repositories.event_repo import EventRepository


# ---------------------------------------------------------------------------
# Server fixture
# ---------------------------------------------------------------------------


def _free_port() -> int:
    """Grab an OS-assigned free localhost port."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
async def server_url():
    # Reset singletons so each test fixture starts clean.
    reset_event_bus()
    reset_connection_manager()
    # Re-import after reset so main wires the fresh singletons together.
    from backend.main import app

    port = _free_port()
    config = uvicorn.Config(
        app, host="127.0.0.1", port=port, log_level="warning", lifespan="on"
    )
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())

    # Wait until uvicorn signals it's started.
    for _ in range(60):
        if server.started:
            break
        await asyncio.sleep(0.05)
    if not server.started:
        task.cancel()
        pytest.fail("uvicorn did not start within 3s")

    try:
        yield f"127.0.0.1:{port}"
    finally:
        server.should_exit = True
        try:
            await asyncio.wait_for(task, timeout=5.0)
        except asyncio.TimeoutError:
            task.cancel()


# ---------------------------------------------------------------------------
# Gate (c): live publish → WS receive
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_global_ws_receives_published_event(server_url):
    bus = get_event_bus()
    event_type = f"test.ws.{uuid.uuid4().hex[:8]}"

    uri = f"ws://{server_url}/ws/global"
    async with websockets.connect(uri) as ws:
        # Give the server's handler a beat to register the connection.
        await asyncio.sleep(0.05)
        await bus.publish(event_type, {"hello": "ws"}, persist=False)

        raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
        envelope = json.loads(raw)

    assert envelope["event_type"] == event_type
    assert envelope["payload"] == {"hello": "ws"}
    assert envelope["job_id"] is None
    assert envelope["task_id"] is None
    assert "timestamp" in envelope


# ---------------------------------------------------------------------------
# Gate (d): replay-on-connect then live
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_job_ws_replays_then_streams_live(server_url):
    job_id = f"job_test_{uuid.uuid4().hex[:8]}"

    # events.job_id has a FK to jobs.id — create a real Job first.
    async with session_scope() as session:
        session.add(
            Job(
                id=job_id,
                user_id=DEMO_USER_ID,
                user_prompt="WS replay test",
                budget=Decimal("100.00"),
                state=JobState.CREATED.value,
            )
        )
    async with session_scope() as session:
        repo = EventRepository(session)
        for i in range(3):
            await repo.add(
                Event(
                    event_type=f"test.replay.{i}",
                    job_id=job_id,
                    task_id=None,
                    payload={"index": i},
                )
            )

    try:
        bus = get_event_bus()
        uri = f"ws://{server_url}/ws/jobs/{job_id}"
        async with websockets.connect(uri) as ws:
            # Replay: receive 3 historical events in order.
            replayed: list[dict] = []
            for _ in range(3):
                raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                replayed.append(json.loads(raw))
            assert [e["event_type"] for e in replayed] == [
                "test.replay.0",
                "test.replay.1",
                "test.replay.2",
            ]
            assert [e["payload"]["index"] for e in replayed] == [0, 1, 2]
            assert all(e["job_id"] == job_id for e in replayed)

            # Now a live event for the same job arrives.
            await asyncio.sleep(0.05)
            await bus.publish(
                "test.live.4", {"index": 4}, job_id=job_id, persist=False
            )
            raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
            live = json.loads(raw)

        assert live["event_type"] == "test.live.4"
        assert live["job_id"] == job_id
        assert live["payload"] == {"index": 4}
    finally:
        # Cleanup: events first (FK), then the job row.
        async with session_scope() as session:
            await session.execute(delete(Event).where(Event.job_id == job_id))
            await session.execute(delete(Job).where(Job.id == job_id))
