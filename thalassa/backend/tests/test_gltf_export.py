"""Unit tests for services/scene/gltf_export — binary GLB serialiser."""
from __future__ import annotations

import json
import struct

import numpy as np
import pytest

from services.scene.gltf_export import mesh_to_glb

_VERTS = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
_FACES = [[0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3]]
_COLORS = [0.1, 0.5, 0.9, 0.3]


def _parse_glb(data: bytes):
    """Parse minimal GLB into (header, json_chunk, bin_chunk)."""
    magic, version, total = struct.unpack_from("<III", data, 0)
    assert magic == 0x46546C67, "wrong glTF magic"
    assert version == 2

    json_len, json_type = struct.unpack_from("<II", data, 12)
    assert json_type == 0x4E4F534A, "first chunk must be JSON"
    json_bytes = data[20 : 20 + json_len]
    gltf = json.loads(json_bytes.decode("utf-8").strip())

    bin_offset = 20 + json_len
    bin_len, bin_type = struct.unpack_from("<II", data, bin_offset)
    assert bin_type == 0x004E4942, "second chunk must be BIN"
    bin_data = data[bin_offset + 8 : bin_offset + 8 + bin_len]

    return gltf, bin_data


def test_magic_and_version():
    glb = mesh_to_glb(_VERTS, _FACES)
    assert glb[:4] == b"glTF"
    _, version, total = struct.unpack_from("<III", glb, 0)
    assert version == 2
    assert total == len(glb)


def test_json_chunk_parses():
    glb = mesh_to_glb(_VERTS, _FACES)
    gltf, _ = _parse_glb(glb)
    assert gltf["asset"]["version"] == "2.0"
    assert len(gltf["meshes"]) == 1
    assert "POSITION" in gltf["meshes"][0]["primitives"][0]["attributes"]


def test_position_accessor_count():
    glb = mesh_to_glb(_VERTS, _FACES)
    gltf, _ = _parse_glb(glb)
    pos_accessor = next(a for a in gltf["accessors"] if a["type"] == "VEC3")
    assert pos_accessor["count"] == len(_VERTS)


def test_index_accessor_count():
    glb = mesh_to_glb(_VERTS, _FACES)
    gltf, _ = _parse_glb(glb)
    idx_accessor = next(a for a in gltf["accessors"] if a["type"] == "SCALAR" and a["componentType"] == 5125)
    assert idx_accessor["count"] == len(_FACES) * 3


def test_binary_chunk_size():
    glb = mesh_to_glb(_VERTS, _FACES)
    _, bin_data = _parse_glb(glb)
    # positions: 4 verts × 3 floats × 4 bytes = 48, padded to 48
    # indices: 4 faces × 3 ints × 4 bytes = 48
    assert len(bin_data) >= 48 + 48


def test_color_scalar_attribute_included():
    glb = mesh_to_glb(_VERTS, _FACES, color_values=_COLORS, scalar_name="CT")
    gltf, _ = _parse_glb(glb)
    attribs = gltf["meshes"][0]["primitives"][0]["attributes"]
    assert "_CT" in attribs


def test_no_color_no_extra_attribute():
    glb = mesh_to_glb(_VERTS, _FACES, color_values=None)
    gltf, _ = _parse_glb(glb)
    attribs = gltf["meshes"][0]["primitives"][0]["attributes"]
    assert len([k for k in attribs if k.startswith("_")]) == 0


def test_empty_mesh_produces_valid_glb():
    glb = mesh_to_glb([], [])
    assert glb[:4] == b"glTF"


def test_vertex_bounds_in_accessor():
    glb = mesh_to_glb(_VERTS, _FACES)
    gltf, _ = _parse_glb(glb)
    pos_accessor = next(a for a in gltf["accessors"] if a["type"] == "VEC3")
    assert "min" in pos_accessor
    assert "max" in pos_accessor
    assert pos_accessor["min"] == [0.0, 0.0, 0.0]
    assert pos_accessor["max"] == [1.0, 1.0, 1.0]
