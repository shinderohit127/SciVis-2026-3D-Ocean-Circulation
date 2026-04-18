"""Tests for the /api/metadata endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.mark.asyncio
async def test_metadata_returns_three_variables():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/metadata")
    assert response.status_code == 200
    data = response.json()
    assert data["dataset"] == "ECCO LLC4320"
    assert len(data["variables"]) == 3
    variable_names = {v["name"] for v in data["variables"]}
    assert variable_names == {"theta", "salt", "w"}


@pytest.mark.asyncio
async def test_metadata_grid_dimensions():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/metadata")
    data = response.json()
    assert data["grid"]["nz"] == 90
    assert data["grid"]["nx"] == 12960
    assert data["grid"]["ny"] == 17280


@pytest.mark.asyncio
async def test_metadata_has_north_atlantic_preset():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/metadata")
    data = response.json()
    regions = data["regions"]
    assert "north_atlantic" in regions
    na = regions["north_atlantic"]
    assert na["lat"] == [0.0, 70.0]
    assert na["lon"] == [-60.0, 0.0]


@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
