"""
Minimal binary glTF (GLB) serialiser for THALASSA isopycnal meshes.

Produces a spec-compliant GLB 2.0 file with:
  - POSITION accessor (VEC3, FLOAT)
  - Indices accessor (SCALAR, UNSIGNED_INT)
  - Optional per-vertex scalar attribute stored as _<NAME> (SCALAR, FLOAT)
    so Blender / ParaView users can apply their own colormap.

No external dependencies beyond the Python standard library and NumPy.
"""
from __future__ import annotations

import json
import struct
from typing import Optional

import numpy as np


def mesh_to_glb(
    vertices: list,
    faces: list,
    color_values: Optional[list] = None,
    scalar_name: str = "COLOR",
) -> bytes:
    """
    Serialise an isopycnal mesh dict to binary glTF (GLB 2.0).

    Args:
        vertices:     [[lon, lat, depth_m], ...] — N × 3 float positions
        faces:        [[i, j, k], ...] — M × 3 triangle indices
        color_values: optional per-vertex scalar  (N,)
        scalar_name:  attribute name stored as _{scalar_name} in glTF

    Returns:
        bytes — valid GLB file ready to write to disk or send as HTTP response
    """
    verts = np.asarray(vertices, dtype=np.float32)   # (N, 3)
    tris  = np.asarray(faces,    dtype=np.uint32)    # (M, 3)

    n_verts   = len(verts)
    n_indices = tris.size   # M × 3 individual indices

    # --- Build binary buffer ------------------------------------------------
    pos_bytes = verts.tobytes()
    idx_bytes = tris.flatten().tobytes()

    def _pad4(b: bytes, pad_byte: int = 0x00) -> bytes:
        r = len(b) % 4
        return b + bytes([pad_byte] * ((4 - r) % 4))

    pos_bytes = _pad4(pos_bytes)
    idx_bytes = _pad4(idx_bytes)

    color_bytes = b""
    n_colors = 0
    if color_values is not None and len(color_values) == n_verts:
        cv = np.asarray(color_values, dtype=np.float32)
        color_bytes = _pad4(cv.tobytes())
        n_colors = len(cv)

    bin_data = pos_bytes + idx_bytes + color_bytes

    # --- Build glTF JSON ----------------------------------------------------
    pos_offset = 0
    idx_offset = len(pos_bytes)
    col_offset = idx_offset + len(idx_bytes)

    v_min = verts.min(axis=0).tolist() if n_verts else [0, 0, 0]
    v_max = verts.max(axis=0).tolist() if n_verts else [0, 0, 0]

    accessors = [
        {
            "bufferView": 0,
            "byteOffset": 0,
            "componentType": 5126,   # FLOAT
            "count": n_verts,
            "type": "VEC3",
            "min": v_min,
            "max": v_max,
        },
        {
            "bufferView": 1,
            "byteOffset": 0,
            "componentType": 5125,   # UNSIGNED_INT
            "count": n_indices,
            "type": "SCALAR",
        },
    ]
    buffer_views = [
        {"buffer": 0, "byteOffset": pos_offset, "byteLength": len(pos_bytes)},
        {"buffer": 0, "byteOffset": idx_offset, "byteLength": len(idx_bytes)},
    ]

    primitive_attributes: dict = {"POSITION": 0}

    if n_colors:
        accessors.append({
            "bufferView": 2,
            "byteOffset": 0,
            "componentType": 5126,   # FLOAT
            "count": n_colors,
            "type": "SCALAR",
        })
        buffer_views.append({
            "buffer": 0,
            "byteOffset": col_offset,
            "byteLength": len(color_bytes),
        })
        primitive_attributes[f"_{scalar_name.upper()}"] = 2

    gltf = {
        "asset": {"version": "2.0", "generator": "THALASSA-SciVis2026"},
        "scene": 0,
        "scenes": [{"nodes": [0], "name": "isopycnal_scene"}],
        "nodes": [{"mesh": 0, "name": "isopycnal_surface"}],
        "meshes": [{
            "name": "isopycnal",
            "primitives": [{
                "attributes": primitive_attributes,
                "indices": 1,
                "mode": 4,   # TRIANGLES
            }],
        }],
        "accessors": accessors,
        "bufferViews": buffer_views,
        "buffers": [{"byteLength": len(bin_data)}],
    }

    # JSON chunk: pad with 0x20 (space) per glTF spec
    json_bytes = _pad4(json.dumps(gltf, separators=(",", ":")).encode("utf-8"), 0x20)

    # GLB binary layout
    json_len = len(json_bytes)
    bin_len  = len(bin_data)
    total    = 12 + (8 + json_len) + (8 + bin_len)

    header    = struct.pack("<III", 0x46546C67, 2, total)          # magic, version, length
    json_chunk = struct.pack("<II", json_len, 0x4E4F534A) + json_bytes
    bin_chunk  = struct.pack("<II", bin_len,  0x004E4942) + bin_data

    return header + json_chunk + bin_chunk
