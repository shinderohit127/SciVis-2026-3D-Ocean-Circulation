"""Unit tests for services/scene/decimation — mesh face reduction."""
from __future__ import annotations

import numpy as np
import pytest

from services.scene.decimation import decimate_mesh


def _sphere_mesh(n: int = 40):
    """Generate a UV-sphere mesh with approximately n×n faces for testing."""
    from scipy.spatial import ConvexHull
    rng = np.random.default_rng(42)
    pts = rng.standard_normal((500, 3))
    pts /= np.linalg.norm(pts, axis=1, keepdims=True)
    hull = ConvexHull(pts)
    return pts.tolist(), hull.simplices.tolist()


@pytest.fixture(scope="module")
def sphere():
    return _sphere_mesh()


def test_no_op_when_below_target(sphere):
    verts, faces = sphere
    target = len(faces) + 100
    nv, nf, nc = decimate_mesh(verts, faces, target_faces=target)
    # Should return unchanged
    assert len(nf) == len(faces)


def test_reduces_face_count(sphere):
    verts, faces = sphere
    original_faces = len(faces)
    target = max(4, original_faces // 4)
    nv, nf, nc = decimate_mesh(verts, faces, target_faces=target)
    # pyvista should produce fewer faces than original
    assert len(nf) < original_faces, f"decimation did not reduce faces: {len(nf)} >= {original_faces}"


def test_output_faces_near_target(sphere):
    verts, faces = sphere
    target = max(4, len(faces) // 4)
    _, nf, _ = decimate_mesh(verts, faces, target_faces=target)
    # Allow 3× overshoot — VTK may not hit target exactly on tiny meshes
    assert len(nf) <= target * 3


def test_color_values_preserved_count(sphere):
    verts, faces = sphere
    colors = list(range(len(verts)))
    target = max(4, len(faces) // 3)
    nv, nf, nc = decimate_mesh(verts, faces, target_faces=target, color_values=colors)
    assert nc is not None
    assert len(nc) == len(nv), f"color count {len(nc)} != vertex count {len(nv)}"


def test_empty_mesh_passthrough():
    nv, nf, nc = decimate_mesh([], [], target_faces=1000)
    assert nv == []
    assert nf == []


def test_color_none_stays_none(sphere):
    verts, faces = sphere
    _, _, nc = decimate_mesh(verts, faces, target_faces=len(faces) // 2, color_values=None)
    assert nc is None
