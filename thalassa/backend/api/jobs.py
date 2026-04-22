"""Async job polling endpoint — check the status of a Celery task."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from api.schemas import JobStatus

log = logging.getLogger(__name__)
router = APIRouter()

# Module-level import so tests can patch api.jobs.AsyncResult directly.
try:
    from celery.result import AsyncResult
    from workers.celery_app import celery_app as _celery_app
    _CELERY_AVAILABLE = True
except ImportError:
    AsyncResult = None      # type: ignore[assignment,misc]
    _celery_app = None      # type: ignore[assignment]
    _CELERY_AVAILABLE = False

_STATE_MAP = {
    "PENDING": "queued",
    "STARTED": "running",
    "SUCCESS": "complete",
    "FAILURE": "failed",
    "REVOKED": "failed",
    "RETRY":   "running",
}


@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str) -> JobStatus:
    """
    Poll the status of an async Celery job by its task ID.

    Status values:
      "queued"   — task is waiting for a worker
      "running"  — worker is actively computing
      "complete" — result is ready; see the "result" field
      "failed"   — task raised an exception; see the "error" field
    """
    if not _CELERY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Celery not available")

    ar     = AsyncResult(job_id, app=_celery_app)
    status = _STATE_MAP.get(ar.state, "queued")

    result = None
    error  = None
    if ar.state == "SUCCESS":
        result = ar.result
    elif ar.state == "FAILURE":
        error = str(ar.result)

    return JobStatus(job_id=job_id, status=status, result=result, error=error)
