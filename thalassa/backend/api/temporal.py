"""Temporal navigation endpoint — Week 9-10."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from api.schemas import JobStatus, TemporalWindowRequest

log = logging.getLogger(__name__)
router = APIRouter()

try:
    from workers.celery_app import celery_app as _celery_app
    from workers.tasks import compute_temporal_window_async
    _CELERY_AVAILABLE = True
except ImportError:
    _celery_app = None          # type: ignore[assignment]
    compute_temporal_window_async = None   # type: ignore[assignment]
    _CELERY_AVAILABLE = False


@router.post("/temporal/window", response_model=JobStatus)
async def submit_temporal_window(req: TemporalWindowRequest) -> JobStatus:
    """
    Submit an async job to compute per-timestep thermohaline descriptors.

    Samples n_samples evenly-spaced timesteps between t_start and t_end,
    queries each at very coarse resolution, and returns anomaly z-scores.
    Poll GET /api/jobs/{job_id} until status == "complete".
    Typical wall time: 15–60 s for 50 timesteps at quality -14.
    """
    if not _CELERY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Celery worker not available")

    task = compute_temporal_window_async.delay(req.model_dump())
    return JobStatus(job_id=task.id, status="queued")
