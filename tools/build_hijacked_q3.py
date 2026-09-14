from __future__ import annotations

from pathlib import Path
import argparse
import hashlib
import json

from tools.q3.export import (
    COLLISION_SHADER,
    VISUAL_SHADER,
    build_common_shader_text,
    build_map_text,
    build_mtl_text,
    build_pk3,
    build_shader_text,
    build_shaderlist_text,
    write_obj,
)
from tools.t6ps3.clipmesh import CollisionMeshView, locate_collision_mesh
from tools.t6ps3.fastfile_decode import decode_fastfile_bytes
from tools.t6ps3.mapents import MapEntsView, locate_mapents

KNOWN_HIJACKED_DECODED_SHA256 = "f93655577fac1916c542f351dc908886290b51a14cfaae39c58aa0fc10002ffa"
KNOWN_HIJACKED_VERTEX_SHA256 = "03d3194b3e7ff619844472620330dcd847980cb5f036d412f0b3eda04aaf2583"
KNOWN_HIJACKED_INDEX_SHA256 = "95346b0f4373061e6facc7912dc23343bb02a6fbb3ce57460ed8d9df95014aee"
KNOWN_HIJACKED_MESH = CollisionMeshView(
    vertex_offset=35_832_497,
    index_offset=36_085_721,
    vertex_count=21_102,
    triangle_count=31_517,
    degenerate_triangles=0,
    mins=(-43_008.0, -30_721.0, -315.0),
    maxs=(26_624.0, 46_336.0, 311.5979919433594),
)


def _verified_known_hijacked_mesh(data: bytes, decoded_sha256: str) -> CollisionMeshView | None:
    if decoded_sha256 != KNOWN_HIJACKED_DECODED_SHA256:
        return None
    mesh = KNOWN_HIJACKED_MESH
    vertex_bytes = data[mesh.vertex_offset : mesh.vertex_offset + mesh.vertex_count * 12]
    index_bytes = data[mesh.index_offset : mesh.index_offset + mesh.triangle_count * 6]
    if len(vertex_bytes) != mesh.vertex_count * 12 or len(index_bytes) != mesh.triangle_count * 6:
        raise ValueError("known Hijacked collision slices are truncated")
    if hashlib.sha256(vertex_bytes).hexdigest() != KNOWN_HIJACKED_VERTEX_SHA256:
        raise ValueError("known Hijacked collision vertex hash mismatch")
    if hashlib.sha256(index_bytes).hexdigest() != KNOWN_HIJACKED_INDEX_SHA256:
        raise ValueError("known Hijacked collision index hash mismatch")
    return mesh


