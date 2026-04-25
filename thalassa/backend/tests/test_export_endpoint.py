"""Tests for GET /api/scene/export/{job_id}.glb."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

from main import app

_MESH = {
    "vertices": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
    "faces":    [[0, 1, 2], [0, 1, 3]],
    "color_values": [0.1, 0.5, 0.9, 0.3],
    "isovalue": 27.0,
    "vertex_count": 4,
    "face_count": 2,
    "color_by": "CT",
}


def _make_mock_result(state: str, result=None):
    ar = MagicMock()
    ar.state = state
    ar.result = result
    return ar


@pytest.mark.asyncio
@patch("api.export.AsyncResult")
@patch("api.export._CELERY_AVAILABLE", True)
async def test_export_glb_200(mock_ar_cls):
    mock_ar_cls.return_value = _make_mock_result("SUCCESS", _MESH)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/scene/export/abc123.glb")
    assert r.status_code == 200
    assert r.headers["content-type"] == "model/gltf-binary"


@pytest.mark.asyncio
@patch("api.export.AsyncResult")
@patch("api.export._CELERY_AVAILABLE", True)
async def test_export_glb_content_is_valid(mock_ar_cls):
    mock_ar_cls.return_value = _make_mock_result("SUCCESS", _MESH)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/scene/export/abc123.glb")
    assert r.content[:4] == b"glTF"


@pytest.mark.asyncio
@patch("api.export.AsyncResult")
@patch("api.export._CELERY_AVAILABLE", True)
async def test_export_404_when_failed(mock_ar_cls):
    mock_ar_cls.return_value = _make_mock_result("FAILURE", Exception("compute error"))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/scene/export/bad_id.glb")
    assert r.status_code == 404


@pytest.mark.asyncio
@patch("api.export.AsyncResult")
@patch("api.export._CELERY_AVAILABLE", True)
async def test_export_409_when_pending(mock_ar_cls):
    mock_ar_cls.return_value = _make_mock_result("PENDING")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/scene/export/pending_id.glb")
    assert r.status_code == 409


@pytest.mark.asyncio
@patch("api.export._CELERY_AVAILABLE", False)
async def test_export_503_when_celery_unavailable():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/scene/export/any.glb")
    assert r.status_code == 503


@pytest.mark.asyncio
@patch("api.export.AsyncResult")
@patch("api.export._CELERY_AVAILABLE", True)
async def test_export_content_disposition_header(mock_ar_cls):
    mock_ar_cls.return_value = _make_mock_result("SUCCESS", _MESH)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/scene/export/abc123ff.glb")
    assert "attachment" in r.headers.get("content-disposition", "")
    assert ".glb" in r.headers.get("content-disposition", "")
