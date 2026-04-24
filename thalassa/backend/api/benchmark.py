"""
Benchmark endpoint — Week 11-12.

Runs a standard query at multiple quality levels against a configurable ROI
and returns a latency table suitable for inclusion in paper §V.
Runs synchronously (no Celery) since queries at coarse quality are fast.
"""
from __future__ import annotations

import logging
import time

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.schemas import BenchmarkResponse, BenchmarkRun
from data_access.llc4320 import LLC4320Reader, ROI as _ROI
from services.derived_metrics.density import compute_density_3d
from services.query_planner.planner import estimate_cost

log = logging.getLogger(__name__)
router = APIRouter()


class BenchmarkRequest(BaseModel):
    lat_min: float = 35.0
    lat_max: float = 45.0
    lon_min: float = -40.0
    lon_max: float = -30.0
    depth_min_m: float = 0.0
    depth_max_m: float = 2000.0
    timestep: int = 0
    qualities: list[int] = [-15, -12, -9, -7]   # qualities to benchmark


@router.post("/benchmark", response_model=BenchmarkResponse)
async def run_benchmark(req: BenchmarkRequest) -> BenchmarkResponse:
    """
    Run a density pipeline benchmark at multiple quality levels.

    Returns per-quality timing, shape, and estimated data size.
    Useful for paper §V performance characterisation.
    Max quality benchmarked is capped at -7 to keep response time under 30 s.
    """
    qualities = [min(q, -7) for q in req.qualities]  # cap to avoid huge syncs
    runs: list[BenchmarkRun] = []
    wall_start = time.monotonic()

    reader = LLC4320Reader()

    for q in qualities:
        plan = estimate_cost(
            req.lat_min, req.lat_max,
            req.lon_min, req.lon_max,
            req.depth_min_m, req.depth_max_m,
            q, n_vars=2,
        )
        roi = _ROI(
            lat_min=req.lat_min, lat_max=req.lat_max,
            lon_min=req.lon_min, lon_max=req.lon_max,
            depth_min_m=req.depth_min_m, depth_max_m=req.depth_max_m,
            timestep=req.timestep, quality=plan.recommended_quality,
        )

        t0 = time.monotonic()
        try:
            theta = reader.read(roi, "theta")
            salt  = reader.read(roi, "salt")
            n_z, n_y, n_x = theta.shape
            lats     = roi.lat_array(n_y)
            depths_m = roi.depth_array(n_z)
            compute_density_3d(theta, salt, lats, depths_m=depths_m, include=["sigma0"])
        except Exception as exc:
            log.warning("benchmark q=%d failed: %s", q, exc)
            runs.append(BenchmarkRun(
                quality=plan.recommended_quality,
                shape={"nz": 0, "ny": 0, "nx": 0},
                elapsed_ms=-1,
                estimated_mb=plan.estimated_mb,
                note=f"failed: {exc}",
            ))
            continue

        elapsed_ms = int((time.monotonic() - t0) * 1000)
        runs.append(BenchmarkRun(
            quality=plan.recommended_quality,
            shape={"nz": n_z, "ny": n_y, "nx": n_x},
            elapsed_ms=elapsed_ms,
            estimated_mb=plan.estimated_mb,
            note=plan.notes,
        ))
        log.info("benchmark q=%d → %dms, shape=%s", plan.recommended_quality, elapsed_ms, theta.shape)

    total_ms = int((time.monotonic() - wall_start) * 1000)
    return BenchmarkResponse(
        roi=req.model_dump(),
        runs=runs,
        total_elapsed_ms=total_ms,
    )
