"""
Per-timestep state descriptor for THALASSA temporal navigation.

Queries ECCO data at very coarse resolution (quality -14) so that a window
of 50–100 timesteps can be processed in seconds rather than minutes.
Each descriptor captures the thermohaline signature of the ROI at that hour.
"""
from __future__ import annotations

import logging
import numpy as np

log = logging.getLogger(__name__)

DESCRIPTOR_VERSION = "v0.1.0"
DESCRIPTOR_QUALITY = -14   # ~1–4 KB per variable per query — intentionally coarse


def _valid_stats(arr: np.ndarray) -> dict[str, float]:
    v = arr[np.isfinite(arr) & (arr != 0)]
    if not len(v):
        return {"mean": 0.0, "std": 0.0, "p10": 0.0, "p90": 0.0}
    return {
        "mean": float(np.mean(v)),
        "std":  float(np.std(v)),
        "p10":  float(np.percentile(v, 10)),
        "p90":  float(np.percentile(v, 90)),
    }


def compute_temporal_descriptor(
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
    depth_min_m: float,
    depth_max_m: float,
    timestep: int,
) -> dict:
    """
    Compute a compact thermohaline descriptor for one timestep.

    Returns a dict with sigma0, CT, and SA statistics that can be compared
    across timesteps to identify anomalous regimes.
    """
    from data_access.llc4320 import LLC4320Reader, ROI as _ROI
    from services.derived_metrics.density import compute_density_3d

    roi = _ROI(
        lat_min=lat_min,
        lat_max=lat_max,
        lon_min=lon_min,
        lon_max=lon_max,
        depth_min_m=depth_min_m,
        depth_max_m=depth_max_m,
        timestep=timestep,
        quality=DESCRIPTOR_QUALITY,
    )

    reader = LLC4320Reader()
    theta = reader.read(roi, "theta")
    salt  = reader.read(roi, "salt")

    n_z, n_y, n_x = theta.shape
    lats     = roi.lat_array(n_y)
    depths_m = roi.depth_array(n_z)

    fields = compute_density_3d(
        theta, salt, lats, depths_m=depths_m,
        include=["sigma0", "CT", "SA"],
    )

    log.debug(
        "descriptor: t=%d shape=%s sigma0_mean=%.3f",
        timestep, theta.shape, float(np.nanmean(fields["sigma0"])),
    )

    return {
        "timestep": timestep,
        "sigma0":   _valid_stats(fields["sigma0"]),
        "CT":       _valid_stats(fields["CT"]),
        "SA":       _valid_stats(fields["SA"]),
        "descriptor_version": DESCRIPTOR_VERSION,
    }
