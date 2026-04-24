"""
Mesh export endpoint — Week 11-12.
Retrieves a completed isopycnal job result and serves it as a binary GLB file.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

log = logging.getLogger(__name__)
router = APIRouter()

try:
    from celery.result import AsyncResult
    from workers.celery_app import celery_app as _celery_app
    _CELERY_AVAILABLE = True
except ImportError:
    AsyncResult = None       # type: ignore[assignment,misc]
    _celery_app = None       # type: ignore[assignment]
    _CELERY_AVAILABLE = False


@router.get("/scene/export/{job_id}.glb")
async def export_glb(job_id: str) -> Response:
    """
    Download the completed isopycnal mesh as binary glTF (GLB 2.0).

    The job must have status "complete" (use GET /api/jobs/{job_id} to poll).
    Returns 404 if the job is not found, 409 if it has not completed yet.

    The GLB contains:
      - POSITION (VEC3, FLOAT) — [lon, lat, depth_m] vertices
      - Indices (SCALAR, UNSIGNED_INT)
      - _COLOR (SCALAR, FLOAT) — per-vertex scalar (CT / SA / α / β) when color_by is set

    Load in Blender with "Import → glTF 2.0 (.glb)" and apply your own colormap
    to the _COLOR attribute for publication-quality figures.
    """
    if not _CELERY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Celery not available")

    ar = AsyncResult(job_id, app=_celery_app)
    if ar.state != "SUCCESS":
        if ar.state in ("PENDING", "STARTED", "RETRY"):
            raise HTTPException(status_code=409, detail=f"Job not complete yet: {ar.state}")
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found or failed")

    mesh = ar.result
    if not mesh or not mesh.get("vertices"):
        raise HTTPException(status_code=422, detail="Job result has no mesh data")

    from services.scene.gltf_export import mesh_to_glb
    color_by = mesh.get("color_by") or "COLOR"
    glb_bytes = mesh_to_glb(
        vertices=mesh["vertices"],
        faces=mesh["faces"],
        color_values=mesh.get("color_values"),
        scalar_name=color_by,
    )

    return Response(
        content=glb_bytes,
        media_type="model/gltf-binary",
        headers={
            "Content-Disposition": f'attachment; filename="isopycnal_{job_id[:8]}.glb"',
            "Content-Length": str(len(glb_bytes)),
        },
    )
