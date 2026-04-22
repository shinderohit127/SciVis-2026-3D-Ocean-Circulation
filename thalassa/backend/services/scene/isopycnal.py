"""
Isopycnal surface extraction — THALASSA scene service.

Uses marching cubes (scikit-image) to triangulate a σ₀ isovalue in a 3D
density field, then maps pixel-space vertex coordinates to geographic
(lon, lat, depth_m) space.

Output is a plain JSON-serialisable dict.  glTF packaging is deferred to
Weeks 11-12 when mesh decimation and transfer optimisation are added.
"""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np

log = logging.getLogger(__name__)


def extract_isopycnal(
    sigma0_3d: np.ndarray,
    isovalue: float,
    lons: np.ndarray,
    lats: np.ndarray,
    depths_m: np.ndarray,
    color_field: Optional[np.ndarray] = None,
) -> dict:
    """
    Extract a triangulated isopycnal surface from a 3D σ₀ field.

    Args:
        sigma0_3d:   (n_z, n_y, n_x) potential density anomaly (kg/m³ − 1000)
        isovalue:    target σ₀ value for the isosurface
        lons:        (n_x,) longitude values in degrees
        lats:        (n_y,) latitude values in degrees
        depths_m:    (n_z,) depth values in metres (positive down)
        color_field: optional (n_z, n_y, n_x) scalar for per-vertex colouring

    Returns:
        dict with:
          "vertices":     list of [lon, lat, depth_m]  (N × 3)
          "faces":        list of [i, j, k] triangle indices (M × 3)
          "color_values": list of float (N,) or None
          "isovalue":     the requested σ₀ level
          "vertex_count": N
          "face_count":   M
    """
    try:
        from skimage.measure import marching_cubes
    except ImportError as exc:
        raise RuntimeError("scikit-image is required for isopycnal extraction") from exc

    _EMPTY = {
        "vertices": [], "faces": [], "color_values": None,
        "isovalue": float(isovalue), "vertex_count": 0, "face_count": 0,
    }

    # Replace land/NaN with a value safely below the isovalue so it doesn't
    # produce spurious triangles at domain boundaries.
    sigma_filled = sigma0_3d.astype(np.float64)
    land = (sigma0_3d == 0) | ~np.isfinite(sigma0_3d)
    sigma_filled[land] = isovalue - 10.0

    ocean = sigma_filled[~land]
    if len(ocean) == 0:
        return _EMPTY

    if isovalue < float(ocean.min()) or isovalue > float(ocean.max()):
        log.warning(
            "isovalue %.2f outside ocean data range [%.2f, %.2f] — no surface",
            isovalue, float(ocean.min()), float(ocean.max()),
        )
        return _EMPTY

    try:
        verts, faces, _normals, _ = marching_cubes(
            sigma_filled, level=isovalue, allow_degenerate=False
        )
    except (ValueError, RuntimeError) as exc:
        log.warning("marching_cubes failed for isovalue=%.2f: %s", isovalue, exc)
        return _EMPTY

    # Map pixel-space coords → geographic coords via linear interpolation
    z_idx, y_idx, x_idx = verts[:, 0], verts[:, 1], verts[:, 2]
    geo_lons   = np.interp(x_idx, np.arange(len(lons)),    lons)
    geo_lats   = np.interp(y_idx, np.arange(len(lats)),    lats)
    geo_depths = np.interp(z_idx, np.arange(len(depths_m)), depths_m)

    geo_verts = np.column_stack([geo_lons, geo_lats, geo_depths])

    # Per-vertex colour by nearest-neighbour lookup in the colour field
    color_values = None
    if color_field is not None:
        zi = np.clip(np.round(z_idx).astype(int), 0, sigma0_3d.shape[0] - 1)
        yi = np.clip(np.round(y_idx).astype(int), 0, sigma0_3d.shape[1] - 1)
        xi = np.clip(np.round(x_idx).astype(int), 0, sigma0_3d.shape[2] - 1)
        color_values = color_field[zi, yi, xi].tolist()

    log.info(
        "extract_isopycnal σ₀=%.2f → %d vertices, %d faces",
        isovalue, len(geo_verts), len(faces),
    )
    return {
        "vertices":     geo_verts.tolist(),
        "faces":        faces.tolist(),
        "color_values": color_values,
        "isovalue":     float(isovalue),
        "vertex_count": len(geo_verts),
        "face_count":   len(faces),
    }
