"""LLM output parsing primitives.

Three responsibilities:
    1. `extract_json_from_response`: best-effort JSON-object extraction from raw text.
    2. `validate_against_schema`: Pydantic v2 validation, returning (instance, error).
    3. `build_repair_prompt`: format the AGENT_PROMPTS.md §8 repair template.

The repair retry loop itself lives in callers (per §16-A11, exactly one
repair attempt per execution). This module only provides the building blocks.
"""

from __future__ import annotations

import json
import re
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from backend.llm.prompts.repair_prompt import REPAIR_PROMPT_TEMPLATE

T = TypeVar("T", bound=BaseModel)

_FENCE_RE = re.compile(
    r"```(?:json|JSON)?\s*\n?(.+?)\n?\s*```", re.DOTALL
)


def extract_json_from_response(text: str | None) -> dict[str, Any] | None:
    """Try several strategies to pull a JSON object out of LLM output.

    Order: direct parse → ```json fence ``` → first brace-balanced substring.
    Returns None if all strategies fail.
    """
    if not text:
        return None
    stripped = text.strip()

    # 1) Direct parse
    obj = _try_parse(stripped)
    if obj is not None:
        return obj

    # 2) Fenced code block
    m = _FENCE_RE.search(stripped)
    if m:
        obj = _try_parse(m.group(1))
        if obj is not None:
            return obj

    # 3) First balanced { ... } substring
    blob = _find_balanced_braces(stripped)
    if blob is not None:
        obj = _try_parse(blob)
        if obj is not None:
            return obj

    return None


def validate_against_schema(
    parsed: dict[str, Any], model: type[T]
) -> tuple[T | None, str | None]:
    """Validate `parsed` against the Pydantic model.

    Returns (instance, None) on success, or (None, formatted_error) on failure.
    The formatted_error is suitable to feed into `build_repair_prompt`.
    """
    try:
        return model.model_validate(parsed), None
    except ValidationError as exc:
        return None, exc.json(indent=2, include_url=False)


def build_repair_prompt(
    *,
    schema_description: str,
    previous_response: str,
    error_message: str,
) -> str:
    return REPAIR_PROMPT_TEMPLATE.format(
        schema_description=schema_description,
        previous_response=previous_response,
        error_message=error_message,
    )


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _try_parse(text: str) -> dict[str, Any] | None:
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _find_balanced_braces(s: str) -> str | None:
    """Return the first balanced top-level `{...}` substring, or None.

    Handles JSON string-literal quoting (so an unmatched `}` inside a
    string doesn't pop the depth).
    """
    start = s.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    i = start
    while i < len(s):
        c = s[i]
        if in_string:
            if c == "\\":
                i += 2  # skip escaped char
                continue
            if c == '"':
                in_string = False
            i += 1
            continue
        if c == '"':
            in_string = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return s[start : i + 1]
        i += 1
    return None
