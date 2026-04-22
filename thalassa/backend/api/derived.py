"""Derived density fields endpoint."""
from __future__ import annotations

import logging
import time

import numpy as np
from fastapi import APIRouter, HTTPException

from api.schemas import (
    DensityRequest, DensityResponse, FieldStats,
    VerticalExchangeRequest, VerticalExchangeResponse,
)
from cache import redis_cache as cache
from data_access.llc4320 import LLC4320Reader
from data_access.llc4320 import ROI as _ROI
from services.derived_metrics.density import METRIC_VERSION, compute_density_3d
from services.derived_metrics.vertical_exchange import (
    METRIC_VERSION as VE_VERSION,
    N2_REF_DEFAULT,
    compute_vertical_exchange_score,
    event_candidates,
)
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


@router.post("/derived/vertical_exchange", response_model=VerticalExchangeResponse)
async def derived_vertical_exchange(req: VerticalExchangeRequest) -> VerticalExchangeResponse:
    """
    Compute the vertical exchange score for an ROI.

    VE = |w| × exp(-max(0, N²) / n2_ref)

    High VE identifies regions where strong vertical motion coincides with
    weak or unstable stratification — the primary loci of thermohaline exchange.
    event_fraction reports the fraction of voxels above the 95th-percentile
    threshold, giving a quick sense of how active the column is.
    """
    t0 = time.monotonic()
    cache_params = req.model_dump()

    hit = cache.get("derived_ve", cache_params)
    if hit is not None:
        return VerticalExchangeResponse(**hit)

    plan = estimate_cost(
        req.roi.lat_min, req.roi.lat_max,
        req.roi.lon_min, req.roi.lon_max,
        req.roi.depth_min_m, req.roi.depth_max_m,
        req.roi.quality, n_vars=3,  # theta + salt + w
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
        w     = reader.read(roi, "w")
    except Exception as exc:
        log.error("OpenVisus read failed: %s", exc)
        raise HTTPException(status_code=503, detail=f"OpenVisus unavailable: {exc}")

    n_z, n_y, n_x = theta.shape
    lats     = roi.lat_array(n_y)
    depths_m = roi.depth_array(n_z)

    try:
        fields_3d = compute_density_3d(
            theta, salt, lats, depths_m=depths_m, include=["N2_squared"],
        )
        ve = compute_vertical_exchange_score(
            w, fields_3d["N2_squared"], n2_ref=req.n2_ref_s2,
        )
    except Exception as exc:
        log.error("VE computation failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"VE computation failed: {exc}")

    valid = ve[np.isfinite(ve)]
    if len(valid) == 0:
        stats = {"min": 0.0, "max": 0.0, "mean": 0.0, "std": 0.0, "p95": 0.0}
        event_frac = 0.0
    else:
        stats = {
            "min":  float(valid.min()),
            "max":  float(valid.max()),
            "mean": float(valid.mean()),
            "std":  float(valid.std()),
            "p95":  float(np.nanpercentile(valid, 95)),
        }
        mask = event_candidates(ve, threshold_percentile=95.0)
        event_frac = float(mask.sum() / ve.size)

    result = VerticalExchangeResponse(
        roi=req.roi,
        stats=stats,
        surface_slice=ve[0].tolist(),
        event_fraction=event_frac,
        metric_version=VE_VERSION,
        elapsed_ms=int((time.monotonic() - t0) * 1000),
    )

    cache.set("derived_ve", cache_params, result.model_dump())
    return result
