"""Tests for POST /api/overview."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

from main import app

_NZ, _NY, _NX = 4, 6, 8
_THETA = np.linspace(20.0, 2.0, _NZ * _NY * _NX, dtype=np.float32).reshape(_NZ, _NY, _NX)
_SALT  = np.full((_NZ, _NY, _NX), 35.5, dtype=np.float32)
_W     = np.random.default_rng(0).uniform(-1e-4, 1e-4, (_NZ, _NY, _NX)).astype(np.float32)


def _mock_reader(*args, **kwargs):
    reader = MagicMock()
    reader.read.side_effect = lambda roi, var: {
        "theta": _THETA, "salt": _SALT, "w": _W,
    }[var]
    return reader


_PAYLOAD = {"basin": "north_atlantic", "timestep": 0, "metric": "sigma0"}


@pytest.mark.asyncio
@patch("api.overview.LLC4320Reader", _mock_reader)
async def test_overview_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/overview", json=_PAYLOAD)
    assert r.status_code == 200


@pytest.mark.asyncio
@patch("api.overview.LLC4320Reader", _mock_reader)
async def test_overview_fields_present():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/overview", json=_PAYLOAD)
    data = r.json()
    assert data["basin"] == "north_atlantic"
    assert data["metric"] == "sigma0"
    assert len(data["depth_bands"]) > 0


@pytest.mark.asyncio
@patch("api.overview.LLC4320Reader", _mock_reader)
async def test_overview_depth_band_structure():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/overview", json=_PAYLOAD)
    band = r.json()["depth_bands"][0]
    assert "band" in band
    assert "depth_range" in band
    assert "mean_map" in band
    assert "stats" in band
    assert set(band["stats"]) == {"min", "max", "mean", "std"}


@pytest.mark.asyncio
@patch("api.overview.LLC4320Reader", _mock_reader)
async def test_overview_lats_lons_present():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/overview", json=_PAYLOAD)
    data = r.json()
    assert len(data["lats"]) == _NY
    assert len(data["lons"]) == _NX


@pytest.mark.asyncio
@patch("api.overview.LLC4320Reader", _mock_reader)
async def test_overview_vertical_exchange_metric():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/overview", json={**_PAYLOAD, "metric": "vertical_exchange"})
    assert r.status_code == 200
    assert r.json()["metric"] == "vertical_exchange"


@pytest.mark.asyncio
async def test_overview_invalid_basin():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/overview", json={**_PAYLOAD, "basin": "mars_ocean"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_overview_invalid_metric():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/overview", json={**_PAYLOAD, "metric": "nonsense"})
    assert r.status_code == 422
