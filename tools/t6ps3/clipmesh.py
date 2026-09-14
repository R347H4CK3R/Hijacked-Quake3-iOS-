from __future__ import annotations

from array import array
from dataclasses import dataclass
import math
import struct
import sys


class ClipMeshError(ValueError):
    pass


@dataclass(frozen=True)
class CollisionMeshView:
    vertex_offset: int
    index_offset: int
    vertex_count: int
    triangle_count: int
    degenerate_triangles: int
    mins: tuple[float, float, float]
    maxs: tuple[float, float, float]


def _good_float(value: float, max_abs: float) -> bool:
    if not math.isfinite(value) or abs(value) > max_abs:
        return False
    return value == 0.0 or abs(value) >= 1.0e-5


def _float_runs(data: bytes, start: int, end: int, min_floats: int, max_abs: float):
    for align in range(4):
        first = start + ((align - start) & 3)
        usable = end - first
        usable -= usable % 4
        if usable <= 0:
            continue
        values = array("f")
        values.frombytes(data[first:first + usable])
        if sys.byteorder == "little":
            values.byteswap()
        run_start = None
        for index, value in enumerate(values):
            good = _good_float(value, max_abs)
            if good and run_start is None:
                run_start = index
            elif not good and run_start is not None:
                if index - run_start >= min_floats:
                    yield first + run_start * 4, index - run_start
                run_start = None
        if run_start is not None and len(values) - run_start >= min_floats:
            yield first + run_start * 4, len(values) - run_start


def _index_run(data: bytes, offset: int, vertex_count: int, max_indices: int = 3_000_000) -> int:
    available = min((len(data) - offset) // 2, max_indices)
    count = 0
    for i in range(available):
        value = struct.unpack_from(">H", data, offset + i * 2)[0]
        if value >= vertex_count:
            break
        count += 1
    return count - (count % 3)


def _mesh_stats(data: bytes, vertex_offset: int, vertex_count: int, index_offset: int, index_count: int):
    mins = [math.inf, math.inf, math.inf]
    maxs = [-math.inf, -math.inf, -math.inf]
    for i in range(vertex_count):
        xyz = struct.unpack_from(">3f", data, vertex_offset + i * 12)
        for axis, value in enumerate(xyz):
            mins[axis] = min(mins[axis], value)
            maxs[axis] = max(maxs[axis], value)

    degenerate = 0
    for i in range(0, index_count, 3):
        a, b, c = struct.unpack_from(">3H", data, index_offset + i * 2)
        if a == b or b == c or a == c:
            degenerate += 1
    return degenerate, tuple(mins), tuple(maxs)


def locate_collision_mesh(
    data: bytes,
    *,
    search_start: int = 0,
    search_end: int | None = None,
    min_vertices: int = 1_000,
    min_triangles: int = 1_000,
    max_abs_coordinate: float = 100_000.0,
) -> CollisionMeshView:
    end = len(data) if search_end is None else min(search_end, len(data))
    if search_start < 0 or search_start >= end:
        raise ClipMeshError("invalid collision search window")

    candidates: list[CollisionMeshView] = []
    min_floats = min_vertices * 3
    for run_offset, run_floats in _float_runs(data, search_start, end, min_floats, max_abs_coordinate):
        for prefix_trim in range(3):
            for suffix_trim in range(3):
                float_count = run_floats - prefix_trim - suffix_trim
                if float_count < min_floats or float_count % 3:
                    continue
                vertex_count = float_count // 3
                vertex_offset = run_offset + prefix_trim * 4
                index_offset = vertex_offset + vertex_count * 12
                if index_offset >= end:
                    continue
                index_count = _index_run(data[:end], index_offset, vertex_count)
                triangle_count = index_count // 3
                if triangle_count < min_triangles:
                    continue
                degenerate, mins, maxs = _mesh_stats(data, vertex_offset, vertex_count, index_offset, index_count)
                extents = tuple(maxs[i] - mins[i] for i in range(3))
                if max(extents) < 100.0:
                    continue
                candidates.append(
                    CollisionMeshView(
                        vertex_offset,
                        index_offset,
                        vertex_count,
                        triangle_count,
                        degenerate,
                        mins,
                        maxs,
                    )
                )

    clean = [candidate for candidate in candidates if candidate.degenerate_triangles == 0]
    if len(clean) == 1:
        return clean[0]
    if not clean:
        raise ClipMeshError("no non-degenerate collision mesh candidate found")
    clean.sort(key=lambda item: (item.triangle_count, item.vertex_count), reverse=True)
    if len(clean) > 1 and (clean[0].triangle_count, clean[0].vertex_count) == (clean[1].triangle_count, clean[1].vertex_count):
        raise ClipMeshError(f"ambiguous collision mesh candidates: {len(clean)}")
    return clean[0]
