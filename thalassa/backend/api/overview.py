"""Overview endpoint — coarse basin-level summaries for the global map view."""
from __future__ import annotations

import logging
import time

import numpy as np
from fastapi import APIRouter, HTTPException

from api.schemas import DepthBandSummary, OverviewRequest, OverviewResponse
from cache import redis_cache as cache
from data_access.llc4320 import BASIN_PRESETS, LLC4320Reader
from data_access.llc4320 import ROI as _ROI
from services.derived_metrics.density import compute_density_3d
from services.derived_metrics.vertical_exchange import compute_vertical_exchange_score

log = logging.getLogger(__name__)
router = APIRouter()

_OVERVIEW_QUALITY = -12   # very coarse; yields ~1–3 MB per full basin
_OVERVIEW_TTL     = 86400  # 24 h — overview data changes only with timestep

_DEPTH_BANDS = [
    ("surface",     0.0,    200.0),
    ("thermocline", 200.0,  1000.0),
    ("deep",        1000.0, 4000.0),
    ("abyss",       4000.0, 6625.0),
]

# Which density fields each metric requires
_METRIC_TO_DENSITY_FIELDS: dict[str, list[str]] = {
    "sigma0":             ["sigma0"],
    "compensation_index": ["compensation_index"],
    "rho_thermal":        ["rho_thermal"],
    "rho_haline":         ["rho_haline"],
    "vertical_exchange":  ["N2_squared"],
}


@router.post("/overview", response_model=OverviewResponse)
async def get_overview(req: OverviewRequest) -> OverviewResponse:
    """
    Compute a coarse basin-level summary at quality=-12.

    Returns a 2D depth-mean map and scalar statistics for each depth band
    (surface 0–200 m, thermocline 200–1000 m, deep 1–4 km, abyss 4–6.6 km).

    Results are cached for 24 hours.  Calling this endpoint repeatedly for
    different metrics over the same basin+timestep reuses the same coarse read
    when cached.
    """
    t0 = time.monotonic()
    cache_params = req.model_dump()

    hit = cache.get("overview", cache_params)
    if hit is not None:
        return OverviewResponse(**hit)

    preset = BASIN_PRESETS[req.basin]   # validated by schema
    lat_min, lat_max = preset["lat"]
    lon_min, lon_max = preset["lon"]

    need_w = req.metric == "vertical_exchange"

    roi = _ROI(
        lat_min=lat_min, lat_max=lat_max,
        lon_min=lon_min, lon_max=lon_max,
        depth_min_m=0.0, depth_max_m=6625.0,
        timestep=req.timestep, quality=_OVERVIEW_QUALITY,
    )

    try:
        reader = LLC4320Reader()
        theta = reader.read(roi, "theta")
        salt  = reader.read(roi, "salt")
        w     = reader.read(roi, "w") if need_w else None
    except Exception as exc:
        log.error("OpenVisus read failed: %s", exc)
        raise HTTPException(status_code=503, detail=f"OpenVisus unavailable: {exc}")

    n_z, n_y, n_x = theta.shape
    lats     = roi.lat_array(n_y)
    depths_m = roi.depth_array(n_z)
    lons     = roi.lon_array(n_x)

    density_include = _METRIC_TO_DENSITY_FIELDS[req.metric]
    fields = compute_density_3d(theta, salt, lats, depths_m=depths_m, include=density_include)

    if req.metric == "vertical_exchange":
        metric_3d = compute_vertical_exchange_score(w, fields["N2_squared"])
    else:
        metric_3d = fields[req.metric]

    # Mask land (zero values) → NaN for clean statistics
    metric_f = np.where(
        (metric_3d == 0) | ~np.isfinite(metric_3d),
        np.nan,
        metric_3d.astype(np.float64),
    )

    depth_bands: list[DepthBandSummary] = []
    for band_name, z_lo, z_hi in _DEPTH_BANDS:
        z0 = int(np.searchsorted(depths_m, z_lo, side="left"))
        z1 = min(int(np.searchsorted(depths_m, z_hi, side="right")), n_z)
        if z0 >= z1:
            continue
        slab  = metric_f[z0:z1]          # (nz_band, ny, nx)
        valid = slab[np.isfinite(slab)]
        if len(valid) == 0:
            continue
        depth_bands.append(DepthBandSummary(
            band=band_name,
            depth_range=[z_lo, z_hi],
            mean_map=np.nanmean(slab, axis=0).tolist(),
            stats={
                "min":  float(np.nanmin(valid)),
                "max":  float(np.nanmax(valid)),
                "mean": float(np.nanmean(valid)),
                "std":  float(np.nanstd(valid)),
            },
        ))

    result = OverviewResponse(
        basin=req.basin,
        metric=req.metric,
        timestep=req.timestep,
        quality=_OVERVIEW_QUALITY,
        shape={"nz": n_z, "ny": n_y, "nx": n_x},
        lats=lats.tolist(),
        lons=lons.tolist(),
        depth_bands=depth_bands,
        elapsed_ms=int((time.monotonic() - t0) * 1000),
    )

    cache.set("overview", cache_params, result.model_dump(), ttl=_OVERVIEW_TTL)
    return result
