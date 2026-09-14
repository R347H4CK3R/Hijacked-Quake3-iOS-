from __future__ import annotations

from pathlib import Path
import argparse
import json

from tools.q3.export import build_map_text, build_mtl_text, build_pk3, build_shader_text, write_obj
from tools.t6ps3.clipmesh import CollisionMeshView
from tools.t6ps3.mapents import MapEntsView


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

    obj_path = model_dir / "hijacked_collision.obj"
    with obj_path.open("w", encoding="utf-8", newline="\n") as stream:
        write_obj(data, mesh, stream)
    (model_dir / "hijacked_collision.mtl").write_text(build_mtl_text(), encoding="utf-8")
    (scripts_dir / "hijacked.shader").write_text(build_shader_text(), encoding="utf-8")
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
        "obj_bytes": obj_path.stat().st_size,
    }
    (out_dir / "hijacked-stage-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if source_pk3 is not None:
        source_pk3.parent.mkdir(parents=True, exist_ok=True)
        build_pk3(out_dir, source_pk3)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write Quake 3 staging files from a decoded Hijacked payload.")
    parser.add_argument("--decoded", type=Path, required=True, help="Decoded T6 zone including 40-byte XFile header")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--mesh-json", type=Path, required=True, help="CollisionMeshView fields as JSON")
    parser.add_argument("--mapents-json", type=Path, required=True, help="MapEntsView fields and entities as JSON")
    parser.add_argument("--source-pk3", type=Path)
    args = parser.parse_args(argv)

    decoded = args.decoded.read_bytes()
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
