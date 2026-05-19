"""Standalone Gemini smoke test.

Usage:
    python scripts/test_gemini_connection.py

Calls `generate()` with a tiny prompt and `embed()` with a sample text.
Exits 0 on full success, non-zero on any failure.
"""

from __future__ import annotations

import asyncio
import sys

from backend.core.logger import get_logger
from backend.llm.gemini_client import get_gemini_client

logger = get_logger("test_gemini_connection")


async def run() -> int:
    client = get_gemini_client()
    logger.info(
        "test_gemini.start",
        model=client.model_name,
        embedding_model=client.embedding_model_name,
    )

    try:
        text = await client.generate(prompt="Reply with the single word PONG.")
        print(f"[OK] generate(): {text.strip()[:120]}")
    except Exception as exc:
        logger.exception("test_gemini.generate.failed")
        print(f"[FAIL] generate(): {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    try:
        vec = await client.embed("hello world")
        print(f"[OK] embed(): dims={len(vec)}")
    except Exception as exc:
        logger.exception("test_gemini.embed.failed")
        print(f"[FAIL] embed(): {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    return 0


def main() -> None:
    sys.exit(asyncio.run(run()))


if __name__ == "__main__":
    main()
