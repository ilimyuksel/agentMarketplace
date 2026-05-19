"""`judge_evaluations` table — see spec §5."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class JudgeEvaluation(Base):
    __tablename__ = "judge_evaluations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(64), ForeignKey("tasks.id"), nullable=False)
    evaluated_agent_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("agents.id"), nullable=False
    )
    scope_completeness: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    structural_quality: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    content_quality: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    brief_fidelity: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    final_score: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    feedback_for_revision: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_in_judgment: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("idx_eval_task", "task_id"),)
