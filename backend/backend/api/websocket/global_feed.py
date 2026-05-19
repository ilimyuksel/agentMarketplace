"""GET /ws/global — marketplace-wide event feed."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.core.connection_manager import WSConnection, get_connection_manager
from backend.core.event_types import CHANNEL_GLOBAL
from backend.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.websocket("/ws/global")
async def global_feed(websocket: WebSocket) -> None:
    await websocket.accept()
    conn = WSConnection(websocket)
    cm = get_connection_manager()
    await cm.register(conn, CHANNEL_GLOBAL)
    try:
        # The channel is broadcast-only; we don't expect client messages.
        # `receive_text` blocks until a frame arrives or the client disconnects.
        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
    finally:
        await cm.unregister(conn, CHANNEL_GLOBAL)
