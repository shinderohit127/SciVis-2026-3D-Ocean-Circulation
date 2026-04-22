"""
Vertical exchange score — THALASSA derived metric.

Combines vertical velocity magnitude with stratification stability to surface
regions where strong upwelling or downwelling occurs in weakly stratified water.

Formula:
    VE(x,y,z,t) = |w(x,y,z,t)| × exp(-max(0, N²) / N²_ref)

Rationale:
    N² ≤ 0 (unstable/neutral):  stability_factor = 1  → VE = |w|
    N² = N²_ref (pycnocline):   stability_factor ≈ 0.37
    N² >> N²_ref (stratified):  stability_factor → 0

N²_ref default = 1e-5 s⁻² is a typical thermocline value.
"""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np

log = logging.getLogger(__name__)

METRIC_VERSION = "v0.1.0"
N2_REF_DEFAULT: float = 1e-5   # s⁻²


def compute_vertical_exchange_score(
    w: np.ndarray,
    N2: np.ndarray,
    n2_ref: float = N2_REF_DEFAULT,
    valid_mask: Optional[np.ndarray] = None,
) -> np.ndarray:
    """
    Compute the vertical exchange score over a 3D subvolume.

    Args:
        w:          (n_z, n_y, n_x) vertical velocity in m/s
        N2:         (n_z, n_y, n_x) Brunt-Väisälä frequency squared in s⁻²
        n2_ref:     stratification threshold in s⁻² (default 1e-5)
        valid_mask: optional bool mask; VE set to NaN where False

    Returns:
        (n_z, n_y, n_x) float32 vertical exchange score
    """
    stability = np.exp(-np.maximum(0.0, N2) / n2_ref)
    ve = np.abs(w) * stability

    if valid_mask is not None:
        ve = np.where(valid_mask, ve, np.nan)

    log.debug(
        "compute_vertical_exchange_score: shape=%s ve_max=%.3e n2_ref=%.1e",
        ve.shape, float(np.nanmax(ve)), n2_ref,
    )
    return ve.astype(np.float32)


def event_candidates(
    ve: np.ndarray,
    threshold_percentile: float = 95.0,
) -> np.ndarray:
    """
    Return a bool mask of voxels above the given VE percentile threshold.

    Args:
        ve:                   (n_z, n_y, n_x) vertical exchange score
        threshold_percentile: cutoff percentile (default 95th)

    Returns:
        (n_z, n_y, n_x) bool — True where VE exceeds the threshold
    """
    valid = ve[np.isfinite(ve)]
    if len(valid) == 0:
        return np.zeros(ve.shape, dtype=bool)
    threshold = float(np.nanpercentile(valid, threshold_percentile))
    return np.isfinite(ve) & (ve >= threshold)
