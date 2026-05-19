"""WebSocket connection registry.

`WSConnection` is a thin wrapper around a Starlette/FastAPI `WebSocket` that
adds a per-connection send lock. Tests substitute a duck-typed stub that
exposes the same `send_json` method.

The send lock serves two purposes:
    1. Serialize concurrent writes from the broadcaster so JSON frames
       don't interleave on the wire.
    2. Allow the job-feed handler to perform a burst of replay sends
       atomically — by acquiring the lock for the whole replay, any
       live broadcasts to the same connection wait until replay is done.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, Protocol

from backend.core.logger import get_logger

logger = get_logger(__name__)


class WebSocketLike(Protocol):
    """Minimal WebSocket shape the manager needs.

    Production hands us a `starlette.websockets.WebSocket`. Tests hand us
    a stub. Either works as long as it exposes `send_json`.
    """

    async def send_json(self, data: Any) -> None: ...


class WSConnection:
    """A live WebSocket + a per-connection send lock."""

    def __init__(self, websocket: WebSocketLike) -> None:
        self.ws = websocket
        # Public on purpose — the job-feed handler holds it across an
        # entire replay burst. See `core/event_bus.py` for the protocol.
        self.send_lock = asyncio.Lock()

    async def send(self, message: dict[str, Any]) -> None:
        async with self.send_lock:
            await self.ws.send_json(message)


class ConnectionManager:
    """Per-channel registry of active `WSConnection`s."""

    def __init__(self) -> None:
        self._channels: dict[str, set[WSConnection]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def register(self, conn: WSConnection, channel: str) -> None:
        async with self._lock:
            self._channels[channel].add(conn)
        logger.info("ws.connection.registered", channel=channel, count=len(self._channels[channel]))

    async def unregister(self, conn: WSConnection, channel: str) -> None:
        async with self._lock:
            self._channels.get(channel, set()).discard(conn)
        logger.info(
            "ws.connection.unregistered",
            channel=channel,
            remaining=len(self._channels.get(channel, set())),
        )

    async def broadcast(self, channel: str, message: dict[str, Any]) -> None:
        async with self._lock:
            conns = list(self._channels.get(channel, set()))
        if not conns:
            return
        results = await asyncio.gather(
            *(conn.send(message) for conn in conns), return_exceptions=True
        )
        # Drop dead connections that raised during send.
        dead = [c for c, r in zip(conns, results) if isinstance(r, BaseException)]
        if dead:
            async with self._lock:
                for c in dead:
                    self._channels.get(channel, set()).discard(c)
            for c, r in zip(conns, results):
                if isinstance(r, BaseException):
                    logger.warning(
                        "ws.broadcast.send_failed",
                        channel=channel,
                        error_type=type(r).__name__,
                        error=str(r)[:200],
                    )

    def channel_count(self, channel: str) -> int:
        """Diagnostic helper. Snapshot count; advisory only."""
        return len(self._channels.get(channel, set()))


# ---------------------------------------------------------------------------
# Process-wide singleton
# ---------------------------------------------------------------------------


_manager: ConnectionManager | None = None


def get_connection_manager() -> ConnectionManager:
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager


def reset_connection_manager() -> None:
    """Test-only."""
    global _manager
    _manager = None
