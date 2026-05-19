"""Designer revision drama — the demo's emotional peak.

Exercises the prompt-design strategy from Phase 11:
    1. Designer's first attempt deliberately produces a safe / generic
       palette (per the revision_count==0 branch in its prompt).
    2. The Judge's prompt explicitly penalizes generic palettes →
       REVISION_REQUESTED with score in the [0.50, 0.69] band.
    3. Designer's second attempt commits to audience-specific signals
       (per the revision_count>=1 branch).
    4. The Judge approves (final_score >= 0.70).

This test calls Designer + Judge directly (4 LLM calls total) rather than
going through the full marketplace + bidding flow. That keeps the test
inside a tight free-tier-quota budget while still proving the revision
contract end-to-end. The full-pipeline path through `execute_task` is
already exercised by `test_single_task_pipeline.py` and the orchestrator
demo runs.
"""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

from backend.agents.registry import get_agent_registry


_DEV_BRIEF_DESCRIPTION = (
    "Produce a complete design token set for a landing page targeting "
    "senior backend developers at Series A-C startups. The product is "
    "an AI pair-programming tool that integrates with private monorepos. "
    "Palette and typography MUST visibly reflect the developer audience — "
    "dark themes, code-friendly fonts, accent colors that signal technical "
    "credibility."
)
_TASK_ID = "task_test_designer_revision_arc"


@pytest.mark.live_gemini
@pytest.mark.asyncio
async def test_designer_revision_arc_completes():
    registry = get_agent_registry()
    designer = await registry.get_by_id("Designer_001")
    judge = await registry.list_judge()

    # ---- Attempt #1 — revision_count=0 — expect SAFE / GENERIC palette ----
    first_ctx = {
        "task_id": _TASK_ID,
        "task_title": "Design direction",
        "task_description": _DEV_BRIEF_DESCRIPTION,
        "final_cost": 22.00,
        "dependencies_context": {
            "market_research": {
                "target_audience": {
                    "primary_segment": "senior backend engineers at Series A-C startups",
                    "demographics": "5-15 yrs experience; Python/Go/TypeScript",
                    "pain_points": [
                        "PR review backlogs eat sprint capacity",
                        "Context switching across repos kills focus",
                        "Generic AI tools don't know team conventions",
                    ],
                },
            },
        },
        "revision_count": 0,
    }
    print("\n=== ATTEMPT #1 (revision_count=0) ===")
    first_output = await designer.execute(first_ctx)
    print("Designer first-attempt deliverable:")
    print(json.dumps(first_output, indent=2)[:1600])

    # ---- Judge #1 — expect REVISION_REQUESTED on the generic palette ----
    judge_ctx_1 = {
        "task_id": _TASK_ID,
        "evaluated_agent_id": designer.id,
        "task_description": _DEV_BRIEF_DESCRIPTION,
        "agent_output": first_output,
        "revision_count": 0,
    }
    first_verdict = await judge.execute(judge_ctx_1)
    print("\n--- Judge verdict on attempt #1 ---")
    print(json.dumps(first_verdict, indent=2))

    # The whole point of the drama is that the judge actually rejects
    # the generic output. If the LLMs both behave correctly, we expect
    # `REVISION_REQUESTED` here.
    first_decision = first_verdict["decision"]
    first_score = float(first_verdict["final_score"])
    print(f"  → score={first_score:.3f}  decision={first_decision}")

    # Strict assertion: if the prompts are calibrated correctly, the
    # judge MUST request revision. If you ever see this assertion fail,
    # the Designer's "safe palette" branch or the Judge's anti-pattern
    # rubric is no longer producing the intended pressure.
    assert first_decision == "REVISION_REQUESTED", (
        f"expected REVISION_REQUESTED on the generic first attempt, "
        f"got decision={first_decision} (score={first_score:.3f}). "
        f"Reasoning: {first_verdict.get('reasoning')}"
    )
    assert 0.50 <= first_score < 0.70, (
        f"REVISION_REQUESTED should put score in the [0.50, 0.70) band; "
        f"got {first_score:.3f}"
    )

    # ---- Attempt #2 — revision_count=1 — expect AUDIENCE-AWARE palette ----
    second_ctx = {
        **first_ctx,
        "revision_count": 1,
        "judge_feedback": first_verdict.get("feedback_for_revision")
        or "Be more audience-specific — incorporate dark theme + dev-coded accent colors.",
    }
    print("\n=== ATTEMPT #2 (revision_count=1) ===")
    second_output = await designer.execute(second_ctx)
    print("Designer revision deliverable:")
    print(json.dumps(second_output, indent=2)[:1600])

    # ---- Judge #2 — expect APPROVED on the audience-aware revision ----
    judge_ctx_2 = {
        **judge_ctx_1,
        "agent_output": second_output,
        "revision_count": 1,
    }
    second_verdict = await judge.execute(judge_ctx_2)
    print("\n--- Judge verdict on attempt #2 ---")
    print(json.dumps(second_verdict, indent=2))

    second_decision = second_verdict["decision"]
    second_score = float(second_verdict["final_score"])
    print(f"  → score={second_score:.3f}  decision={second_decision}")

    assert second_decision == "APPROVED", (
        f"expected APPROVED on the audience-aware revision, got "
        f"decision={second_decision} (score={second_score:.3f}). "
        f"Reasoning: {second_verdict.get('reasoning')}"
    )
    assert second_score >= 0.70, (
        f"APPROVED should have score >= 0.70; got {second_score:.3f}"
    )

    # ---- Side-by-side proof ----
    print("\n=== SIDE-BY-SIDE PALETTE SHIFT ===")
    first_palette = first_output.get("deliverable", {}).get("color_palette", {})
    second_palette = second_output.get("deliverable", {}).get("color_palette", {})
    print(f"  attempt 1 primary    : {first_palette.get('primary')}")
    print(f"  attempt 2 primary    : {second_palette.get('primary')}")
    print(f"  attempt 1 background : {first_palette.get('background')}")
    print(f"  attempt 2 background : {second_palette.get('background')}")
    print(f"  attempt 1 score      : {first_score:.3f}  ({first_decision})")
    print(f"  attempt 2 score      : {second_score:.3f}  ({second_decision})")
    print(f"  revision arc gain    : {second_score - first_score:+.3f}")