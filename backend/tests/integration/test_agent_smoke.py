"""Phase 4 — Exercise every agent in isolation and print the full response.

Gates exercised (per the Phase 4 plan):
    (a) ContentWriter_001.bid()
    (b) ContentWriter_001.execute()
    (c) ProjectManager_001.execute() (planning + UUID remap)
    (d) ContentWriter_002 (ghost) bid — deterministic, no Gemini call
    (e) AgentRegistry: list_workers / list_managers / list_judge
    (f) QAJudge_001.execute() — evaluation

Runs either as:
    python tests/integration/test_agent_smoke.py
    pytest tests/integration/test_agent_smoke.py -s
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

import pytest

from backend.agents.registry import get_agent_registry


def _section(title: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print("=" * 70)


def _dump(label: str, obj: Any) -> None:
    print(f"\n--- {label} ---")
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


# ---------------------------------------------------------------------------
# Gates
# ---------------------------------------------------------------------------


async def gate_a() -> dict[str, Any]:
    _section("GATE (a) — ContentWriter_001.bid()")
    reg = get_agent_registry()
    agent = await reg.get_by_id("ContentWriter_001")
    task_context = {
        "task_title": "Landing page copy",
        "task_description": "Write hero + 3 value props for a developer AI tool",
        "task_budget": 35,
        "required_skills": ["copywriting", "landing_page_copy"],
    }
    result = await agent.bid(task_context)
    _dump("bid response", result)
    return result


async def gate_b() -> dict[str, Any]:
    _section("GATE (b) — ContentWriter_001.execute()")
    reg = get_agent_registry()
    agent = await reg.get_by_id("ContentWriter_001")
    task_context = {
        "task_title": "Landing page copy",
        "task_description": (
            "Write hero headline, subheadline, three value propositions, "
            "and primary CTA for a developer-focused AI pair-programming tool. "
            "Voice: technical, developer-to-developer."
        ),
        "final_cost": 35,
        "dependencies_context": {
            "market_research": {
                "target_audience": {
                    "primary_segment": (
                        "senior backend engineers at Series A-C startups"
                    ),
                    "demographics": (
                        "5-15 yrs experience; small high-velocity teams; "
                        "Python/Go/TypeScript dominant"
                    ),
                    "pain_points": [
                        "PR review backlogs eat sprint capacity",
                        "Context switching between repos kills focus",
                        "Generic AI tools don't know team conventions",
                    ],
                },
            },
        },
    }
    result = await agent.execute(task_context)
    _dump("execute response", result)
    return result


async def gate_c() -> dict[str, Any]:
    _section("GATE (c) — ProjectManager_001.execute() (planning + UUID remap)")
    reg = get_agent_registry()
    pm = await reg.get_by_id("ProjectManager_001")
    job_context = {
        "user_prompt": "Create a landing page for a developer AI tool",
        "accepted_bid": 182.00,
        "profit_margin": 0.18,
        "budget_tier": "STANDARD",
    }
    plan = await pm.execute(job_context)
    _dump("plan", plan)
    print("\n--- UUID remap verification ---")
    for st in plan["sub_tasks"]:
        ok = st["id"].startswith("task_")
        deps_ok = all(d.startswith("task_") for d in st["dependencies"])
        print(
            f"  id={st['id']:34}  startswith_task_={ok}  "
            f"deps_remapped={deps_ok}  deps={st['dependencies']}"
        )
    return plan


async def gate_d() -> dict[str, Any]:
    _section("GATE (d) — Ghost ContentWriter_002.bid() (no Gemini call)")
    reg = get_agent_registry()
    ghost = await reg.get_by_id("ContentWriter_002")
    task_context = {
        "task_title": "Landing page copy",
        "task_description": "Write hero + 3 value props for a developer AI tool",
        "task_budget": 35,
        "required_skills": ["copywriting", "landing_page_copy"],
    }

    # Call twice to confirm determinism.
    r1 = await ghost.bid(task_context)
    r2 = await ghost.bid(task_context)
    _dump("bid response (1st call)", r1)
    print(f"\n  deterministic: {r1 == r2}")
    print(f"  is_ghost flag: {r1.get('is_ghost')}")
    print(f"  expected bid: 35 * 0.65 = {round(35 * 0.65, 2)}")
    return r1


async def gate_e() -> dict[str, Any]:
    _section("GATE (e) — AgentRegistry counts")
    reg = get_agent_registry()
    workers = await reg.list_workers()
    managers = await reg.list_managers()
    judge = await reg.list_judge()
    summary = {
        "workers": [{"id": w.id, "tier": w.tier, "is_ghost": w.is_ghost} for w in workers],
        "managers": [{"id": m.id, "tier": m.tier} for m in managers],
        "judge": {"id": judge.id, "tier": judge.tier},
    }
    _dump("registry summary", summary)
    print("\n  workers (T2):  ", len(workers))
    print("  managers (T1): ", len(managers))
    print("  judge (JUDGE): ", judge.id)
    return summary


async def gate_f() -> dict[str, Any]:
    _section("GATE (f) — QAJudge_001.execute() (evaluation)")
    reg = get_agent_registry()
    judge = await reg.list_judge()
    evaluation_context = {
        "task_id": "task_smoke_demo",
        "evaluated_agent_id": "ContentWriter_001",
        "task_description": (
            "Write hero headline, subheadline, three value propositions, and "
            "primary CTA for a developer-focused AI pair-programming tool. "
            "Voice: technical, developer-to-developer."
        ),
        "agent_output": {
            "deliverable": {
                "hero_headline": "Ship Production Code in Hours, Not Days",
                "subheadline": (
                    "AI pair-programming that actually understands your "
                    "codebase, your conventions, and your tests."
                ),
                "value_propositions": [
                    "Cuts PR review time by 60% on average",
                    "Indexes your entire monorepo, not just open files",
                    "Pays for itself within the first sprint",
                ],
                "primary_cta": "Start Free 14-Day Trial",
                "supporting_copy": [
                    (
                        "Built for engineering teams who measure velocity in shipped "
                        "features, not in lines of code. Drop it into your existing "
                        "GitHub workflow in under 10 minutes."
                    ),
                    (
                        "Unlike generic AI assistants, it learns your team's patterns "
                        "from your private repos. Your style guide is its style guide."
                    ),
                ],
                "tone_notes": (
                    "Developer-to-developer voice, technical credibility over "
                    "marketing polish, specificity-first."
                ),
            },
            "confidence_score": 0.89,
        },
        "revision_count": 0,
    }
    verdict = await judge.execute(evaluation_context)
    _dump("verdict", verdict)
    return verdict


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def main() -> int:
    print("Phase 4 agent smoke test")
    try:
        await gate_a()
        await gate_b()
        await gate_c()
        await gate_d()
        await gate_e()
        await gate_f()
        print("\n[OK] all 6 gates completed.")
        return 0
    except Exception as exc:
        print(f"\n[FAIL] {type(exc).__name__}: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


# pytest entry point
@pytest.mark.live_gemini
async def test_agent_smoke() -> None:  # noqa: D401
    """Pytest wrapper. Pass when all 6 gates complete without raising."""
    rc = await main()
    assert rc == 0, "agent smoke test failed — see stdout for details"


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
