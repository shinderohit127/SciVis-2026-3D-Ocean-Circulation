"""ROI query endpoint — fetch subvolume statistics from LLC4320."""
from __future__ import annotations

import logging
import time

import numpy as np
from fastapi import APIRouter, HTTPException

from api.schemas import QueryPlanInfo, QueryStats, ROIRequest, VariableStats
from cache import redis_cache as cache
from data_access.llc4320 import LLC4320Reader
from data_access.llc4320 import ROI as _ROI
from services.query_planner.planner import estimate_cost

log = logging.getLogger(__name__)
router = APIRouter()


def _var_stats(arr: np.ndarray) -> VariableStats:
    ocean = arr[arr != 0]
    if len(ocean) == 0:
        return VariableStats(min=0.0, max=0.0, mean=0.0, std=0.0, ocean_fraction=0.0)
    return VariableStats(
        min=float(ocean.min()),
        max=float(ocean.max()),
        mean=float(ocean.mean()),
        std=float(ocean.std()),
        ocean_fraction=float(len(ocean) / arr.size),
    )


@router.post("/roi/query", response_model=QueryStats)
async def roi_query(req: ROIRequest) -> QueryStats:
    """
    Fetch a subvolume for the requested ROI and return per-variable statistics
    plus a 2D surface-level preview slice (theta and salt only).

    The query planner may downgrade quality if the estimated payload exceeds
    200 MB. Clients should use quality=-9 for fast previews and quality=-6
    for moderate-detail ROIs.
    """
    t0 = time.monotonic()
    cache_params = req.model_dump()

    hit = cache.get("roi_query", cache_params)
    if hit is not None:
        return QueryStats(**hit)

    plan = estimate_cost(
        req.lat_min, req.lat_max, req.lon_min, req.lon_max,
        req.depth_min_m, req.depth_max_m, req.quality,
    )

    roi = _ROI(
        lat_min=req.lat_min, lat_max=req.lat_max,
        lon_min=req.lon_min, lon_max=req.lon_max,
        depth_min_m=req.depth_min_m, depth_max_m=req.depth_max_m,
        timestep=req.timestep, quality=plan.recommended_quality,
    )

    try:
        reader = LLC4320Reader()
        theta = reader.read(roi, "theta")
        salt  = reader.read(roi, "salt")
        w     = reader.read(roi, "w")
    except Exception as exc:
        log.error("OpenVisus read failed: %s", exc)
        raise HTTPException(status_code=503, detail=f"OpenVisus unavailable: {exc}")

    nz, ny, nx = theta.shape
    result = QueryStats(
        roi=req,
        query_plan=QueryPlanInfo(
            recommended_quality=plan.recommended_quality,
            estimated_mb=plan.estimated_mb,
            capped=plan.capped,
            notes=plan.notes,
        ),
        shape={"nz": nz, "ny": ny, "nx": nx},
        variables={
            "theta": _var_stats(theta),
            "salt":  _var_stats(salt),
            "w":     _var_stats(w),
        },
        surface_slices={
            "theta": theta[0].tolist(),
            "salt":  salt[0].tolist(),
        },
        elapsed_ms=int((time.monotonic() - t0) * 1000),
    )

    cache.set("roi_query", cache_params, result.model_dump())
    return result
