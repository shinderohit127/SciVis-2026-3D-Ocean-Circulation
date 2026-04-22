"""Tests for POST /api/derived/density."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

from main import app

_NZ, _NY, _NX = 3, 5, 8
# Warm surface water decreasing in temperature with depth — realistic profiles.
_theta = np.linspace(25.0, 5.0, _NZ * _NY * _NX, dtype=np.float32).reshape(_NZ, _NY, _NX)
_salt  = np.full((_NZ, _NY, _NX), 36.0, dtype=np.float32)


def _mock_reader(*args, **kwargs):
    reader = MagicMock()
    reader.read.side_effect = lambda roi, var: {"theta": _theta, "salt": _salt}[var]
    return reader


_ROI = {
    "lat_min": 35.0, "lat_max": 45.0,
    "lon_min": -40.0, "lon_max": -30.0,
    "depth_min_m": 0.0, "depth_max_m": 500.0,
    "timestep": 0, "quality": -9,
}
_REQ = {"roi": _ROI, "include": ["rho", "sigma0"]}


@pytest.mark.asyncio
@patch("api.derived.LLC4320Reader", _mock_reader)
async def test_derived_density_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/derived/density", json=_REQ)
    assert r.status_code == 200


@pytest.mark.asyncio
@patch("api.derived.LLC4320Reader", _mock_reader)
async def test_derived_density_fields_present():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/derived/density", json=_REQ)
    assert set(r.json()["fields"]) == {"rho", "sigma0"}


@pytest.mark.asyncio
@patch("api.derived.LLC4320Reader", _mock_reader)
async def test_derived_density_metric_version():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/derived/density", json=_REQ)
    assert r.json()["metric_version"] == "v0.1.0"


@pytest.mark.asyncio
@patch("api.derived.LLC4320Reader", _mock_reader)
async def test_derived_density_rho_in_range():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/derived/density", json=_REQ)
    rho = r.json()["fields"]["rho"]
    assert 1020.0 < rho["mean"] < 1030.0, f"rho mean out of range: {rho['mean']}"


@pytest.mark.asyncio
@patch("api.derived.LLC4320Reader", _mock_reader)
async def test_derived_density_surface_slice_shape():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/derived/density", json=_REQ)
    rho_slice = r.json()["fields"]["rho"]["surface_slice"]
    assert len(rho_slice) == _NY
    assert len(rho_slice[0]) == _NX


@pytest.mark.asyncio
async def test_derived_density_invalid_roi():
    bad = {**_REQ, "roi": {**_ROI, "lat_min": 50.0, "lat_max": 30.0}}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/derived/density", json=bad)
    assert r.status_code == 422
