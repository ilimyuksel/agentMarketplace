"""Pre-bidding eligibility filter.

A worker agent is eligible to bid on a task iff:
    1. It is in the T2 (worker) tier — managers and judges never bid here.
    2. It is `is_active` — admins can soft-disable an agent without deleting.
    3. Its `min_acceptance` does not exceed the task's budget.

Ghost agents pass the filter and bid normally — `selection_engine` is the
component that hard-excludes them from the rerank pool per spec §16-A5.
"""

from __future__ import annotations

from collections.abc import Iterable

from backend.core.logger import get_logger
from backend.marketplace.types import BiddingAgent
from backend.models.orm.task import Task

logger = get_logger(__name__)


def filter_eligible(
    task: Task,
    candidates: Iterable[BiddingAgent],
) -> list[BiddingAgent]:
    budget = float(task.budget)
    eligible: list[BiddingAgent] = []
    rejected_reasons: dict[str, str] = {}

    for agent in candidates:
        if agent.tier != "T2":
            rejected_reasons[agent.id] = f"tier={agent.tier}"
            continue
        if not agent.is_active:
            rejected_reasons[agent.id] = "inactive"
            continue
        if agent.min_acceptance > budget:
            rejected_reasons[agent.id] = (
                f"min_acceptance={agent.min_acceptance:.2f} > budget={budget:.2f}"
            )
            continue
        eligible.append(agent)

    logger.info(
        "marketplace.eligibility",
        task_id=task.id,
        eligible=[a.id for a in eligible],
        rejected=rejected_reasons,
    )
    return eligible
