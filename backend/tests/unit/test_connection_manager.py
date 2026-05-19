"""ConnectionManager: register / broadcast / disconnect handling."""

from __future__ import annotations

from typing import Any

import pytest

from backend.core.connection_manager import ConnectionManager, WSConnection


class FakeWebSocket:
    """Duck-typed WebSocket stub that matches the `WebSocketLike` protocol."""

    def __init__(self, *, fail_after: int | None = None) -> None:
        self.received: list[dict[str, Any]] = []
        self._fail_after = fail_after
        self._sends = 0

    async def send_json(self, data: dict[str, Any]) -> None:
        self._sends += 1
        if self._fail_after is not None and self._sends > self._fail_after:
            raise ConnectionError("simulated remote close")
        self.received.append(data)


@pytest.mark.asyncio
async def test_register_and_broadcast_reaches_all_subscribers():
    cm = ConnectionManager()
    ws_a, ws_b = FakeWebSocket(), FakeWebSocket()
    conn_a, conn_b = WSConnection(ws_a), WSConnection(ws_b)

    await cm.register(conn_a, "global")
    await cm.register(conn_b, "global")

    await cm.broadcast("global", {"event_type": "test.x", "payload": {"v": 1}})

    assert ws_a.received == [{"event_type": "test.x", "payload": {"v": 1}}]
    assert ws_b.received == [{"event_type": "test.x", "payload": {"v": 1}}]


@pytest.mark.asyncio
async def test_dead_connection_is_dropped_and_remaining_subscriber_keeps_receiving():
    cm = ConnectionManager()
    ws_alive = FakeWebSocket()
    ws_dies = FakeWebSocket(fail_after=0)  # raises on the very first send
    conn_alive, conn_dies = WSConnection(ws_alive), WSConnection(ws_dies)

    await cm.register(conn_alive, "global")
    await cm.register(conn_dies, "global")

    # First broadcast: alive receives, dies raises, manager drops it.
    await cm.broadcast("global", {"event_type": "first", "payload": {}})
    assert len(ws_alive.received) == 1
    assert ws_dies.received == []
    assert cm.channel_count("global") == 1  # dead one was removed

    # Second broadcast: only the surviving subscriber receives.
    await cm.broadcast("global", {"event_type": "second", "payload": {}})
    assert len(ws_alive.received) == 2
    assert ws_alive.received[-1]["event_type"] == "second"


@pytest.mark.asyncio
async def test_unregister_removes_connection():
    cm = ConnectionManager()
    ws = FakeWebSocket()
    conn = WSConnection(ws)

    await cm.register(conn, "global")
    assert cm.channel_count("global") == 1
    await cm.unregister(conn, "global")
    assert cm.channel_count("global") == 0

    await cm.broadcast("global", {"event_type": "noone", "payload": {}})
    assert ws.received == []


@pytest.mark.asyncio
async def test_broadcast_to_unknown_channel_is_a_noop():
    cm = ConnectionManager()
    await cm.broadcast("does-not-exist", {"event_type": "x", "payload": {}})  # no raise
