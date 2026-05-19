"""Abstract base class shared by all LLM-backed agents.

Concrete subclasses implement `bid()` and `execute()`. They typically delegate
to `self._call_gemini(...)`, which orchestrates the full LLM round-trip:

    build user prompt JSON
        ↓
    GeminiClient.generate(system_instruction=<persona>, prompt=<user-json>)
        ↓
    output_parser.extract_json_from_response
        ↓
    Pydantic validation
        ↓  (if step above failed)
    one repair attempt (per spec §16-A11)
        ↓
    return validated dict, or raise GeminiAPIError

Structured logs are emitted at every state transition with `agent_id`,
`task_id`, and `duration_ms` so the demo's WebSocket feed and the audit
log can reconstruct who did what.
"""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from typing import Any, TypeVar

from pydantic import BaseModel

from backend.core.logger import get_logger
from backend.exceptions import GeminiAPIError
from backend.llm.gemini_client import get_gemini_client
from backend.llm.output_parser import (
    build_repair_prompt,
    extract_json_from_response,
    validate_against_schema,
)
from backend.models.orm.agent import Agent as AgentORM

logger = get_logger(__name__)

ResponseT = TypeVar("ResponseT", bound=BaseModel)


class BaseAgent(ABC):
    """Common contract for every agent in the marketplace."""

    def __init__(self, orm: AgentORM) -> None:
        self.orm = orm

    # ---------- convenience accessors ----------

    @property
    def id(self) -> str:
        return self.orm.id

    @property
    def tier(self) -> str:
        return self.orm.tier

    @property
    def reputation(self) -> float:
        return float(self.orm.reputation)

    @property
    def is_ghost(self) -> bool:
        return bool(self.orm.is_ghost)

    @property
    def is_active(self) -> bool:
        return bool(self.orm.is_active)

    @property
    def min_acceptance(self) -> float:
        return float(self.orm.min_acceptance)

    @property
    def wallet_id(self) -> str:
        return str(self.orm.wallet_id)

    # ---------- abstract API ----------

    @abstractmethod
    async def bid(self, task_context: dict[str, Any]) -> dict[str, Any]:
        """Produce a bid for a task. Implementations decide the schema."""
        raise NotImplementedError

    @abstractmethod
    async def execute(self, task_context: dict[str, Any]) -> dict[str, Any]:
        """Produce a deliverable for an awarded task."""
        raise NotImplementedError

    # ---------- shared LLM helper ----------

    async def _call_gemini(
        self,
        *,
        system_prompt: str,
        user_payload: dict[str, Any],
        response_schema: type[ResponseT],
        operation: str,
        task_id: str | None = None,
    ) -> ResponseT:
        """Generate → parse → validate → (one-shot repair) → return.

        Raises `GeminiAPIError` if the repair attempt also fails or the
        underlying transport raises something non-retryable.
        """
        start = time.monotonic()
        log = logger.bind(agent_id=self.id, task_id=task_id, operation=operation)
        log.debug(f"agent.{operation}.start")

        user_text = json.dumps(user_payload, ensure_ascii=False, indent=2, default=str)
        client = get_gemini_client()

        # --- attempt 1 ---
        try:
            raw = await client.generate(
                prompt=user_text,
                system_instruction=system_prompt,
                response_mime_type="application/json",
            )
        except Exception as exc:
            log.error(f"agent.{operation}.gemini_failed", error=str(exc)[:240])
            raise GeminiAPIError(f"Gemini call failed in {self.id}.{operation}: {exc}") from exc

        validated, err = self._try_validate(raw, response_schema)
        if validated is not None:
            duration_ms = int((time.monotonic() - start) * 1000)
            log.debug(f"agent.{operation}.success", duration_ms=duration_ms, repaired=False)
            return validated

        # --- repair attempt (one-shot per §16-A11) ---
        log.warning(
            f"agent.{operation}.parse_failed",
            error=err,
            raw_preview=(raw or "")[:200],
        )
        repair_text = build_repair_prompt(
            schema_description=json.dumps(
                response_schema.model_json_schema(), indent=2, ensure_ascii=False
            ),
            previous_response=raw or "",
            error_message=err or "Output failed validation.",
        )
        try:
            raw2 = await client.generate(
                prompt=repair_text,
                system_instruction=system_prompt,
                response_mime_type="application/json",
            )
        except Exception as exc:
            log.error(f"agent.{operation}.repair_failed", error=str(exc)[:240])
            raise GeminiAPIError(
                f"Gemini repair call failed in {self.id}.{operation}: {exc}"
            ) from exc

        validated2, err2 = self._try_validate(raw2, response_schema)
        if validated2 is None:
            log.error(
                f"agent.{operation}.repair_invalid",
                error=err2,
                raw_preview=(raw2 or "")[:200],
            )
            raise GeminiAPIError(
                f"{self.id}.{operation}: repair attempt failed validation: {err2}"
            )

        duration_ms = int((time.monotonic() - start) * 1000)
        log.debug(f"agent.{operation}.success", duration_ms=duration_ms, repaired=True)
        return validated2

    @staticmethod
    def _try_validate(
        raw: str | None, model: type[ResponseT]
    ) -> tuple[ResponseT | None, str | None]:
        parsed = extract_json_from_response(raw)
        if parsed is None:
            return None, "Output was not parseable JSON."
        return validate_against_schema(parsed, model)
