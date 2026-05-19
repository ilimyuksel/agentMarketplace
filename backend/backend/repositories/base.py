"""Generic async repository.

`Repository[T]` provides the common CRUD primitives that every concrete repo needs:
fetch-by-id, add, list, delete. Concrete subclasses declare `model` and add their own
query helpers as needed.

Sessions are passed in by the caller (typically the orchestrator or an API handler).
A repository never opens or commits a session — that's the caller's responsibility,
via `core.database.session_scope` or the FastAPI `get_session` dependency.
"""

from __future__ import annotations

from typing import Any, ClassVar, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import Base

T = TypeVar("T", bound=Base)


class Repository(Generic[T]):
    model: ClassVar[type[Base]]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ---------- single-entity ----------

    async def get(self, entity_id: Any) -> T | None:
        return await self.session.get(self.model, entity_id)  # type: ignore[return-value]

    async def add(self, entity: T) -> T:
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def delete(self, entity: T) -> None:
        await self.session.delete(entity)
        await self.session.flush()

    # ---------- collection ----------

    async def list_all(self, *, limit: int | None = None, offset: int = 0) -> list[T]:
        stmt = select(self.model).offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self) -> int:
        from sqlalchemy import func

        stmt = select(func.count()).select_from(self.model)
        result = await self.session.execute(stmt)
        return int(result.scalar() or 0)
