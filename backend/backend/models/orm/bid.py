"""`bids` table — see spec §5."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class Bid(Base):
    __tablename__ = "bids"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(64), ForeignKey("tasks.id"), nullable=False)
    agent_id: Mapped[str] = mapped_column(String(64), ForeignKey("agents.id"), nullable=False)
    bid_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    estimated_time_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scope_assumption: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_winner: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    selection_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_bids_task", "task_id"),
        Index("idx_bids_agent", "agent_id"),
    )
