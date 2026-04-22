"""Tests for POST /api/roi/query."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

from main import app

_NZ, _NY, _NX = 1, 5, 8
_FAKE_THETA = np.full((_NZ, _NY, _NX), 25.0, dtype=np.float32)
_FAKE_SALT  = np.full((_NZ, _NY, _NX), 36.0, dtype=np.float32)
_FAKE_W     = np.zeros((_NZ, _NY, _NX), dtype=np.float32)


def _mock_reader(*args, **kwargs):
    reader = MagicMock()
    reader.read.side_effect = lambda roi, var: {
        "theta": _FAKE_THETA,
        "salt":  _FAKE_SALT,
        "w":     _FAKE_W,
    }[var]
    return reader


_PAYLOAD = {
    "lat_min": 35.0, "lat_max": 45.0,
    "lon_min": -40.0, "lon_max": -30.0,
    "depth_min_m": 0.0, "depth_max_m": 500.0,
    "timestep": 0, "quality": -9,
}


@pytest.mark.asyncio
@patch("api.roi.LLC4320Reader", _mock_reader)
async def test_roi_query_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/roi/query", json=_PAYLOAD)
    assert r.status_code == 200


@pytest.mark.asyncio
@patch("api.roi.LLC4320Reader", _mock_reader)
async def test_roi_query_shape():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/roi/query", json=_PAYLOAD)
    assert r.json()["shape"] == {"nz": _NZ, "ny": _NY, "nx": _NX}


@pytest.mark.asyncio
@patch("api.roi.LLC4320Reader", _mock_reader)
async def test_roi_query_variable_names():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/roi/query", json=_PAYLOAD)
    assert set(r.json()["variables"]) == {"theta", "salt", "w"}


@pytest.mark.asyncio
@patch("api.roi.LLC4320Reader", _mock_reader)
async def test_roi_query_surface_slices():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/roi/query", json=_PAYLOAD)
    slices = r.json()["surface_slices"]
    assert "theta" in slices and "salt" in slices
    assert len(slices["theta"]) == _NY


@pytest.mark.asyncio
@patch("api.roi.LLC4320Reader", _mock_reader)
async def test_roi_query_plan_present():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/roi/query", json=_PAYLOAD)
    plan = r.json()["query_plan"]
    assert "recommended_quality" in plan
    assert "estimated_mb" in plan


@pytest.mark.asyncio
async def test_roi_query_invalid_lat_order():
    bad = {**_PAYLOAD, "lat_min": 50.0, "lat_max": 30.0}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/roi/query", json=bad)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_roi_query_positive_quality_rejected():
    bad = {**_PAYLOAD, "quality": 1}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/roi/query", json=bad)
    assert r.status_code == 422
