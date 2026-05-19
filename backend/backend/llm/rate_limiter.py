"""Sliding-window token bucket for outbound Gemini calls.

Scope is process-local: a single Python process orchestrates all LLM I/O
for the demo, so we don't need Redis for distributed coordination.

Algorithm:
    The bucket holds a deque of monotonic timestamps of recently-issued
    calls. On acquire(), expired entries (older than `window_seconds`) are
    pulled off the front. If the deque has fewer than `max_calls` entries,
    we record the new call and return immediately. Otherwise we sleep
    until the oldest entry is about to fall out, then loop and re-check
    (re-check protects against bursts of acquirers racing each other).

Concurrency:
    `asyncio.Lock` protects the deque so concurrent acquirers see a
    consistent view. The lock is released before sleeping, so other
    coroutines can make progress while one is waiting.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque


class TokenBucket:
    def __init__(self, *, max_calls: int, window_seconds: float) -> None:
        if max_calls <= 0:
            raise ValueError("max_calls must be positive")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self.max_calls = max_calls
        self.window = float(window_seconds)
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Block until a call slot is available, then claim it."""
        while True:
            sleep_for = 0.0
            async with self._lock:
                now = time.monotonic()
                self._expire(now)
                if len(self._timestamps) < self.max_calls:
                    self._timestamps.append(now)
                    return
                # Wait until the oldest entry exits the window.
                sleep_for = self._timestamps[0] + self.window - now
            # Use a tiny floor so we never spin if computed delay is 0.
            await asyncio.sleep(max(sleep_for, 0.001))

    def _expire(self, now: float) -> None:
        while self._timestamps and now - self._timestamps[0] >= self.window:
            self._timestamps.popleft()

    def in_flight(self) -> int:
        """Diagnostic: number of unexpired entries (advisory; no lock held)."""
        now = time.monotonic()
        return sum(1 for t in self._timestamps if now - t < self.window)
