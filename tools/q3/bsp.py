from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import struct

BSP_MAGIC = b"IBSP"
BSP_VERSION = 46
LUMP_COUNT = 17
LUMP_BRUSHES = 8
LUMP_BRUSHSIDES = 9
LUMP_DRAWVERTS = 10
LUMP_MESHVERTS = 11
LUMP_DRAWFACES = 13


@dataclass(frozen=True)
class BspStats:
    bytes: int
    brushes: int
    brushsides: int
    drawverts: int
    meshverts: int
    drawfaces: int


def _lump(data: bytes, index: int) -> tuple[int, int]:
    offset, length = struct.unpack_from("<ii", data, 8 + index * 8)
    if offset < 0 or length < 0 or offset + length > len(data):
        raise ValueError(f"invalid BSP lump {index}: offset={offset} length={length}")
    return offset, length


def read_bsp_stats(path: Path) -> BspStats:
    data = path.read_bytes()
    header_size = 8 + LUMP_COUNT * 8
    if len(data) < header_size:
        raise ValueError("BSP is truncated")
    if data[:4] != BSP_MAGIC:
        raise ValueError(f"unexpected BSP magic {data[:4]!r}")
    version = struct.unpack_from("<i", data, 4)[0]
    if version != BSP_VERSION:
        raise ValueError(f"unexpected BSP version {version}")

    _, brush_bytes = _lump(data, LUMP_BRUSHES)
    _, brushside_bytes = _lump(data, LUMP_BRUSHSIDES)
    _, drawvert_bytes = _lump(data, LUMP_DRAWVERTS)
    _, meshvert_bytes = _lump(data, LUMP_MESHVERTS)
    _, drawface_bytes = _lump(data, LUMP_DRAWFACES)

    record_sizes = {
        "brushes": 12,
        "brushsides": 8,
        "drawverts": 44,
        "meshverts": 4,
        "drawfaces": 104,
    }
    lengths = {
        "brushes": brush_bytes,
        "brushsides": brushside_bytes,
        "drawverts": drawvert_bytes,
        "meshverts": meshvert_bytes,
        "drawfaces": drawface_bytes,
    }
    for name, length in lengths.items():
        size = record_sizes[name]
        if length % size:
            raise ValueError(f"BSP {name} lump length {length} is not divisible by {size}")

    return BspStats(
        bytes=len(data),
        brushes=brush_bytes // 12,
        brushsides=brushside_bytes // 8,
        drawverts=drawvert_bytes // 44,
        meshverts=meshvert_bytes // 4,
        drawfaces=drawface_bytes // 104,
    )


def validate_bsp(
    path: Path,
    *,
    min_brushes: int = 1,
    min_drawverts: int = 3,
    min_drawfaces: int = 1,
) -> BspStats:
    stats = read_bsp_stats(path)
    if stats.brushes < min_brushes:
        raise ValueError(f"BSP has {stats.brushes} brushes; expected at least {min_brushes}")
    if stats.drawverts < min_drawverts:
        raise ValueError(f"BSP has {stats.drawverts} draw vertices; expected at least {min_drawverts}")
    if stats.drawfaces < min_drawfaces:
        raise ValueError(f"BSP has {stats.drawfaces} draw faces; expected at least {min_drawfaces}")
    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate that a Quake 3 BSP contains real geometry.")
    parser.add_argument("bsp", type=Path)
    parser.add_argument("--min-brushes", type=int, default=1)
    parser.add_argument("--min-drawverts", type=int, default=3)
    parser.add_argument("--min-drawfaces", type=int, default=1)
    args = parser.parse_args(argv)
    stats = validate_bsp(
        args.bsp,
        min_brushes=args.min_brushes,
        min_drawverts=args.min_drawverts,
        min_drawfaces=args.min_drawfaces,
    )
    print(
        f"bytes={stats.bytes} brushes={stats.brushes} brushsides={stats.brushsides} "
        f"drawverts={stats.drawverts} meshverts={stats.meshverts} drawfaces={stats.drawfaces}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
