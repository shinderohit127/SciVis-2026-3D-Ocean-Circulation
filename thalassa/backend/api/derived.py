"""Derived density fields endpoint."""
from __future__ import annotations

import logging
import time

import numpy as np
from fastapi import APIRouter, HTTPException

from api.schemas import DensityRequest, DensityResponse, FieldStats
from cache import redis_cache as cache
from data_access.llc4320 import LLC4320Reader
from data_access.llc4320 import ROI as _ROI
from services.derived_metrics.density import METRIC_VERSION, compute_density_3d
from services.query_planner.planner import estimate_cost

log = logging.getLogger(__name__)
router = APIRouter()


def _field_stats(arr: np.ndarray) -> FieldStats:
    valid = arr[np.isfinite(arr) & (arr != 0)]
    if len(valid) == 0:
        return FieldStats(min=0.0, max=0.0, mean=0.0, std=0.0, surface_slice=[])
    return FieldStats(
        min=float(valid.min()),
        max=float(valid.max()),
        mean=float(valid.mean()),
        std=float(valid.std()),
        surface_slice=arr[0].tolist(),
    )


@router.post("/derived/density", response_model=DensityResponse)
async def derived_density(req: DensityRequest) -> DensityResponse:
    """
    Compute TEOS-10 density and thermohaline decomposition for an ROI.

    Returns per-field statistics and a 2D surface-level slice for each
    requested field. Available fields: rho, sigma0, rho_thermal, rho_haline,
    compensation_index, N2_squared (expensive — exclude unless needed),
    SA, CT, alpha, beta, pressure.

    metric_version is included in the response so clients can detect when
    cached results need invalidation.
    """
    t0 = time.monotonic()
    cache_params = req.model_dump()

    hit = cache.get("derived_density", cache_params)
    if hit is not None:
        return DensityResponse(**hit)

    plan = estimate_cost(
        req.roi.lat_min, req.roi.lat_max,
        req.roi.lon_min, req.roi.lon_max,
        req.roi.depth_min_m, req.roi.depth_max_m,
        req.roi.quality, n_vars=2,  # theta + salt only
    )

    roi = _ROI(
        lat_min=req.roi.lat_min, lat_max=req.roi.lat_max,
        lon_min=req.roi.lon_min, lon_max=req.roi.lon_max,
        depth_min_m=req.roi.depth_min_m, depth_max_m=req.roi.depth_max_m,
        timestep=req.roi.timestep, quality=plan.recommended_quality,
    )

    try:
        reader = LLC4320Reader()
        theta = reader.read(roi, "theta")
        salt  = reader.read(roi, "salt")
    except Exception as exc:
        log.error("OpenVisus read failed: %s", exc)
        raise HTTPException(status_code=503, detail=f"OpenVisus unavailable: {exc}")

    n_z, n_y, n_x = theta.shape
    lats     = roi.lat_array(n_y)
    depths_m = roi.depth_array(n_z)

    try:
        fields_3d = compute_density_3d(
            theta, salt, lats, depths_m=depths_m, include=req.include,
        )
    except Exception as exc:
        log.error("Density computation failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Density computation failed: {exc}")

    result = DensityResponse(
        roi=req.roi,
        fields={
            name: _field_stats(arr)
            for name, arr in fields_3d.items()
            if isinstance(arr, np.ndarray) and name in req.include
        },
        metric_version=METRIC_VERSION,
        elapsed_ms=int((time.monotonic() - t0) * 1000),
    )

    cache.set("derived_density", cache_params, result.model_dump())
    return result