def write_stage(
    data: bytes,
    mesh: CollisionMeshView,
    mapents: MapEntsView,
    out_dir: Path,
    *,
    source_pk3: Path | None = None,
) -> dict[str, object]:
    model_dir = out_dir / "models" / "hijacked"
    maps_dir = out_dir / "maps"
    scripts_dir = out_dir / "scripts"
    model_dir.mkdir(parents=True, exist_ok=True)
    maps_dir.mkdir(parents=True, exist_ok=True)
    scripts_dir.mkdir(parents=True, exist_ok=True)

    collision_obj_path = model_dir / "hijacked_collision.obj"
    with collision_obj_path.open("w", encoding="utf-8", newline="\n") as stream:
        write_obj(data, mesh, stream)
    (model_dir / "hijacked_collision.mtl").write_text(
        build_mtl_text(COLLISION_SHADER), encoding="utf-8"
    )

    visual_obj_path = model_dir / "hijacked_visual.obj"
    with visual_obj_path.open("w", encoding="utf-8", newline="\n") as stream:
        write_obj(
            data,
            mesh,
            stream,
            shader=VISUAL_SHADER,
            mtllib="hijacked_visual.mtl",
        )
    (model_dir / "hijacked_visual.mtl").write_text(
        build_mtl_text(VISUAL_SHADER), encoding="utf-8"
    )

    (scripts_dir / "hijacked.shader").write_text(build_shader_text(), encoding="utf-8")
    (scripts_dir / "common.shader").write_text(build_common_shader_text(), encoding="utf-8")
    (scripts_dir / "shaderlist.txt").write_text(build_shaderlist_text(), encoding="utf-8")
    (maps_dir / "hijacked.map").write_text(
        build_map_text(mapents, mins=mesh.mins, maxs=mesh.maxs),
        encoding="utf-8",
    )

    dm_spawns = sum(1 for entity in mapents.entities if entity.get("classname") == "mp_dm_spawn")
    tdm_spawns = sum(1 for entity in mapents.entities if entity.get("classname") == "mp_tdm_spawn")
    report: dict[str, object] = {
        "collision_vertices": mesh.vertex_count,
        "collision_triangles": mesh.triangle_count,
        "degenerate_triangles": mesh.degenerate_triangles,
        "dm_spawns": dm_spawns,
        "tdm_spawns": tdm_spawns,
        "obj_bytes": collision_obj_path.stat().st_size,
        "collision_obj_bytes": collision_obj_path.stat().st_size,
        "visual_obj_bytes": visual_obj_path.stat().st_size,
    }
    (out_dir / "hijacked-stage-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if source_pk3 is not None:
        source_pk3.parent.mkdir(parents=True, exist_ok=True)
        build_pk3(out_dir, source_pk3)
    return report


def build_from_fastfile_bytes(
    source: bytes,
    out_dir: Path,
    *,
    source_pk3: Path | None = None,
) -> dict[str, object]:
    """Decode a signed PS3 T6 fastfile and produce the Quake 3 staging tree."""
    decoded, decode_report = decode_fastfile_bytes(source)
    if len(decoded) < 40:
        raise ValueError("decoded fastfile is missing the 40-byte XFile header")

    data = decoded[40:]
    mesh = _verified_known_hijacked_mesh(data, decode_report.decoded_sha256)
    mesh_source = "verified-profile"
    if mesh is None:
        mesh = locate_collision_mesh(data)
        mesh_source = "discovery-scan"
    mapents = locate_mapents(data)
    report = write_stage(data, mesh, mapents, out_dir, source_pk3=source_pk3)
    report.update(
        {
            "zone_name": decode_report.zone_name,
            "fastfile_version": decode_report.version,
            "decoded_bytes": decode_report.decoded_bytes,
            "decoded_sha256": decode_report.decoded_sha256,
            "xchunk_count": decode_report.chunk_count,
            "map_entity_count": len(mapents.entities),
            "collision_mesh_source": mesh_source,
        }
    )
    (out_dir / "hijacked-stage-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def build_from_fastfile(
    fastfile: Path,
    out_dir: Path,
    *,
    source_pk3: Path | None = None,
) -> dict[str, object]:
    return build_from_fastfile_bytes(fastfile.read_bytes(), out_dir, source_pk3=source_pk3)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write Quake 3 staging files from PS3 BO2 Hijacked data.")
    parser.add_argument("--fastfile", type=Path, help="Signed PS3 mp_hijacked.ff; preferred direct input")
    parser.add_argument("--decoded", type=Path, help="Decoded T6 zone including 40-byte XFile header")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--mesh-json", type=Path, help="Legacy CollisionMeshView fields as JSON")
    parser.add_argument("--mapents-json", type=Path, help="Legacy MapEntsView fields and entities as JSON")
    parser.add_argument("--source-pk3", type=Path)
    args = parser.parse_args(argv)

    if args.fastfile is not None:
        if args.decoded is not None or args.mesh_json is not None or args.mapents_json is not None:
            parser.error("--fastfile cannot be combined with --decoded/--mesh-json/--mapents-json")
        report = build_from_fastfile(args.fastfile, args.out, source_pk3=args.source_pk3)
    else:
        if args.decoded is None or args.mesh_json is None or args.mapents_json is None:
            parser.error("use --fastfile, or provide --decoded, --mesh-json, and --mapents-json together")
        decoded = args.decoded.read_bytes()
        if len(decoded) < 40:
            parser.error("decoded zone is missing the 40-byte XFile header")
        data = decoded[40:]
        mesh_data = json.loads(args.mesh_json.read_text(encoding="utf-8"))
        mapents_data = json.loads(args.mapents_json.read_text(encoding="utf-8"))
        mesh = CollisionMeshView(**mesh_data)
        mapents = MapEntsView(
            mapents_data.get("offset", 0),
            mapents_data.get("name_pointer", 0),
            mapents_data.get("num_entity_chars", 0),
            mapents_data.get("entity_string", ""),
            tuple(mapents_data["entities"]),
        )
        report = write_stage(data, mesh, mapents, args.out, source_pk3=args.source_pk3)

    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
