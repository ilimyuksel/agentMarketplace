"""Hybrid selection: composite score → ghost filter → top-K → Gemini reranker.

Per spec §7.3 the composite score is a weighted sum of five factors. The
weights live in `settings`. The cosine similarity between the agent's
skill embedding and the task's skill embedding is computed in Python with
NumPy — pgvector could do it server-side, but doing it here lets us keep
the scoring function pure and unit-testable.

Reputation is read FRESH from the agents table inside `select_winner`,
NOT from the cached `BaseAgent.orm`, per the Phase-4 retrospective item 8:
the cache is stable enough for class lookup and prompt selection, but
reputation is mutated by `reputation_service` after every judge verdict
and a stale snapshot would distort the score.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import numpy as np
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.constants import RERANKER_SHORTLIST_SIZE
from backend.core.event_bus import EventBus
from backend.core.event_types import BIDDING_WINNER_SELECTED
from backend.core.logger import get_logger
from backend.exceptions import NoAgentAvailableForSkillError
from backend.llm.gemini_client import get_gemini_client
from backend.llm.output_parser import extract_json_from_response, validate_against_schema
from backend.llm.prompts.reranker_prompt import RERANKER_PROMPT_TEMPLATE
from backend.models.orm.agent import Agent
from backend.models.orm.bid import Bid
from backend.models.orm.task import Task

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Pure scoring (unit-testable)
# ---------------------------------------------------------------------------


def cosine_similarity(a: list[float] | None, b: list[float] | None) -> float:
    """Cosine sim of two embeddings. 0.0 if either is missing or a zero vector."""
    if not a or not b:
        return 0.0
    av = np.asarray(a, dtype=float)
    bv = np.asarray(b, dtype=float)
    na = float(np.linalg.norm(av))
    nb = float(np.linalg.norm(bv))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(np.dot(av, bv) / (na * nb))


def compute_composite_score(
    *,
    skill_similarity: float,
    agent_reputation: float,
    bid_amount: float,
    task_budget: float,
    confidence: float | None,
    estimated_time_seconds: int | None,
) -> float:
    """The §7.3 weighted sum. Defaults: confidence=0.5, slow ≥60s → speed_score=0."""
    if bid_amount > task_budget:
        price_score = 0.0
    else:
        price_score = 1.0 - (bid_amount / task_budget) * 0.5

    speed = float(estimated_time_seconds) if estimated_time_seconds else 60.0
    speed_score = max(0.0, 1.0 - speed / 60.0)

    conf = float(confidence) if confidence is not None else 0.5

    return (
        settings.weight_skill_similarity * skill_similarity
        + settings.weight_reputation * agent_reputation
        + settings.weight_price * price_score
        + settings.weight_confidence * conf
        + settings.weight_speed * speed_score
    )


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


@dataclass
class _ScoredBid:
    bid: Bid
    agent: Agent
    score: float


class _RerankerResponse(BaseModel):
    winner_id: str
    reasoning: str = ""
    runner_up_id: str | None = None
    confidence_in_selection: float | None = Field(default=None, ge=0.0, le=1.0)


def _render_candidates(scored: list[_ScoredBid]) -> str:
    lines: list[str] = []
    for i, sc in enumerate(scored, 1):
        reasoning = (sc.bid.reasoning or "").replace("\n", " ").strip()
        if len(reasoning) > 160:
            reasoning = reasoning[:157] + "..."
        lines.append(
            f"- Candidate {i}: agent_id={sc.agent.id}, "
            f"reputation={float(sc.agent.reputation):.3f}, "
            f"bid_amount=${float(sc.bid.bid_amount):.2f}, "
            f"confidence={(float(sc.bid.confidence) if sc.bid.confidence is not None else 0.0):.2f}, "
            f"estimated_time={sc.bid.estimated_time_seconds or 'unknown'}s, "
            f"composite_score={sc.score:.4f}, "
            f'reasoning="{reasoning}"'
        )
    return "\n".join(lines)


async def _run_reranker(
    task: Task, scored: list[_ScoredBid]
) -> tuple[str, str | None, str, bool]:
    """Call Gemini reranker. Returns (winner_id, runner_up_id, reasoning, used_fallback).

    On any failure (LLM error, malformed JSON, hallucinated agent_id), falls
    back to the top-scoring candidate.
    """
    fallback_winner = scored[0].agent.id
    fallback_runner_up = scored[1].agent.id if len(scored) >= 2 else None

    prompt = RERANKER_PROMPT_TEMPLATE.format(
        task_title=task.title,
        task_description=task.description,
        task_budget=f"{float(task.budget):.2f}",
        required_skills=", ".join(task.required_skills or []),
        candidates_table=_render_candidates(scored),
    )

    try:
        raw = await get_gemini_client().generate(
            prompt=prompt, response_mime_type="application/json"
        )
    except Exception as exc:
        logger.warning(
            "selection.reranker.llm_failed",
            task_id=task.id,
            error_type=type(exc).__name__,
            error=str(exc)[:200],
        )
        return (
            fallback_winner,
            fallback_runner_up,
            "Reranker LLM error; selected highest composite score.",
            True,
        )

    parsed = extract_json_from_response(raw)
    if parsed is None:
        logger.warning("selection.reranker.unparseable", task_id=task.id, raw=raw[:200])
        return (
            fallback_winner,
            fallback_runner_up,
            "Reranker output not JSON; selected highest composite score.",
            True,
        )

    validated, err = validate_against_schema(parsed, _RerankerResponse)
    if validated is None:
        logger.warning("selection.reranker.invalid", task_id=task.id, error=err)
        return (
            fallback_winner,
            fallback_runner_up,
            "Reranker output failed validation; selected highest composite score.",
            True,
        )

    valid_ids = {sc.agent.id for sc in scored}
    if validated.winner_id not in valid_ids:
        logger.warning(
            "selection.reranker.hallucinated_winner",
            task_id=task.id,
            winner_id=validated.winner_id,
            valid_ids=sorted(valid_ids),
        )
        return (
            fallback_winner,
            fallback_runner_up,
            "Reranker hallucinated unknown winner; selected highest composite score.",
            True,
        )

    runner_up = validated.runner_up_id if validated.runner_up_id in valid_ids else None
    return (validated.winner_id, runner_up, validated.reasoning, False)


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------


async def select_winner(
    *,
    task: Task,
    bids: list[Bid],
    session: AsyncSession,
    event_bus: EventBus,
) -> Bid:
    """Score, ghost-filter, rerank → winner. Persists is_winner + selection_score.

    Raises `NoAgentAvailableForSkillError` if no non-ghost bid is present.
    """
    if not bids:
        raise NoAgentAvailableForSkillError(
            f"no bids for task {task.id} — selection cannot proceed"
        )

    # Fresh reputation read for every bidding agent.
    agent_ids = list({b.agent_id for b in bids})
    rows = (
        await session.execute(select(Agent).where(Agent.id.in_(agent_ids)))
    ).scalars().all()
    agents_by_id = {a.id: a for a in rows}

    scored: list[_ScoredBid] = []
    for bid in bids:
        agent = agents_by_id.get(bid.agent_id)
        if agent is None:
            logger.warning(
                "selection.unknown_agent", task_id=task.id, agent_id=bid.agent_id
            )
            continue
        skill_sim = cosine_similarity(
            list(agent.skill_embedding) if agent.skill_embedding is not None else None,
            list(task.skill_embedding) if task.skill_embedding is not None else None,
        )
        score = compute_composite_score(
            skill_similarity=skill_sim,
            agent_reputation=float(agent.reputation),
            bid_amount=float(bid.bid_amount),
            task_budget=float(task.budget),
            confidence=float(bid.confidence) if bid.confidence is not None else None,
            estimated_time_seconds=bid.estimated_time_seconds,
        )
        bid.selection_score = Decimal(str(round(score, 4)))
        scored.append(_ScoredBid(bid=bid, agent=agent, score=score))

    # Persist the score updates we just made.
    await session.flush()

    if not scored:
        raise NoAgentAvailableForSkillError(
            f"task {task.id}: no bids could be scored (agents missing?)"
        )

    # Sort: composite desc, then reputation desc, then estimated_time asc,
    # then completed_jobs asc (spec §7.3 tie-break order).
    scored.sort(
        key=lambda s: (
            -s.score,
            -float(s.agent.reputation),
            s.bid.estimated_time_seconds or 99999,
            int(s.agent.completed_jobs or 0),
        )
    )

    # GHOSTS NEVER WIN (spec §16-A5).
    non_ghost = [s for s in scored if not s.agent.is_ghost]
    if not non_ghost:
        raise NoAgentAvailableForSkillError(
            f"task {task.id}: only ghost bidders present — cannot select a winner"
        )

    shortlist = non_ghost[: RERANKER_SHORTLIST_SIZE]

    if len(shortlist) == 1:
        winner_id = shortlist[0].agent.id
        runner_up_id: str | None = None
        rerank_reasoning = "Only one non-ghost candidate; reranker skipped."
        used_fallback = True
    else:
        winner_id, runner_up_id, rerank_reasoning, used_fallback = await _run_reranker(
            task, shortlist
        )

    winner = next(s for s in shortlist if s.agent.id == winner_id)
    winner.bid.is_winner = True
    await session.flush()

    await event_bus.publish(
        BIDDING_WINNER_SELECTED,
        {
            "task_id": task.id,
            "winner_id": winner_id,
            "winner_bid_id": winner.bid.id,
            "winner_bid_amount": float(winner.bid.bid_amount),
            "selection_score": float(winner.bid.selection_score),
            "runner_up_id": runner_up_id,
            "reranker_used": not used_fallback,
            "reranker_reasoning": rerank_reasoning,
            "shortlist": [
                {
                    "agent_id": s.agent.id,
                    "bid_id": s.bid.id,
                    "score": float(s.bid.selection_score),
                    "bid_amount": float(s.bid.bid_amount),
                }
                for s in shortlist
            ],
        },
        job_id=task.job_id,
        task_id=task.id,
    )

    logger.info(
        "selection.winner",
        task_id=task.id,
        winner_id=winner_id,
        score=float(winner.bid.selection_score),
        runner_up_id=runner_up_id,
        reranker_used=not used_fallback,
    )
    return winner.bid
