"""Repair prompt template (AGENT_PROMPTS.md §8).

Spec §16-A11: callers use this exactly once per execution. If the repaired
output also fails to parse/validate, the task transitions to FAILED.
"""

from __future__ import annotations

REPAIR_PROMPT_TEMPLATE = """\
The previous response was malformed and could not be parsed.

EXPECTED SCHEMA:
{schema_description}

YOUR PREVIOUS RESPONSE:
{previous_response}

PARSE ERROR:
{error_message}

INSTRUCTIONS:
Return ONLY valid JSON matching the schema above. No prose. No markdown fences.
No explanations. Just the JSON object.

If your previous response was substantively correct but had formatting issues,
preserve the substance and fix the format. If the substance was also wrong,
produce a corrected response.
"""
