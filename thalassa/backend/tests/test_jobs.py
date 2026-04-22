"""Tests for GET /api/jobs/{job_id}."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


def _make_ar(state: str, result=None):
    ar = MagicMock()
    ar.state = state
    ar.result = result
    return ar


@pytest.mark.asyncio
@patch("api.jobs.AsyncResult")
async def test_job_queued(mock_ar):
    mock_ar.return_value = _make_ar("PENDING")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/jobs/abc-123")
    assert r.status_code == 200
    assert r.json()["status"] == "queued"
    assert r.json()["job_id"] == "abc-123"


@pytest.mark.asyncio
@patch("api.jobs.AsyncResult")
async def test_job_running(mock_ar):
    mock_ar.return_value = _make_ar("STARTED")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/jobs/abc-123")
    assert r.json()["status"] == "running"


@pytest.mark.asyncio
@patch("api.jobs.AsyncResult")
async def test_job_complete(mock_ar):
    fake_result = {"vertex_count": 42, "face_count": 80}
    mock_ar.return_value = _make_ar("SUCCESS", result=fake_result)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/jobs/abc-123")
    data = r.json()
    assert data["status"] == "complete"
    assert data["result"]["vertex_count"] == 42


@pytest.mark.asyncio
@patch("api.jobs.AsyncResult")
async def test_job_failed(mock_ar):
    mock_ar.return_value = _make_ar("FAILURE", result=Exception("connection refused"))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/jobs/abc-123")
    data = r.json()
    assert data["status"] == "failed"
    assert data["error"] is not None
