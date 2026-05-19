"""In-process EventBus.

Responsibilities (per spec §3, §8, §10):
    - Cross-cutting communication between modules that, by §10, MUST NOT
      import each other directly (e.g., `payments/` listens to events from
      `workflow/`).
    - Audit-log persistence to the `events` table — same source of truth
      used by WebSocket replay on reconnect.
    - Fan-out to WebSocket subscribers via the attached `ConnectionManager`.

Channel routing:
    Every publish goes to the `"global"` channel. If `job_id` is provided,
    it also goes to `f"job:{job_id}"`. A single publish() call may therefore
    fan out to multiple channels — the connection manager and subscribers
    receive each event once per channel they subscribe to.

Failure mode:
    Persistence failure does not block notification. Subscriber failures
    do not block WS broadcast. Each layer logs and continues — the spirit
    of the demo is that the live feed should keep flowing even when a
    component misbehaves.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from backend.core.database import session_scope
from backend.core.event_types import CHANNEL_GLOBAL, channel_for_job
from backend.core.logger import get_logger
from backend.models.orm.event import Event as EventORM
from backend.repositories.event_repo import EventRepository

if TYPE_CHECKING:
    from backend.core.connection_manager import ConnectionManager

logger = get_logger(__name__)

SubscriberCallback = Callable[[dict[str, Any]], Awaitable[None]]


class EventBus:
    """In-process pub/sub with audit-log persistence and WS fan-out."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[SubscriberCallback]] = defaultdict(list)
        self._connection_manager: ConnectionManager | None = None

    # ---------- wiring ----------

    def attach_connection_manager(self, cm: ConnectionManager) -> None:
        """Bind the WebSocket connection registry. Called once at app startup."""
        self._connection_manager = cm

    def subscribe(self, channel: str, callback: SubscriberCallback) -> None:
        self._subscribers[channel].append(callback)

    def unsubscribe(self, channel: str, callback: SubscriberCallback) -> None:
        subs = self._subscribers.get(channel)
        if subs and callback in subs:
            subs.remove(callback)

    # ---------- main entry point ----------

    async def publish(
        self,
        event_type: str,
        payload: dict[str, Any],
        *,
        job_id: str | None = None,
        task_id: str | None = None,
        persist: bool = True,
    ) -> None:
        """Persist (optional), fan out to subscribers, broadcast to WS channels.

        `persist=False` is intended for high-frequency low-signal events
        such as `system.heartbeat` that would otherwise bloat the events
        table.
        """
        envelope: dict[str, Any] = {
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "job_id": job_id,
            "task_id": task_id,
            "payload": payload,
        }

        if persist:
            await self._persist(event_type, payload, job_id=job_id, task_id=task_id)

        channels = [CHANNEL_GLOBAL]
        if job_id:
            channels.append(channel_for_job(job_id))

        await self._notify_subscribers(channels, envelope)
        await self._broadcast_ws(channels, envelope)

    # ---------- internals ----------

    async def _persist(
        self,
        event_type: str,
        payload: dict[str, Any],
        *,
        job_id: str | None,
        task_id: str | None,
    ) -> None:
        try:
            async with session_scope() as session:
                await EventRepository(session).add(
                    EventORM(
                        event_type=event_type,
                        job_id=job_id,
                        task_id=task_id,
                        payload=payload,
                    )
                )
        except Exception as exc:  # never let persistence failure block live notify
            logger.error(
                "event_bus.persist.failed",
                event_type=event_type,
                error=str(exc)[:240],
            )

    async def _notify_subscribers(
        self, channels: list[str], envelope: dict[str, Any]
    ) -> None:
        for channel in channels:
            callbacks = list(self._subscribers.get(channel, []))
            if not callbacks:
                continue
            results = await asyncio.gather(
                *(cb(envelope) for cb in callbacks), return_exceptions=True
            )
            for cb, res in zip(callbacks, results):
                if isinstance(res, BaseException):
                    logger.error(
                        "event_bus.subscriber.failed",
                        channel=channel,
                        event_type=envelope["event_type"],
                        callback=getattr(cb, "__qualname__", repr(cb)),
                        error=str(res)[:240],
                    )

    async def _broadcast_ws(
        self, channels: list[str], envelope: dict[str, Any]
    ) -> None:
        cm = self._connection_manager
        if cm is None:
            return
        for channel in channels:
            try:
                await cm.broadcast(channel, envelope)
            except Exception as exc:
                logger.error(
                    "event_bus.ws_broadcast.failed",
                    channel=channel,
                    event_type=envelope["event_type"],
                    error=str(exc)[:240],
                )


# ---------------------------------------------------------------------------
# Process-wide singleton
# ---------------------------------------------------------------------------


_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus


def reset_event_bus() -> None:
    """Test-only: clears the singleton so subscribers don't leak across tests."""
    global _bus
    _bus = None
