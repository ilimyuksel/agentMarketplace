"""GET /ws/jobs/{job_id} — per-job event feed with on-connect replay.

Race-free replay:
    1. Register the connection in the channel.
    2. Acquire the per-connection send lock for the entire replay burst.
    3. Read historical events and send them through the websocket directly
       (still inside the held lock).
    4. Release the lock — live broadcasts that arrived during replay were
       queued waiting on the same lock and now proceed in order.

The send lock is the same one `ConnectionManager.broadcast` acquires via
`WSConnection.send`. That's how live + historical interleaving is
prevented without losing live events.
"""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.core.connection_manager import WSConnection, get_connection_manager
from backend.core.database import session_scope
from backend.core.event_types import channel_for_job
from backend.core.logger import get_logger
from backend.repositories.event_repo import EventRepository

logger = get_logger(__name__)

router = APIRouter()


@router.websocket("/ws/jobs/{job_id}")
async def job_feed(websocket: WebSocket, job_id: str) -> None:
    await websocket.accept()
    conn = WSConnection(websocket)
    cm = get_connection_manager()
    channel = channel_for_job(job_id)

    try:
        async with conn.send_lock:
            await cm.register(conn, channel)
            async with session_scope() as session:
                events = await EventRepository(session).list_for_job(job_id)
            replayed = 0
            for ev in events:
                envelope = {
                    "event_type": ev.event_type,
                    "timestamp": ev.created_at.isoformat() if ev.created_at else None,
                    "job_id": ev.job_id,
                    "task_id": ev.task_id,
                    "payload": ev.payload,
                }
                await websocket.send_json(envelope)
                replayed += 1
            logger.info("ws.job.replayed", job_id=job_id, count=replayed)

        # Live loop: any subsequent broadcasts reach us via cm.broadcast →
        # conn.send(); receive_text only exists to detect disconnect.
        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
    finally:
        await cm.unregister(conn, channel)
