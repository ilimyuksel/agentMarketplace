"""`reputation_history` table — see spec §5."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class ReputationHistory(Base):
    __tablename__ = "reputation_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(String(64), ForeignKey("agents.id"), nullable=False)
    job_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("jobs.id"), nullable=True)
    task_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("tasks.id"), nullable=True)
    old_reputation: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    new_reputation: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    delta: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    judge_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("idx_rep_agent", "agent_id"),)
