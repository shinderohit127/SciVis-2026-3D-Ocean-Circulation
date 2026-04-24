"""
Mesh decimation for THALASSA — Week 11-12.

Uses PyVista (VTK Quadric Error Metrics) to reduce isopycnal mesh density
while preserving surface shape. Color scalars are re-assigned after decimation
via nearest-neighbour lookup since VTK does not carry through arbitrary
point-data in all decimation modes.
"""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np

log = logging.getLogger(__name__)


def decimate_mesh(
    vertices: list,
    faces: list,
    target_faces: int,
    color_values: Optional[list] = None,
) -> tuple[list, list, Optional[list]]:
    """
    Decimate an isopycnal mesh to approximately target_faces triangles.

    Uses VTK Quadric Error Metrics via PyVista. If the mesh already has fewer
    than target_faces triangles the input is returned unchanged.

    Args:
        vertices:     list of [x, y, z] positions  (N × 3)
        faces:        list of [i, j, k] triangle indices  (M × 3)
        target_faces: target number of output triangles
        color_values: optional per-vertex scalar values  (N,)

    Returns:
        (new_vertices, new_faces, new_color_values) — same types as input
    """
    try:
        import pyvista as pv
    except ImportError as exc:
        raise RuntimeError("pyvista is required for mesh decimation") from exc

    verts = np.asarray(vertices, dtype=np.float32)
    tris  = np.asarray(faces,    dtype=np.int64)

    if len(tris) == 0:
        return vertices, faces, color_values
    if len(tris) <= target_faces:
        log.debug("decimate: %d faces ≤ target %d — skipping", len(tris), target_faces)
        return vertices, faces, color_values

    # PyVista face array: [3, i0, i1, i2, 3, i0, i1, i2, ...]
    faces_pv = np.hstack([np.full((len(tris), 1), 3, dtype=np.int64), tris]).flatten()
    mesh = pv.PolyData(verts, faces_pv)

    target_reduction = max(0.0, min(0.99, 1.0 - target_faces / len(tris)))
    try:
        dec = mesh.decimate(target_reduction, progress_bar=False)
    except Exception as exc:
        log.warning("pyvista decimate failed: %s — returning original mesh", exc)
        return vertices, faces, color_values

    new_verts = dec.points.astype(np.float32)
    new_faces = dec.faces.reshape(-1, 4)[:, 1:4].astype(np.int64)

    # Re-assign color scalars by nearest-neighbour lookup in original vertex set
    new_colors: Optional[list] = None
    if color_values is not None and len(color_values) == len(verts):
        try:
            from scipy.spatial import cKDTree
            tree = cKDTree(verts)
            _, nn_idx = tree.query(new_verts)
            cv = np.asarray(color_values, dtype=np.float32)
            new_colors = cv[nn_idx].tolist()
        except Exception as exc:
            log.warning("color re-interpolation failed: %s — dropping colors", exc)

    log.info(
        "decimate: %d → %d faces (%.1f%%), %d → %d vertices",
        len(tris), len(new_faces),
        100 * len(new_faces) / len(tris),
        len(verts), len(new_verts),
    )

    return new_verts.tolist(), new_faces.tolist(), new_colors
