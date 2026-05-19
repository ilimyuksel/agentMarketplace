"""Deterministic final-output assembly. NO Gemini call.

For a landing-page job, the `WebDeveloper_001` task's `html_code` field
is the primary deliverable; everything else (research, copy, design)
goes into the JobOutput's `content` JSONB as metadata.

Spec §6 Critical-Path Tolerance: if the WebDeveloper task didn't ship
(only soft-failures), `aggregate_outputs` returns a minimal fallback
HTML so the API can still serve *something*. The caller (orchestrator)
decides whether to mark the job COMPLETED or FAILED based on whether
the critical path actually succeeded.
"""

from __future__ import annotations

import html
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.constants import CRITICAL_SKILLS
from backend.core.logger import get_logger
from backend.enums.task_state import TaskState
from backend.models.orm.job_output import JobOutput
from backend.models.orm.task import Task

logger = get_logger(__name__)


def _primary_skill_key(task: Task) -> str:
    if task.required_skills:
        return task.required_skills[0]
    return task.id


async def aggregate_outputs(
    *, job_id: str, session: AsyncSession
) -> JobOutput:
    """Walk every PAID task for the job and assemble a `job_outputs` row."""
    rows = (
        await session.execute(
            select(Task)
            .where(Task.job_id == job_id)
            .order_by(Task.created_at.asc())
        )
    ).scalars().all()

    contributing: list[str] = []
    total_cost = Decimal("0.00")
    by_skill: dict[str, Any] = {}
    html_artifact: str | None = None
    html_source_agent: str | None = None

    for t in rows:
        if t.state != TaskState.PAID.value:
            continue
        if t.assigned_agent_id and t.assigned_agent_id not in contributing:
            contributing.append(t.assigned_agent_id)
        if t.final_cost is not None:
            total_cost += t.final_cost
        if not t.output_json:
            continue

        by_skill[_primary_skill_key(t)] = t.output_json

        # WebDeveloper's deliverable carries the HTML.
        deliverable = (
            t.output_json.get("deliverable", {})
            if isinstance(t.output_json, dict)
            else {}
        )
        candidate = deliverable.get("html_code") if isinstance(deliverable, dict) else None
        if isinstance(candidate, str) and candidate.strip():
            html_artifact = candidate
            html_source_agent = t.assigned_agent_id

    missing_critical = html_artifact is None
    if missing_critical:
        html_artifact = _build_fallback_html(by_skill)
        logger.warning(
            "aggregator.fallback_used",
            job_id=job_id,
            reason="no WebDeveloper output present in PAID tasks",
            available_skills=sorted(by_skill.keys()),
        )

    content = {
        "tasks": [t.id for t in rows if t.state == TaskState.PAID.value],
        "by_skill": by_skill,
        "html_source_agent": html_source_agent,
        "critical_skills_required": list(CRITICAL_SKILLS),
        "fallback_html_used": missing_critical,
    }

    output_row = JobOutput(
        id=f"output_{uuid.uuid4().hex[:16]}",
        job_id=job_id,
        output_type="landing_page",
        content=content,
        html_artifact=html_artifact,
        contributing_agents=contributing,
        total_cost=total_cost.quantize(Decimal("0.01")),
    )
    session.add(output_row)
    await session.flush()
    logger.info(
        "aggregator.done",
        job_id=job_id,
        contributing=contributing,
        total_cost=str(total_cost),
        fallback_html=missing_critical,
    )
    return output_row


# ---------------------------------------------------------------------------
# Fallback
# ---------------------------------------------------------------------------


def _build_fallback_html(by_skill: dict[str, Any]) -> str:
    """Last-resort HTML when no WebDeveloper output is available."""
    headline = "AI Agent Marketplace — Landing Page (Fallback)"
    subhead = "WebDeveloper output unavailable. Showing assembled fragments only."
    copy_block = ""

    copy = by_skill.get("copywriting") or by_skill.get("content_writing")
    if isinstance(copy, dict):
        deliv = copy.get("deliverable", {})
        if isinstance(deliv, dict):
            headline = deliv.get("hero_headline", headline)
            subhead = deliv.get("subheadline", subhead)
            vps = deliv.get("value_propositions") or []
            if isinstance(vps, list) and vps:
                bullets = "".join(f"<li>{html.escape(str(v))}</li>" for v in vps)
                copy_block = f"<ul>{bullets}</ul>"

    return (
        "<!DOCTYPE html>\n"
        "<html lang='en'><head><meta charset='utf-8'>"
        f"<title>{html.escape(headline)}</title>"
        "<style>body{font-family:system-ui;max-width:720px;margin:48px auto;padding:0 16px;}"
        "h1{font-size:2rem;}p{color:#555;}small{color:#888;}</style>"
        "</head><body>"
        f"<h1>{html.escape(headline)}</h1>"
        f"<p>{html.escape(subhead)}</p>"
        f"{copy_block}"
        "<hr>"
        "<small>Built by AI Agent Marketplace (fallback assembly).</small>"
        "</body></html>"
    )
