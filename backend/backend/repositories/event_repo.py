"""Event audit-log repository."""

from __future__ import annotations

from sqlalchemy import select

from backend.models.orm.event import Event
from backend.repositories.base import Repository


class EventRepository(Repository[Event]):
    model = Event

    async def list_for_job(
        self,
        job_id: str,
        *,
        since_event_id: int | None = None,
        limit: int | None = None,
    ) -> list[Event]:
        """Return events for a job ordered by their monotonic BigInteger id.

        `since_event_id` enables resume-from-cursor semantics for reconnecting
        WebSocket clients (currently unused by the v1 replay path, which
        replays from the beginning, but kept for forward compatibility).
        """
        stmt = select(Event).where(Event.job_id == job_id)
        if since_event_id is not None:
            stmt = stmt.where(Event.id > since_event_id)
        stmt = stmt.order_by(Event.id.asc())
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_recent(self, limit: int = 100) -> list[Event]:
        stmt = select(Event).order_by(Event.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
