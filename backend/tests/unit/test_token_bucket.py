"""TokenBucket timing tests.

Uses a 1-second window (vs the 60-second production window) so the test
stays fast. The mechanism is identical — only the scaling factor differs.
"""

from __future__ import annotations

import asyncio
import time

import pytest

from backend.llm.rate_limiter import TokenBucket


@pytest.mark.asyncio
async def test_13th_call_blocks_after_max_reached():
    """12 immediate calls + the 13th blocks ~1s until the first expires."""
    bucket = TokenBucket(max_calls=12, window_seconds=1.0)

    timings: list[float] = []
    overall_start = time.monotonic()
    for _ in range(15):
        before = time.monotonic()
        await bucket.acquire()
        timings.append(time.monotonic() - before)
    elapsed = time.monotonic() - overall_start

    # First 12 should be effectively instant.
    for i in range(12):
        assert timings[i] < 0.05, f"call {i + 1} took {timings[i]:.3f}s (expected <50ms)"

    # 13th call must wait until the oldest entry exits the 1-second window.
    assert 0.8 < timings[12] < 1.3, (
        f"13th call waited {timings[12]:.3f}s, expected ~1.0s"
    )

    # Total elapsed should be > 1s (since 13th wait pushes us past the window).
    assert elapsed >= 1.0, f"all 15 calls finished in {elapsed:.3f}s (expected ≥ 1.0s)"


@pytest.mark.asyncio
async def test_bucket_never_blocks_when_under_capacity():
    """Fewer calls than max should never sleep."""
    bucket = TokenBucket(max_calls=12, window_seconds=1.0)
    for _ in range(5):
        before = time.monotonic()
        await bucket.acquire()
        assert time.monotonic() - before < 0.02


@pytest.mark.asyncio
async def test_rejects_invalid_config():
    with pytest.raises(ValueError):
        TokenBucket(max_calls=0, window_seconds=1.0)
    with pytest.raises(ValueError):
        TokenBucket(max_calls=1, window_seconds=0)
