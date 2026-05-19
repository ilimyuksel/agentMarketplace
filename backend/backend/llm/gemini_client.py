"""Async wrapper around `google.genai` with concurrency + rate limit + per-category retries.

Singleton: call `get_gemini_client()` from app code. Tests may construct
their own instance and (optionally) call `reset_gemini_client()` to clear
the global cache.

Retry policy (spec §7.9):
    - timeout       : 1 retry,  delays = [2s]
    - rate limit    : 3 retries, delays = [5s, 10s, 20s]
    - server error  : 2 retries, delays = [3s, 6s]
    - network       : 2 retries, delays = [1s, 3s]
    - other         : no retry

Spec §16-A11: this client does NOT perform the JSON-parse repair retry
(that's a single attempt owned by callers via `output_parser`). It only
retries transport-level failures listed above.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types
from tenacity import AsyncRetrying, stop_never

from backend.config import settings
from backend.core.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Retry schedule + classification
# ---------------------------------------------------------------------------

_SCHEDULES: dict[str, list[float]] = {
    "timeout": [2.0, 5.0],
    "rate_limit": [5.0, 10.0, 20.0],
    # Gemini 5xx (esp. 503 "model overloaded") spikes can last 30–60s.
    # Stretching the schedule so a single API hiccup doesn't tank a
    # whole DAG: a failed critical task cascades the entire job.
    "server_error": [3.0, 8.0, 20.0, 45.0],
    "network": [1.0, 3.0, 8.0],
}


def _classify(exc: BaseException) -> str | None:
    """Map an exception to a retry category, or None if not retryable."""
    if isinstance(exc, asyncio.TimeoutError):
        return "timeout"
    if isinstance(exc, httpx.TimeoutException):
        return "timeout"
    if isinstance(exc, httpx.RemoteProtocolError):
        return "network"
    if isinstance(exc, httpx.NetworkError):
        return "network"
    if isinstance(exc, ConnectionError):
        return "network"

    code = getattr(exc, "code", None)
    if code is None:
        code = getattr(exc, "status_code", None)

    if code == 429:
        return "rate_limit"
    if code in (500, 502, 503, 504):
        return "server_error"

    # An APIError with no recognized code is not retryable (e.g., 400/403).
    return None


def _should_retry(retry_state: Any) -> bool:
    if retry_state.outcome is None or not retry_state.outcome.failed:
        return False
    exc = retry_state.outcome.exception()
    if exc is None:
        return False
    category = _classify(exc)
    if category is None:
        return False
    return retry_state.attempt_number <= len(_SCHEDULES[category])


def _wait_delay(retry_state: Any) -> float:
    if retry_state.outcome is None:
        return 0.0
    exc = retry_state.outcome.exception()
    if exc is None:
        return 0.0
    category = _classify(exc) or "rate_limit"
    schedule = _SCHEDULES[category]
    idx = retry_state.attempt_number - 1
    return schedule[min(idx, len(schedule) - 1)]


def _log_retry(retry_state: Any) -> None:
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    category = _classify(exc) if exc else None
    delay = _wait_delay(retry_state) if exc else 0.0
    logger.warning(
        "gemini.retry",
        attempt=retry_state.attempt_number,
        category=category,
        delay_seconds=delay,
        error_type=type(exc).__name__ if exc else None,
        error=str(exc)[:240] if exc else None,
    )


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class GeminiClient:
    """Singleton-friendly async Gemini client."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        embedding_model: str,
        embedding_dim: int,
        concurrency_limit: int,
        rpm_limit: int,
        timeout_seconds: float,
    ) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._embedding_model = embedding_model
        self._embedding_dim = embedding_dim
        self._semaphore = asyncio.Semaphore(concurrency_limit)
        from backend.llm.rate_limiter import TokenBucket

        self._rate_limiter = TokenBucket(max_calls=rpm_limit, window_seconds=60.0)
        self._timeout = float(timeout_seconds)

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def embedding_model_name(self) -> str:
        return self._embedding_model

    @property
    def rate_limiter(self):  # noqa: ANN201  — exposed for diagnostics
        return self._rate_limiter

    # ---------- generate ----------

    async def generate(
        self,
        prompt: str,
        *,
        system_instruction: str | None = None,
        response_schema: Any | None = None,
        response_mime_type: str | None = None,
        temperature: float | None = None,
    ) -> str:
        """Run a generation call and return the response text.

        If `response_schema` is provided (a Pydantic model class or a JSON
        schema dict), structured-output mode is enabled. `response_mime_type`
        defaults to "application/json" automatically in that case.
        """

        async def _call() -> str:
            # Rate-limiter wait is OUTSIDE asyncio.wait_for: backpressure
            # at the bucket does not eat into the per-call API timeout.
            async with self._semaphore:
                await self._rate_limiter.acquire()
                cfg_kwargs: dict[str, Any] = {
                    # We never use function-calling in this project; turning
                    # AFC off centrally silences the SDK's "AFC is enabled"
                    # informational log on every call.
                    "automatic_function_calling": genai_types.AutomaticFunctionCallingConfig(
                        disable=True
                    ),
                }
                if system_instruction is not None:
                    cfg_kwargs["system_instruction"] = system_instruction
                if response_schema is not None:
                    cfg_kwargs["response_mime_type"] = "application/json"
                    cfg_kwargs["response_schema"] = response_schema
                if response_mime_type is not None and "response_mime_type" not in cfg_kwargs:
                    cfg_kwargs["response_mime_type"] = response_mime_type
                if temperature is not None:
                    cfg_kwargs["temperature"] = temperature
                config = genai_types.GenerateContentConfig(**cfg_kwargs)
                response = await asyncio.wait_for(
                    self._client.aio.models.generate_content(
                        model=self._model, contents=prompt, config=config
                    ),
                    timeout=self._timeout,
                )
                return response.text or ""

        return await self._with_retries(_call)

    # ---------- embed ----------

    async def embed(
        self,
        text: str,
        *,
        task_type: str = "RETRIEVAL_DOCUMENT",
        output_dim: int | None = None,
    ) -> list[float]:
        """Embed a single string. Returns a list of `output_dim` floats."""
        dim = output_dim or self._embedding_dim

        async def _call() -> list[float]:
            async with self._semaphore:
                await self._rate_limiter.acquire()
                config = genai_types.EmbedContentConfig(
                    task_type=task_type, output_dimensionality=dim
                )
                response = await asyncio.wait_for(
                    self._client.aio.models.embed_content(
                        model=self._embedding_model, contents=text, config=config
                    ),
                    timeout=self._timeout,
                )
                if not response.embeddings:
                    raise RuntimeError("embed_content returned no embeddings")
                values = response.embeddings[0].values
                if not values or len(values) != dim:
                    raise RuntimeError(
                        f"unexpected embedding shape: got "
                        f"{len(values) if values else 0} dims, want {dim}"
                    )
                return [float(v) for v in values]

        return await self._with_retries(_call)

    # ---------- retry driver ----------

    async def _with_retries(self, fn: Callable[[], Awaitable[T]]) -> T:
        """Run `fn` under the spec §7.9 retry policy."""
        last: T | None = None
        async for attempt in AsyncRetrying(
            retry=_should_retry,
            wait=_wait_delay,
            stop=stop_never,
            before_sleep=_log_retry,
            reraise=True,
        ):
            with attempt:
                last = await fn()
        # AsyncRetrying with reraise=True will have raised on terminal failure,
        # so reaching here means at least one attempt succeeded.
        return last  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Process-wide singleton
# ---------------------------------------------------------------------------


_singleton: GeminiClient | None = None


def get_gemini_client() -> GeminiClient:
    global _singleton
    if _singleton is None:
        _singleton = GeminiClient(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            embedding_model=settings.gemini_embedding_model,
            embedding_dim=settings.gemini_embedding_dim,
            concurrency_limit=settings.gemini_concurrency_limit,
            rpm_limit=settings.gemini_rpm_limit,
            timeout_seconds=float(settings.gemini_timeout_seconds),
        )
    return _singleton


def reset_gemini_client() -> None:
    """Test-only: clears the cached singleton so the next call rebuilds it."""
    global _singleton
    _singleton = None
