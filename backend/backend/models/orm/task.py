"""`tasks` table — see spec §5."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(64), ForeignKey("jobs.id"), nullable=False)
    parent_task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    required_skills: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    skill_embedding: Mapped[list[float] | None] = mapped_column(Vector(768), nullable=True)
    budget: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    final_cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    dependencies: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default="{}"
    )
    assigned_agent_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    output_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    judge_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    judge_verdict: Mapped[str | None] = mapped_column(String(32), nullable=True)
    judge_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    revision_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_tasks_job", "job_id"),
        Index("idx_tasks_state", "state"),
        Index("idx_tasks_agent", "assigned_agent_id"),
    )
