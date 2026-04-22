"""
Query cost estimator for THALASSA — Week 3-4 skeleton.

Given an ROI and quality parameter, estimates the approximate data volume
OpenVisus will return and downgrades quality if the estimate exceeds
MAX_PAYLOAD_MB.  Auto-refinement (progressive multi-pass loading) is
deferred to Weeks 7-8.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass

import numpy as np

log = logging.getLogger(__name__)

BYTES_PER_PIXEL: int = 4       # float32
N_VARS_DEFAULT: int = 3        # theta, salt, w
MAX_PAYLOAD_MB: float = 200.0
MIN_QUALITY: int = -15


@dataclass
class QueryPlan:
    recommended_quality: int
    estimated_pixels: int
    estimated_mb: float
    capped: bool   # True when quality was downgraded to fit under MAX_PAYLOAD_MB
    notes: str


def estimate_cost(
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
    depth_min_m: float,
    depth_max_m: float,
    quality: int,
    n_vars: int = N_VARS_DEFAULT,
) -> QueryPlan:
    """
    Estimate data volume for an OpenVisus subvolume read.

    At quality q (negative int), OpenVisus returns approximately
    NX_full / 2^(|q|/3) pixels per axis (cube-root IDX decomposition).
    This is an approximation; actual sizes depend on internal block alignment.

    Args:
        lat_min, lat_max, lon_min, lon_max: geographic bounds in degrees
        depth_min_m, depth_max_m: depth range in metres
        quality: OpenVisus quality (≤ 0; more negative = coarser)
        n_vars: number of variables to count in the size estimate

    Returns:
        QueryPlan with recommended_quality, estimated size, and audit notes.
    """
    from data_access.llc4320 import NX, NY
    from data_access.depth_levels import DEPTH_LEVELS_M

    lat_span = abs(lat_max - lat_min)
    lon_span = abs(lon_max - lon_min) % 360 or 360.0

    full_nx = max(1, int(lon_span / 360.0 * NX))
    full_ny = max(1, int(lat_span / 180.0 * NY))
    full_nz = max(1, int(
        np.searchsorted(DEPTH_LEVELS_M, depth_max_m, side="right")
        - np.searchsorted(DEPTH_LEVELS_M, depth_min_m, side="left")
    ))

    def _estimate(q: int) -> tuple[int, float]:
        scale = 2.0 ** (abs(q) / 3.0)
        nx = max(1, math.ceil(full_nx / scale))
        ny = max(1, math.ceil(full_ny / scale))
        nz = max(1, math.ceil(full_nz / scale))
        total = nx * ny * nz
        mb = total * BYTES_PER_PIXEL * n_vars / 1e6
        return total, mb

    est_pixels, est_mb = _estimate(quality)
    notes = (
        f"ROI {lat_span:.1f}°lat × {lon_span:.1f}°lon × "
        f"{depth_max_m - depth_min_m:.0f}m depth"
    )

    capped = False
    recommended_quality = quality

    if est_mb > MAX_PAYLOAD_MB:
        for q in range(quality - 1, MIN_QUALITY - 1, -1):
            p, m = _estimate(q)
            if m <= MAX_PAYLOAD_MB:
                recommended_quality = q
                est_pixels, est_mb = p, m
                capped = True
                notes += f" | quality capped {quality}→{q} (est. >{MAX_PAYLOAD_MB:.0f} MB)"
                break

    log.info(
        "QueryPlan: pixels=%d est_mb=%.1f quality=%d capped=%s | %s",
        est_pixels, round(est_mb, 2), recommended_quality, capped, notes,
    )
    return QueryPlan(
        recommended_quality=recommended_quality,
        estimated_pixels=est_pixels,
        estimated_mb=round(est_mb, 2),
        capped=capped,
        notes=notes,
    )
