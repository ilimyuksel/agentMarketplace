"""End-to-end WebSocket smoke runner.

Plays the role of the two-terminal demo the spec describes:
    1. Starts uvicorn programmatically on a free port.
    2. Opens a WebSocket client to /ws/global.
    3. Publishes a `system.heartbeat` event via the in-process EventBus.
    4. Prints the envelope received over the wire.
    5. Shuts everything down cleanly.

Usage:
    python scripts/ws_smoke_demo.py
"""

from __future__ import annotations

import asyncio
import json
import socket
import sys

import uvicorn
import websockets

from backend.core.event_bus import get_event_bus
from backend.core.event_types import SYSTEM_HEARTBEAT
from backend.core.logger import get_logger
from backend.main import app

logger = get_logger("ws_smoke_demo")


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def run() -> int:
    port = _free_port()
    print(f"starting uvicorn on 127.0.0.1:{port} ...", flush=True)

    config = uvicorn.Config(
        app, host="127.0.0.1", port=port, log_level="warning", lifespan="on"
    )
    server = uvicorn.Server(config)
    server_task = asyncio.create_task(server.serve())

    for _ in range(60):
        if server.started:
            break
        await asyncio.sleep(0.05)
    if not server.started:
        print("[FAIL] uvicorn did not start", file=sys.stderr)
        return 1

    try:
        uri = f"ws://127.0.0.1:{port}/ws/global"
        print(f"connecting to {uri} ...", flush=True)
        async with websockets.connect(uri) as ws:
            await asyncio.sleep(0.05)  # let server register the connection
            print('publishing system.heartbeat {"test": true} ...', flush=True)
            await get_event_bus().publish(
                SYSTEM_HEARTBEAT, {"test": True}, persist=False
            )
            raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
            envelope = json.loads(raw)
            print("received envelope:")
            print(json.dumps(envelope, indent=2))
        print("[OK]")
        return 0
    finally:
        server.should_exit = True
        try:
            await asyncio.wait_for(server_task, timeout=5.0)
        except asyncio.TimeoutError:
            server_task.cancel()


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
