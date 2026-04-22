"""Tests for POST /api/derived/vertical_exchange."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

from main import app

_NZ, _NY, _NX = 3, 5, 8
_THETA = np.linspace(25.0, 5.0, _NZ * _NY * _NX, dtype=np.float32).reshape(_NZ, _NY, _NX)
_SALT  = np.full((_NZ, _NY, _NX), 36.0, dtype=np.float32)
_W     = np.random.default_rng(1).uniform(-1e-4, 1e-4, (_NZ, _NY, _NX)).astype(np.float32)


def _mock_reader(*args, **kwargs):
    reader = MagicMock()
    reader.read.side_effect = lambda roi, var: {
        "theta": _THETA, "salt": _SALT, "w": _W,
    }[var]
    return reader


_ROI = {
    "lat_min": 35.0, "lat_max": 45.0,
    "lon_min": -40.0, "lon_max": -30.0,
    "depth_min_m": 0.0, "depth_max_m": 500.0,
    "timestep": 0, "quality": -9,
}
_PAYLOAD = {"roi": _ROI}


@pytest.mark.asyncio
@patch("api.derived.LLC4320Reader", _mock_reader)
async def test_ve_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/derived/vertical_exchange", json=_PAYLOAD)
    assert r.status_code == 200


@pytest.mark.asyncio
@patch("api.derived.LLC4320Reader", _mock_reader)
async def test_ve_stats_keys():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/derived/vertical_exchange", json=_PAYLOAD)
    stats = r.json()["stats"]
    assert set(stats) == {"min", "max", "mean", "std", "p95"}


@pytest.mark.asyncio
@patch("api.derived.LLC4320Reader", _mock_reader)
async def test_ve_surface_slice_shape():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/derived/vertical_exchange", json=_PAYLOAD)
    data = r.json()
    assert len(data["surface_slice"]) == _NY
    assert len(data["surface_slice"][0]) == _NX


@pytest.mark.asyncio
@patch("api.derived.LLC4320Reader", _mock_reader)
async def test_ve_event_fraction_bounded():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/derived/vertical_exchange", json=_PAYLOAD)
    ef = r.json()["event_fraction"]
    assert 0.0 <= ef <= 1.0


@pytest.mark.asyncio
@patch("api.derived.LLC4320Reader", _mock_reader)
async def test_ve_metric_version():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/derived/vertical_exchange", json=_PAYLOAD)
    assert r.json()["metric_version"] == "v0.1.0"


@pytest.mark.asyncio
async def test_ve_invalid_roi():
    bad = {"roi": {**_ROI, "lat_min": 50.0, "lat_max": 30.0}}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/derived/vertical_exchange", json=bad)
    assert r.status_code == 422
