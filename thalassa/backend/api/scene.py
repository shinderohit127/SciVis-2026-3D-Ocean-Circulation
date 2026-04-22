"""Scene endpoint — isopycnal mesh extraction (always dispatched to Celery)."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from api.schemas import IsopycnalRequest, JobStatus

log = logging.getLogger(__name__)
router = APIRouter()

# Module-level import so tests can patch api.scene.extract_isopycnal_async directly.
try:
    from workers.tasks import extract_isopycnal_async
    _CELERY_AVAILABLE = True
except ImportError:
    extract_isopycnal_async = None   # type: ignore[assignment]
    _CELERY_AVAILABLE = False


@router.post("/scene/isopycnal", response_model=JobStatus)
async def scene_isopycnal(req: IsopycnalRequest) -> JobStatus:
    """
    Extract a triangulated σ₀ isopycnal surface for the requested ROI.

    Marching cubes over a 3D density field is CPU-heavy, so this endpoint
    always dispatches to a Celery worker and returns a job_id immediately.
    Poll GET /api/jobs/{job_id} to check status and retrieve the mesh.

    Result dict (when complete):
      {
        "vertices":     [[lon, lat, depth_m], ...],   # N × 3
        "faces":        [[i, j, k], ...],             # M × 3
        "color_values": [float, ...] or null,
        "isovalue":     float,
        "vertex_count": int,
        "face_count":   int
      }

    color_by options: "CT", "SA", "alpha", "beta".
    """
    if not _CELERY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Celery not available")

    try:
        task = extract_isopycnal_async.delay(req.model_dump())
    except Exception as exc:
        log.error("Failed to dispatch isopycnal task: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=f"Could not queue job — is Redis running? ({exc})",
        )
    log.info(
        "Dispatched isopycnal task %s: σ₀=%.2f lat=[%s,%s] t=%d",
        task.id, req.sigma0_value, req.roi.lat_min, req.roi.lat_max, req.roi.timestep,
    )
    return JobStatus(job_id=task.id, status="queued", result=None, error=None)
