from __future__ import annotations

from pathlib import Path
import struct
from typing import TextIO
import zipfile

from tools.t6ps3.clipmesh import CollisionMeshView
from tools.t6ps3.mapents import MapEntsView

SHADER = "textures/hijacked/collision"
MODEL_PATH = "models/hijacked/hijacked_collision.obj"


def _num(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.6f}".rstrip("0").rstrip(".")


def write_obj(data: bytes, mesh: CollisionMeshView, out: TextIO) -> None:
    out.write("# Generated from user-supplied PS3 T6 collision data\n")
    out.write("mtllib hijacked_collision.mtl\n")
    out.write(f"usemtl {SHADER}\n")
    for index in range(mesh.vertex_count):
        x, y, z = struct.unpack_from(">3f", data, mesh.vertex_offset + index * 12)
        out.write(f"v {_num(x)} {_num(y)} {_num(z)}\n")
    for index in range(mesh.triangle_count):
        a, b, c = struct.unpack_from(">3H", data, mesh.index_offset + index * 6)
        out.write(f"f {a + 1} {b + 1} {c + 1}\n")


def build_mtl_text() -> str:
    return f"newmtl {SHADER}\nKd 0.55 0.62 0.68\n"


def build_shader_text() -> str:
    return f"""{SHADER}
{{
    q3map_clipModel
    surfaceparm solid
    surfaceparm nolightmap
    {{
        map $whiteimage
        rgbGen const ( 0.55 0.62 0.68 )
    }}
}}
"""


def _plane(a, b, c, shader: str = "common/caulk") -> str:
    def point(v):
        return f"( {_num(v[0])} {_num(v[1])} {_num(v[2])} )"
    return f"{point(a)} {point(b)} {point(c)} {shader} 0 0 0 1 1"


def _box_brush(mins, maxs, shader: str = "common/caulk") -> str:
    x0, y0, z0 = mins
    x1, y1, z1 = maxs
    lines = [
        _plane((x1, y1, z1), (x1, y0, z1), (x1, y0, z0), shader),
        _plane((x0, y1, z1), (x0, y1, z0), (x0, y0, z0), shader),
        _plane((x1, y1, z1), (x1, y1, z0), (x0, y1, z0), shader),
        _plane((x1, y0, z1), (x0, y0, z1), (x0, y0, z0), shader),
        _plane((x1, y1, z1), (x0, y1, z1), (x0, y0, z1), shader),
        _plane((x1, y1, z0), (x1, y0, z0), (x0, y0, z0), shader),
    ]
    return "{\n" + "\n".join(lines) + "\n}\n"


def _enclosure_brushes(mins, maxs) -> str:
    margin = 256.0
    thickness = 64.0
    x0, y0, z0 = (mins[0] - margin, mins[1] - margin, mins[2] - margin)
    x1, y1, z1 = (maxs[0] + margin, maxs[1] + margin, maxs[2] + margin)
    boxes = [
        ((x0 - thickness, y0, z0), (x0, y1, z1)),
        ((x1, y0, z0), (x1 + thickness, y1, z1)),
        ((x0, y0 - thickness, z0), (x1, y0, z1)),
        ((x0, y1, z0), (x1, y1 + thickness, z1)),
        ((x0, y0, z0 - thickness), (x1, y1, z0)),
        ((x0, y0, z1), (x1, y1, z1 + thickness)),
    ]
    return "".join(_box_brush(a, b) for a, b in boxes)


def _spawn_entities(mapents: MapEntsView) -> list[dict[str, str]]:
    spawns = [entity for entity in mapents.entities if entity.get("classname") == "mp_dm_spawn"]
    if not spawns:
        spawns = [entity for entity in mapents.entities if entity.get("classname") == "mp_tdm_spawn"]
    return spawns


def build_map_text(mapents: MapEntsView, *, mins, maxs) -> str:
    parts = ["// Generated Hijacked Quake 3 map\n{\n\"classname\" \"worldspawn\"\n"]
    parts.append(_enclosure_brushes(mins, maxs))
    parts.append("}\n")
    parts.append(
        "{\n\"classname\" \"misc_model\"\n"
        f"\"model\" \"{MODEL_PATH}\"\n"
        "\"spawnflags\" \"2\"\n}\n"
    )
    for entity in _spawn_entities(mapents):
        origin = entity.get("origin")
        if not origin:
            continue
        angles = entity.get("angles", "0 0 0").split()
        yaw = angles[1] if len(angles) >= 2 else "0"
        parts.append(
            "{\n\"classname\" \"info_player_deathmatch\"\n"
            f"\"origin\" \"{origin}\"\n"
            f"\"angle\" \"{yaw}\"\n}}\n"
        )
    return "".join(parts)


def build_pk3(source_dir: Path, output: Path) -> None:
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(source_dir.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(source_dir).as_posix())
