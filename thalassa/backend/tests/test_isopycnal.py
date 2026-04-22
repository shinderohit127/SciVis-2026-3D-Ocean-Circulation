"""Tests for POST /api/scene/isopycnal."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from main import app

_ROI = {
    "lat_min": 35.0, "lat_max": 45.0,
    "lon_min": -40.0, "lon_max": -30.0,
    "depth_min_m": 0.0, "depth_max_m": 2000.0,
    "timestep": 0, "quality": -9,
}
_PAYLOAD = {"roi": _ROI, "sigma0_value": 27.0}


def _make_fake_task():
    task = MagicMock()
    task.id = "fake-task-id-0001"
    return task


@pytest.mark.asyncio
@patch("api.scene.extract_isopycnal_async")
async def test_isopycnal_dispatches_job(mock_task_fn):
    mock_task_fn.delay.return_value = _make_fake_task()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/scene/isopycnal", json=_PAYLOAD)
    assert r.status_code == 200
    assert r.json()["status"] == "queued"
    assert r.json()["job_id"] == "fake-task-id-0001"


@pytest.mark.asyncio
@patch("api.scene.extract_isopycnal_async")
async def test_isopycnal_delay_called_once(mock_task_fn):
    mock_task_fn.delay.return_value = _make_fake_task()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post("/api/scene/isopycnal", json=_PAYLOAD)
    mock_task_fn.delay.assert_called_once()


@pytest.mark.asyncio
@patch("api.scene.extract_isopycnal_async")
async def test_isopycnal_with_color_by(mock_task_fn):
    mock_task_fn.delay.return_value = _make_fake_task()
    payload = {**_PAYLOAD, "color_by": "CT"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/scene/isopycnal", json=payload)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_isopycnal_invalid_roi():
    bad = {**_PAYLOAD, "roi": {**_ROI, "depth_min_m": 3000.0, "depth_max_m": 100.0}}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/scene/isopycnal", json=bad)
    assert r.status_code == 422
