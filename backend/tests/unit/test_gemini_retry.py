"""Verify tenacity-driven retry on a 429 from the Gemini client.

Mock the underlying SDK call to return [429, success]. Assert:
    - generate() returns the success value.
    - The underlying call ran exactly twice (one retry).
    - tenacity slept ~5s (the spec §7.9 first rate_limit delay) before the
      retry. We stub `asyncio.sleep` to record durations so the test stays fast.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest


class _FakeRateLimitError(Exception):
    """Duck-typed 429: GeminiClient._classify checks `.code`."""

    code = 429


@pytest.mark.asyncio
async def test_retry_on_429_then_success(monkeypatch):
    """First call raises 429, second call succeeds → result returned after 1 retry."""
    from backend.llm.gemini_client import GeminiClient

    client = GeminiClient(
        api_key="fake-key",
        model="gemini-2.5-flash",
        embedding_model="gemini-embedding-001",
        embedding_dim=768,
        concurrency_limit=3,
        # Generous rpm so the token bucket never blocks during the test.
        rpm_limit=10000,
        timeout_seconds=30.0,
    )

    calls = {"n": 0}

    async def fake_generate_content(*, model, contents, config=None):  # noqa: ARG001
        calls["n"] += 1
        if calls["n"] == 1:
            raise _FakeRateLimitError("429: rate limited")
        return SimpleNamespace(text="ok-after-retry")

    # Replace the SDK's bound method on this instance only.
    client._client.aio.models.generate_content = fake_generate_content  # type: ignore[attr-defined]

    # Capture sleep durations without actually sleeping.
    sleep_durations: list[float] = []
    real_sleep = asyncio.sleep

    async def fake_sleep(delay):
        sleep_durations.append(delay)
        await real_sleep(0)  # yield to keep the loop responsive

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    result = await client.generate(prompt="ping")

    assert result == "ok-after-retry"
    assert calls["n"] == 2, f"expected 2 underlying calls, got {calls['n']}"
    # The rate_limit schedule (5/10/20s) → first retry waits 5s.
    assert 5.0 in sleep_durations, (
        f"expected a 5.0s sleep between retries, got {sleep_durations}"
    )


@pytest.mark.asyncio
async def test_non_retryable_error_propagates(monkeypatch):
    """A 400-class error must NOT be retried."""
    from backend.llm.gemini_client import GeminiClient

    client = GeminiClient(
        api_key="fake-key",
        model="gemini-2.5-flash",
        embedding_model="gemini-embedding-001",
        embedding_dim=768,
        concurrency_limit=3,
        rpm_limit=10000,
        timeout_seconds=30.0,
    )

    class _FakeBadRequestError(Exception):
        code = 400

    calls = {"n": 0}

    async def fake_generate_content(*, model, contents, config=None):  # noqa: ARG001
        calls["n"] += 1
        raise _FakeBadRequestError("400: bad request")

    client._client.aio.models.generate_content = fake_generate_content  # type: ignore[attr-defined]

    with pytest.raises(_FakeBadRequestError):
        await client.generate(prompt="ping")

    assert calls["n"] == 1, "400 must not be retried"
