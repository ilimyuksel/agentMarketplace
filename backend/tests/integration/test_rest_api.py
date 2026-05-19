"""HTTP roundtrip tests for the REST surface.

Uses `httpx.AsyncClient` + `ASGITransport` so the test client runs in the
same asyncio loop as the FastAPI app (matches our session-scoped pytest
loop) — no thread boundary, no cross-loop issues.

`run_job` is patched to a no-op so POST /api/v1/jobs returns instantly
and no live Gemini calls fire from the background task.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from backend.constants import DEMO_USER_ID
from backend.core.database import session_scope
from backend.enums.job_state import JobState
from backend.models.orm.event import Event
from backend.models.orm.job import Job


@pytest.fixture
async def http_client():
    from backend.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture(autouse=True)
def _stub_run_job(monkeypatch):
    """Stop POST /jobs from actually firing Gemini in the background.

    The stub records the job_id so a test can assert it was invoked.
    """
    invoked: list[str] = []

    async def _noop(*, job_id: str, **_):
        invoked.append(job_id)

    monkeypatch.setattr("backend.api.rest.jobs.run_job", _noop)
    return invoked


# ---------------------------------------------------------------------------
# System
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_returns_ok(http_client):
    r = await http_client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"


@pytest.mark.asyncio
async def test_stats_returns_ints_and_money(http_client):
    r = await http_client.get("/api/v1/stats")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    data = body["data"]
    for key in (
        "total_jobs",
        "completed_jobs",
        "failed_jobs",
        "active_jobs",
        "total_agents",
        "active_agents",
        "ledger_length",
        "total_volume",
    ):
        assert key in data, f"missing field: {key}"
    assert data["total_agents"] >= 9, "seed should have at least 9 agents"
    assert isinstance(data["total_volume"], (int, float))


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_agents_returns_nine(http_client):
    r = await http_client.get("/api/v1/agents")
    assert r.status_code == 200
    body = r.json()
    data = body["data"]
    assert data["count"] == 9
    ids = {a["id"] for a in data["agents"]}
    assert "ProjectManager_001" in ids
    assert "QAJudge_001" in ids
    assert "ContentWriter_002" in ids
    # Money is serialized as a number, not a string.
    for a in data["agents"]:
        assert isinstance(a["wallet_balance"], (int, float))


@pytest.mark.asyncio
async def test_get_unknown_agent_returns_404_envelope(http_client):
    r = await http_client.get("/api/v1/agents/does_not_exist")
    assert r.status_code == 404
    body = r.json()
    assert body["success"] is False
    assert body["error"]["code"] == "AGENT_NOT_FOUND"


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ledger_recent_returns_reverse_chrono(http_client):
    r = await http_client.get("/api/v1/ledger/recent?limit=10")
    assert r.status_code == 200
    body = r.json()
    txs = body["data"]["transactions"]
    if len(txs) > 1:
        # block_number descending
        block_numbers = [t["block_number"] for t in txs]
        assert block_numbers == sorted(block_numbers, reverse=True)


@pytest.mark.asyncio
async def test_ledger_verify_returns_valid_for_clean_chain(http_client):
    r = await http_client.post("/api/v1/ledger/verify")
    assert r.status_code == 200
    body = r.json()
    data = body["data"]
    assert data["is_valid"] is True
    assert data["first_bad_block"] is None
    assert data["blocks_verified"] >= 1


# ---------------------------------------------------------------------------
# Jobs (no LLM — orchestrator stubbed)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_job_happy_path(http_client, _stub_run_job):
    r = await http_client.post(
        "/api/v1/jobs",
        json={"prompt": "Create a landing page", "budget": 200.00},
    )
    assert r.status_code == 202
    body = r.json()
    assert body["success"] is True
    data = body["data"]
    assert data["state"] == JobState.CREATED.value
    assert data["budget"] == 200.00
    assert data["budget_tier"] == "STANDARD"
    assert data["websocket_url"].startswith("/ws/jobs/")
    job_id = data["job_id"]
    # The orchestrator stub should have observed this job_id (giving the
    # background task a moment to be scheduled).
    import asyncio

    await asyncio.sleep(0.05)
    assert job_id in _stub_run_job

    # Cleanup: drop the row + any events it spawned.
    async with session_scope() as session:
        await session.execute(delete(Event).where(Event.job_id == job_id))
        await session.execute(delete(Job).where(Job.id == job_id))


@pytest.mark.asyncio
async def test_create_job_rejects_zero_budget(http_client):
    r = await http_client.post(
        "/api/v1/jobs",
        json={"prompt": "Anything", "budget": 0},
    )
    assert r.status_code == 422
    body = r.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_create_job_rejects_empty_prompt(http_client):
    r = await http_client.post(
        "/api/v1/jobs",
        json={"prompt": "", "budget": 100.00},
    )
    assert r.status_code == 422
    body = r.json()
    assert body["success"] is False


@pytest.mark.asyncio
async def test_get_unknown_job_returns_404_envelope(http_client):
    r = await http_client.get("/api/v1/jobs/job_definitely_does_not_exist")
    assert r.status_code == 404
    body = r.json()
    assert body["error"]["code"] == "JOB_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_job_output_404_before_aggregator_runs(http_client):
    """Create a Job row directly (no orchestrator) and ask for its output."""
    job_id = f"job_test_{uuid.uuid4().hex[:8]}"
    async with session_scope() as session:
        session.add(
            Job(
                id=job_id,
                user_id=DEMO_USER_ID,
                user_prompt="output-not-ready test",
                budget=Decimal("100.00"),
                state=JobState.EXECUTING.value,
            )
        )
    try:
        r = await http_client.get(f"/api/v1/jobs/{job_id}/output")
        assert r.status_code == 404
        body = r.json()
        assert body["error"]["code"] == "OUTPUT_NOT_READY"
    finally:
        async with session_scope() as session:
            await session.execute(delete(Job).where(Job.id == job_id))


@pytest.mark.asyncio
async def test_get_job_detail_includes_refund_explanation(http_client):
    job_id = f"job_test_{uuid.uuid4().hex[:8]}"
    async with session_scope() as session:
        session.add(
            Job(
                id=job_id,
                user_id=DEMO_USER_ID,
                user_prompt="refund-note test",
                budget=Decimal("100.00"),
                state=JobState.EXECUTING.value,
            )
        )
    try:
        r = await http_client.get(f"/api/v1/jobs/{job_id}")
        assert r.status_code == 200
        data = r.json()["data"]
        assert "refund_explanation" in data
        assert data["refund_amount"] == 0.0
        assert data["pm_profit_realized"] == 0.0
    finally:
        async with session_scope() as session:
            await session.execute(delete(Job).where(Job.id == job_id))


# ---------------------------------------------------------------------------
# Wallets
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_wallets_returns_seeded_wallets(http_client):
    r = await http_client.get("/api/v1/wallets")
    assert r.status_code == 200
    body = r.json()
    wallets = body["data"]["wallets"]
    ids = {w["id"] for w in wallets}
    assert "wallet_user_demo" in ids
    assert "wallet_projectmanager_001" in ids
    # Balance is a number, not a string.
    for w in wallets:
        assert isinstance(w["balance"], (int, float))
