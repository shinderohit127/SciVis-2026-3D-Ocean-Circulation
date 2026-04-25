"""Tests for POST /api/benchmark."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

from main import app

_NZ, _NY, _NX = 3, 4, 6
_THETA = np.linspace(20.0, 5.0, _NZ * _NY * _NX, dtype=np.float32).reshape(_NZ, _NY, _NX)
_SALT  = np.full((_NZ, _NY, _NX), 35.0, dtype=np.float32)


def _mock_reader(*_, **__):
    r = MagicMock()
    r.read.side_effect = lambda roi, var: {"theta": _THETA, "salt": _SALT}[var]
    return r


_PAYLOAD = {
    "lat_min": 35, "lat_max": 45,
    "lon_min": -40, "lon_max": -30,
    "qualities": [-15, -12],
}


@pytest.mark.asyncio
@patch("api.benchmark.LLC4320Reader", _mock_reader)
async def test_benchmark_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/benchmark", json=_PAYLOAD)
    assert r.status_code == 200


@pytest.mark.asyncio
@patch("api.benchmark.LLC4320Reader", _mock_reader)
async def test_benchmark_returns_runs():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/benchmark", json=_PAYLOAD)
    data = r.json()
    assert "runs" in data
    assert len(data["runs"]) == len(_PAYLOAD["qualities"])


@pytest.mark.asyncio
@patch("api.benchmark.LLC4320Reader", _mock_reader)
async def test_benchmark_run_structure():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/benchmark", json=_PAYLOAD)
    run = r.json()["runs"][0]
    assert "quality" in run
    assert "elapsed_ms" in run
    assert "shape" in run
    assert "estimated_mb" in run
    assert run["elapsed_ms"] >= 0


@pytest.mark.asyncio
@patch("api.benchmark.LLC4320Reader", _mock_reader)
async def test_benchmark_shape_matches_mock():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/benchmark", json=_PAYLOAD)
    run = r.json()["runs"][0]
    s = run["shape"]
    assert s["nz"] == _NZ
    assert s["ny"] == _NY
    assert s["nx"] == _NX


@pytest.mark.asyncio
@patch("api.benchmark.LLC4320Reader", _mock_reader)
async def test_benchmark_total_elapsed_present():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/benchmark", json=_PAYLOAD)
    assert r.json()["total_elapsed_ms"] >= 0


@pytest.mark.asyncio
@patch("api.benchmark.LLC4320Reader", _mock_reader)
async def test_benchmark_quality_capped_at_minus7():
    """Benchmark endpoint caps quality at -7 to prevent runaway sync requests."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/benchmark", json={**_PAYLOAD, "qualities": [-3, -5]})
    for run in r.json()["runs"]:
        assert run["quality"] <= -7
