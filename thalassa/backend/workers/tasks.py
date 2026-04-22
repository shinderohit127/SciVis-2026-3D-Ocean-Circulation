"""
Celery tasks for CPU-heavy THALASSA jobs.

All tasks accept plain JSON-serialisable dicts (not dataclasses) and store
their result in the Redis result backend.  Clients poll
GET /api/jobs/{task_id} to retrieve completed results.
"""
from __future__ import annotations

import logging

import numpy as np

from workers.celery_app import celery_app

log = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _field_stats(arr: np.ndarray) -> dict:
    valid = arr[np.isfinite(arr) & (arr != 0)]
    if len(valid) == 0:
        return {"min": 0.0, "max": 0.0, "mean": 0.0, "std": 0.0, "surface_slice": []}
    return {
        "min":           float(valid.min()),
        "max":           float(valid.max()),
        "mean":          float(valid.mean()),
        "std":           float(valid.std()),
        "surface_slice": arr[0].tolist(),
    }


# ── Tasks ──────────────────────────────────────────────────────────────────────

@celery_app.task(bind=True, name="tasks.compute_density_async")
def compute_density_async(self, request_dict: dict) -> dict:
    """
    Async density computation for large ROIs that exceed the sync size cap.

    Args:
        request_dict: serialised DensityRequest (roi dict + include list)

    Returns:
        serialised DensityResponse dict
    """
    from data_access.llc4320 import LLC4320Reader, ROI
    from services.derived_metrics.density import METRIC_VERSION, compute_density_3d
    from services.query_planner.planner import estimate_cost

    roi_d   = request_dict["roi"]
    include = request_dict.get(
        "include",
        ["rho", "sigma0", "rho_thermal", "rho_haline", "compensation_index"],
    )

    plan = estimate_cost(
        roi_d["lat_min"], roi_d["lat_max"],
        roi_d["lon_min"], roi_d["lon_max"],
        roi_d["depth_min_m"], roi_d["depth_max_m"],
        roi_d["quality"], n_vars=2,
    )

    roi = ROI(
        lat_min=roi_d["lat_min"], lat_max=roi_d["lat_max"],
        lon_min=roi_d["lon_min"], lon_max=roi_d["lon_max"],
        depth_min_m=roi_d["depth_min_m"], depth_max_m=roi_d["depth_max_m"],
        timestep=roi_d["timestep"], quality=plan.recommended_quality,
    )

    reader = LLC4320Reader()
    theta    = reader.read(roi, "theta")
    salt     = reader.read(roi, "salt")
    n_z, n_y, n_x = theta.shape
    lats     = roi.lat_array(n_y)
    depths_m = roi.depth_array(n_z)

    fields_3d = compute_density_3d(theta, salt, lats, depths_m=depths_m, include=include)

    return {
        "roi": roi_d,
        "fields": {
            name: _field_stats(arr)
            for name, arr in fields_3d.items()
            if isinstance(arr, np.ndarray) and name in include
        },
        "metric_version": METRIC_VERSION,
    }


@celery_app.task(bind=True, name="tasks.extract_isopycnal_async")
def extract_isopycnal_async(self, request_dict: dict) -> dict:
    """
    Async isopycnal mesh extraction (marching cubes is CPU-heavy).

    Args:
        request_dict: serialised IsopycnalRequest

    Returns:
        isopycnal mesh dict (vertices, faces, isovalue, …)
    """
    from data_access.llc4320 import LLC4320Reader, ROI
    from services.derived_metrics.density import compute_density_3d
    from services.query_planner.planner import estimate_cost
    from services.scene.isopycnal import extract_isopycnal

    roi_d      = request_dict["roi"]
    sigma0_val = float(request_dict["sigma0_value"])
    color_by   = request_dict.get("color_by")

    plan = estimate_cost(
        roi_d["lat_min"], roi_d["lat_max"],
        roi_d["lon_min"], roi_d["lon_max"],
        roi_d["depth_min_m"], roi_d["depth_max_m"],
        roi_d["quality"], n_vars=2,
    )

    roi = ROI(
        lat_min=roi_d["lat_min"], lat_max=roi_d["lat_max"],
        lon_min=roi_d["lon_min"], lon_max=roi_d["lon_max"],
        depth_min_m=roi_d["depth_min_m"], depth_max_m=roi_d["depth_max_m"],
        timestep=roi_d["timestep"], quality=plan.recommended_quality,
    )

    reader = LLC4320Reader()
    theta    = reader.read(roi, "theta")
    salt     = reader.read(roi, "salt")
    n_z, n_y, n_x = theta.shape
    lats     = roi.lat_array(n_y)
    depths_m = roi.depth_array(n_z)

    density_include = ["sigma0"]
    if color_by in ("CT", "SA", "alpha", "beta"):
        density_include.append(color_by)

    fields      = compute_density_3d(theta, salt, lats, depths_m=depths_m, include=density_include)
    sigma0_3d   = fields["sigma0"]
    color_field = fields.get(color_by) if color_by else None
    lons        = roi.lon_array(n_x)

    mesh = extract_isopycnal(sigma0_3d, sigma0_val, lons, lats, depths_m, color_field)
    mesh["roi"]      = roi_d
    mesh["color_by"] = color_by
    return mesh
