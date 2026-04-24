"""
Celery tasks for CPU-heavy THALASSA jobs.

All tasks accept plain JSON-serialisable dicts (not dataclasses) and store
their result in the Redis result backend.  Clients poll
GET /api/jobs/{task_id} to retrieve completed results.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

# Ensure backend root is on sys.path in every forked worker process.
_BACKEND = str(Path(__file__).resolve().parent.parent)
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

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


@celery_app.task(bind=True, name="tasks.compute_temporal_window_async")
def compute_temporal_window_async(self, request_dict: dict) -> dict:
    """
    Compute per-timestep thermohaline descriptors for a window of time.

    Samples n_samples evenly-spaced timesteps between t_start and t_end,
    then computes anomaly scores as |z-scores| of sigma0_mean across the window.

    Args:
        request_dict: serialised TemporalWindowRequest

    Returns:
        serialised TemporalWindowResponse dict
    """
    import numpy as np
    from services.features.temporal import compute_temporal_descriptor, DESCRIPTOR_VERSION

    lat_min = request_dict["lat_min"]
    lat_max = request_dict["lat_max"]
    lon_min = request_dict["lon_min"]
    lon_max = request_dict["lon_max"]
    depth_min_m = request_dict.get("depth_min_m", 0.0)
    depth_max_m = request_dict.get("depth_max_m", 2000.0)
    t_start = request_dict["t_start"]
    t_end   = request_dict["t_end"]
    n_samples = min(request_dict.get("n_samples", 50), 200)

    timesteps = [
        int(round(t_start + i * (t_end - t_start) / (n_samples - 1)))
        for i in range(n_samples)
    ]
    timesteps = sorted(set(timesteps))   # deduplicate after rounding

    raw = []
    for t in timesteps:
        try:
            d = compute_temporal_descriptor(
                lat_min, lat_max, lon_min, lon_max,
                depth_min_m, depth_max_m, t,
            )
            raw.append(d)
        except Exception as exc:
            log.warning("descriptor failed for t=%d: %s", t, exc)

    if not raw:
        return {
            "t_start": t_start, "t_end": t_end, "n_computed": 0,
            "descriptors": [], "descriptor_version": DESCRIPTOR_VERSION,
        }

    means = np.array([d["sigma0"]["mean"] for d in raw])
    window_mean = float(np.mean(means))
    window_std  = float(np.std(means)) or 1.0
    anomaly_scores = np.abs((means - window_mean) / window_std)

    descriptors = [
        {
            "timestep":      d["timestep"],
            "sigma0_mean":   d["sigma0"]["mean"],
            "sigma0_std":    d["sigma0"]["std"],
            "ct_mean":       d["CT"]["mean"],
            "sa_mean":       d["SA"]["mean"],
            "anomaly_score": float(anomaly_scores[i]),
        }
        for i, d in enumerate(raw)
    ]

    return {
        "t_start":            t_start,
        "t_end":              t_end,
        "n_computed":         len(descriptors),
        "descriptors":        descriptors,
        "descriptor_version": DESCRIPTOR_VERSION,
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

    target_faces = request_dict.get("target_faces")
    if target_faces and mesh.get("face_count", 0) > target_faces:
        from services.scene.decimation import decimate_mesh
        new_v, new_f, new_c = decimate_mesh(
            mesh["vertices"], mesh["faces"],
            target_faces=target_faces,
            color_values=mesh.get("color_values"),
        )
        mesh["vertices"]     = new_v
        mesh["faces"]        = new_f
        mesh["color_values"] = new_c
        mesh["vertex_count"] = len(new_v)
        mesh["face_count"]   = len(new_f)
        mesh["decimated"]    = True

    mesh["roi"]      = roi_d
    mesh["color_by"] = color_by
    return mesh
