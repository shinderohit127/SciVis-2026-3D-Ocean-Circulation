"""
TEOS-10 thermohaline density derivation — THALASSA derived metrics service.

Production migration of notebooks/02_density_prototype.py.
Pure functions: no I/O, no file paths, no side effects.

metric_version is bumped whenever the algorithm changes so that cached
results from prior runs can be invalidated.
"""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import gsw

from data_access.depth_levels import DEPTH_LEVELS_M

log = logging.getLogger(__name__)

METRIC_VERSION = "v0.1.0"

ALL_FIELDS: frozenset[str] = frozenset({
    "SA", "CT", "pressure",
    "rho", "sigma0", "alpha", "beta",
    "rho_thermal", "rho_haline", "compensation_index",
    "N2_squared",
})

DEFAULT_INCLUDE: list[str] = [
    "rho", "sigma0", "rho_thermal", "rho_haline", "compensation_index",
]


def compute_density_fields(
    theta_profiles: np.ndarray,
    salt_profiles: np.ndarray,
    lats: np.ndarray,
    depths_m: Optional[np.ndarray] = None,
    include: Optional[list[str]] = None,
) -> dict:
    """
    Compute TEOS-10 density and thermohaline decomposition for profile arrays.

    Args:
        theta_profiles: (n_profiles, n_z) potential temperature in °C
        salt_profiles:  (n_profiles, n_z) practical salinity in g/kg
        lats:           (n_profiles,) latitude in degrees
        depths_m:       (n_z,) depth in metres (positive down).
                        Required when n_z != 90; defaults to DEPTH_LEVELS_M otherwise.
        include:        list of field names to compute. Defaults to DEFAULT_INCLUDE.

    Returns:
        dict with the requested field arrays of shape (n_profiles, n_z),
        plus always: "depth_m", "metric_version", "valid_mask".
    """
    if include is None:
        include = DEFAULT_INCLUDE
    want = frozenset(include)

    n_profiles, n_z = theta_profiles.shape

    if depths_m is None:
        if n_z != 90:
            raise ValueError(
                f"depths_m must be provided when n_z != 90 (got n_z={n_z})"
            )
        depths_m = DEPTH_LEVELS_M
    depths_m = np.asarray(depths_m, dtype=np.float64)

    valid_mask = (theta_profiles != 0) & (salt_profiles > 1)

    lat_2d = np.broadcast_to(lats[:, np.newaxis], (n_profiles, n_z))
    p_grid = gsw.p_from_z(
        np.broadcast_to((-depths_m)[np.newaxis, :], (n_profiles, n_z)),
        lat_2d,
    )

    # Use 0°E as longitude placeholder for SA_from_SP (SAAR correction < 0.01 g/kg)
    SA = gsw.SA_from_SP(salt_profiles, p_grid, np.zeros_like(lat_2d), lat_2d)
    CT = gsw.CT_from_pt(SA, theta_profiles)

    out: dict = {
        "depth_m": depths_m,
        "metric_version": METRIC_VERSION,
        "valid_mask": valid_mask,
    }
    if "SA" in want:
        out["SA"] = SA
    if "CT" in want:
        out["CT"] = CT
    if "pressure" in want:
        out["pressure"] = p_grid

    needs_rho = want & {
        "rho", "sigma0", "alpha", "beta",
        "rho_thermal", "rho_haline", "compensation_index",
    }
    if needs_rho:
        rho = gsw.rho(SA, CT, p_grid)
        if "rho" in want:
            out["rho"] = rho
        if "sigma0" in want:
            out["sigma0"] = gsw.sigma0(SA, CT)

        needs_ab = want & {"alpha", "beta", "rho_thermal", "rho_haline", "compensation_index"}
        if needs_ab:
            alpha = gsw.alpha(SA, CT, p_grid)
            beta  = gsw.beta(SA, CT, p_grid)
            if "alpha" in want:
                out["alpha"] = alpha
            if "beta" in want:
                out["beta"] = beta

            needs_contrib = want & {"rho_thermal", "rho_haline", "compensation_index"}
            if needs_contrib:
                SA_v    = np.where(valid_mask, SA,  np.nan)
                CT_v    = np.where(valid_mask, CT,  np.nan)
                rho_v   = np.where(valid_mask, rho, np.nan)
                SA_ref  = np.nanmean(SA_v,  axis=1, keepdims=True)
                CT_ref  = np.nanmean(CT_v,  axis=1, keepdims=True)
                rho_ref = np.nanmean(rho_v, axis=1, keepdims=True)

                rho_T = -rho_ref * alpha * (CT - CT_ref)
                rho_S =  rho_ref * beta  * (SA - SA_ref)

                if "rho_thermal" in want:
                    out["rho_thermal"] = rho_T
                if "rho_haline" in want:
                    out["rho_haline"] = rho_S
                if "compensation_index" in want:
                    out["compensation_index"] = (
                        np.abs(rho_S) / (np.abs(rho_T) + np.abs(rho_S) + 1e-10)
                    )

    if "N2_squared" in want:
        N2, _ = gsw.Nsquared(SA, CT, p_grid, lat=lat_2d, axis=1)
        out["N2_squared"] = np.concatenate([N2, N2[:, -1:]], axis=1)

    log.debug("compute_density_fields: n=%d nz=%d fields=%s", n_profiles, n_z, sorted(out))
    return out


def compute_density_3d(
    theta: np.ndarray,
    salt: np.ndarray,
    lats: np.ndarray,
    depths_m: Optional[np.ndarray] = None,
    include: Optional[list[str]] = None,
) -> dict:
    """
    Compute density fields over a 3D OpenVisus subvolume.

    Reshapes the (n_z, n_y, n_x) input to column profiles, calls
    compute_density_fields, then reshapes results back to (n_z, n_y, n_x).

    Args:
        theta:    (n_z, n_y, n_x) potential temperature in °C
        salt:     (n_z, n_y, n_x) practical salinity in g/kg
        lats:     (n_y,) latitude values for each row
        depths_m: (n_z,) actual depth values for the fetched levels.
                  Use roi.depth_array(n_z) to construct this from the ROI.
        include:  list of field names to compute

    Returns:
        dict of field → (n_z, n_y, n_x) arrays, plus "depth_m" and "metric_version".
    """
    n_z, n_y, n_x = theta.shape

    # Reshape 3D → 2D profiles: (n_y*n_x, n_z)
    theta_2d = theta.transpose(1, 2, 0).reshape(n_y * n_x, n_z)
    salt_2d  = salt.transpose(1, 2, 0).reshape(n_y * n_x, n_z)
    lats_1d  = np.repeat(lats, n_x)   # each lat repeated n_x times

    fields = compute_density_fields(
        theta_2d, salt_2d, lats_1d, depths_m=depths_m, include=include
    )

    result: dict = {
        "depth_m": fields["depth_m"],
        "metric_version": fields["metric_version"],
    }
    for key in (include or DEFAULT_INCLUDE):
        if key in fields and isinstance(fields[key], np.ndarray):
            # Reshape (n_profiles, n_z) → (n_z, n_y, n_x)
            result[key] = fields[key].reshape(n_y, n_x, n_z).transpose(2, 0, 1)
    return result
