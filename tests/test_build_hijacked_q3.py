from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import struct
import zipfile

from tools.build_hijacked_q3 import build_from_fastfile_bytes, write_stage
from tools.t6ps3.clipmesh import CollisionMeshView
from tools.t6ps3.mapents import MapEntsView


def _fixture():
    data = bytearray()
    for vertex in ((0.0, 0.0, 0.0), (64.0, 0.0, 0.0), (0.0, 64.0, 0.0)):
        data += struct.pack(">3f", *vertex)
    index_offset = len(data)
    data += struct.pack(">3H", 0, 1, 2)
    mesh = CollisionMeshView(0, index_offset, 3, 1, 0, (0.0, 0.0, 0.0), (64.0, 64.0, 0.0))
    mapents = MapEntsView(0, 0, 0, "", ({"classname": "mp_dm_spawn", "origin": "8 9 10", "angles": "0 45 0"},))
    return bytes(data), mesh, mapents


def test_write_stage_creates_expected_q3_layout(tmp_path: Path):
    data, mesh, mapents = _fixture()
    report = write_stage(data, mesh, mapents, tmp_path)

    assert (tmp_path / "models/hijacked/hijacked_collision.obj").is_file()
    assert (tmp_path / "models/hijacked/hijacked_collision.mtl").is_file()
    assert (tmp_path / "maps/hijacked.map").is_file()
    assert (tmp_path / "scripts/hijacked.shader").is_file()
    assert report["collision_vertices"] == 3
    assert report["collision_triangles"] == 1
    assert report["dm_spawns"] == 1


def test_write_stage_can_package_source_pk3(tmp_path: Path):
    data, mesh, mapents = _fixture()
    pk3 = tmp_path / "hijacked-source.pk3"
    write_stage(data, mesh, mapents, tmp_path / "stage", source_pk3=pk3)

    with zipfile.ZipFile(pk3) as archive:
        names = set(archive.namelist())
    assert "maps/hijacked.map" in names
    assert "models/hijacked/hijacked_collision.obj" in names
    assert "scripts/hijacked.shader" in names


def test_build_from_fastfile_bytes_runs_entire_pipeline(tmp_path: Path):
    data, mesh, mapents = _fixture()
    decoded = b"\0" * 40 + data
    decode_report = SimpleNamespace(
        zone_name="mp_hijacked",
        version=146,
        decoded_bytes=len(decoded),
        decoded_sha256="abc123",
        chunk_count=1603,
    )

    with (
        patch("tools.build_hijacked_q3.decode_fastfile_bytes", return_value=(decoded, decode_report)) as decode,
        patch("tools.build_hijacked_q3.locate_collision_mesh", return_value=mesh) as locate_mesh,
        patch("tools.build_hijacked_q3.locate_mapents", return_value=mapents) as locate_entities,
    ):
        report = build_from_fastfile_bytes(b"signed-fastfile", tmp_path)

    decode.assert_called_once_with(b"signed-fastfile")
    locate_mesh.assert_called_once_with(data)
    locate_entities.assert_called_once_with(data)
    assert report["zone_name"] == "mp_hijacked"
    assert report["fastfile_version"] == 146
    assert report["collision_triangles"] == 1
    assert report["map_entity_count"] == 1
    assert (tmp_path / "maps/hijacked.map").is_file()
