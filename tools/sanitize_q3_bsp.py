from __future__ import annotations

import argparse
import math
import struct
from pathlib import Path


class BspSanitizeError(ValueError):
    pass


def _lumps(data: bytes) -> list[tuple[int, int]]:
    if len(data) < 144 or data[:4] != b"IBSP":
        raise BspSanitizeError("not an IBSP file")
    if struct.unpack_from("<i", data, 4)[0] != 46:
        raise BspSanitizeError("expected Quake 3 BSP version 46")
    lumps = [struct.unpack_from("<ii", data, 8 + i * 8) for i in range(17)]
    for i, (off, length) in enumerate(lumps):
        if off < 0 or length < 0 or off + length > len(data):
            raise BspSanitizeError(f"invalid lump {i}: {off}+{length}")
    return lumps


def _edge_max(data: bytes, vertex_off: int, a: int, b: int, c: int) -> float:
    pts = [struct.unpack_from("<3f", data, vertex_off + i * 44) for i in (a, b, c)]
    def d(p, q):
        return math.sqrt(sum((p[i] - q[i]) ** 2 for i in range(3)))
    return max(d(pts[0], pts[1]), d(pts[1], pts[2]), d(pts[2], pts[0]))


def sanitize_bsp_bytes(data: bytes, *, max_edge: float = 1000.0) -> tuple[bytes, dict[str, int | float]]:
    if max_edge <= 0:
        raise BspSanitizeError("max_edge must be positive")

    lumps = _lumps(data)
    vo, vl = lumps[10]
    mo, ml = lumps[11]
    fo, fl = lumps[13]
    if vl % 44 or ml % 4 or fl % 104:
        raise BspSanitizeError("misaligned Quake 3 geometry lump")

    nv, nm, nf = vl // 44, ml // 4, fl // 104
    out = bytearray(data)
    scanned = degenerated = 0

    for face_index in range(nf):
        face_off = fo + face_index * 104
        _, _, surface_type, first_vert, num_verts, first_index, num_indexes, _ = struct.unpack_from(
            "<8i", out, face_off
        )
        if surface_type not in (1, 2, 3, 4):
            raise BspSanitizeError(f"face {face_index}: unsupported surface type {surface_type}")
        if not (0 <= first_vert <= nv and 0 <= num_verts <= nv - first_vert):
            raise BspSanitizeError(f"face {face_index}: bad vertex range")
        if not (0 <= first_index <= nm and 0 <= num_indexes <= nm - first_index and num_indexes % 3 == 0):
            raise BspSanitizeError(f"face {face_index}: bad meshvert range")

        for k in range(first_index, first_index + num_indexes, 3):
            rel = struct.unpack_from("<3i", out, mo + k * 4)
            absolute = tuple(first_vert + value for value in rel)
            if any(index < 0 or index >= nv for index in absolute):
                raise BspSanitizeError(f"face {face_index}: meshvert references vertex outside drawvert lump")
            scanned += 1
            if _edge_max(out, vo, *absolute) > max_edge:
                # Preserve all BSP lump sizes/offsets. A zero-area triangle is ignored by the
                # renderer but avoids rewriting every following face's firstIndex.
                struct.pack_into("<3i", out, mo + k * 4, rel[0], rel[0], rel[0])
                degenerated += 1

    report = {
        "vertices": nv,
        "mesh_indices": nm,
        "surfaces": nf,
        "triangles_scanned": scanned,
        "triangles_degenerated": degenerated,
        "max_edge": float(max_edge),
    }
    return bytes(out), report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Neutralize pathological long triangles in a Quake 3 BSP.")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--max-edge", type=float, default=1000.0)
    args = parser.parse_args(argv)

    patched, report = sanitize_bsp_bytes(args.input.read_bytes(), max_edge=args.max_edge)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(patched)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
