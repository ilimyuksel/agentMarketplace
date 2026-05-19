"""Gemini embedding helper — delegates to the singleton `GeminiClient`.

Public API (`embed_text`, `embed_texts`) is intentionally stable; the seed
script and any future caller can keep importing the same names.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable

from backend.llm.gemini_client import get_gemini_client


async def embed_text(
    text: str, *, task_type: str = "RETRIEVAL_DOCUMENT"
) -> list[float]:
    """Embed a single string. Routes through the shared GeminiClient."""
    return await get_gemini_client().embed(text, task_type=task_type)


async def embed_texts(
    texts: Iterable[str], *, task_type: str = "RETRIEVAL_DOCUMENT"
) -> list[list[float]]:
    """Embed many texts. The underlying client's Semaphore (default 3) caps
    parallelism and the token bucket throttles RPM."""
    return await asyncio.gather(
        *(embed_text(t, task_type=task_type) for t in texts)
    )
