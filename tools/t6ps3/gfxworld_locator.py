from __future__ import annotations

from dataclasses import dataclass
import struct

FOLLOW = 0xFFFFFFFF
INSERT = 0xFFFFFFFE


class GfxWorldLocateError(ValueError):
    pass


@dataclass(frozen=True)
class GfxWorldHeader:
    offset: int
    plane_count: int
    node_count: int
    surface_count: int
    primary_light_count: int
    cell_count: int
    vertex_count: int
    vertex_data_size0: int
    vertex_data_size1: int
    index_count: int


def _u32(data: bytes, off: int) -> int:
    return struct.unpack_from(">I", data, off)[0]


def _ptrish(value: int) -> bool:
    return value in (0, FOLLOW, INSERT) or 0xA0000000 <= value <= 0xBFFFFFFF


def _candidate(data: bytes, start: int) -> GfxWorldHeader | None:
    if start < 0 or start + 1028 > len(data):
        return None

    plane_count = _u32(data, start + 8)
    node_count = _u32(data, start + 12)
    surface_count = _u32(data, start + 16)
    if not (
        10 <= plane_count < 200_000
        and 10 <= node_count < 200_000
        and 10 <= surface_count < 100_000
    ):
        return None

    for off in (0, 4, 24, 32, 36, 256, 376, 380, 392):
        if not _ptrish(_u32(data, start + off)):
            return None

    primary_light_count = _u32(data, start + 264)
    cell_count = _u32(data, start + 372)
    if primary_light_count > 4096 or not (1 <= cell_count < 10_000):
        return None

    # PS3 T6 v146 uses the PC-compatible GfxWorldDraw header positions even
    # though the surrounding zone is big-endian. These positions are verified
    # against the user-supplied mp_hijacked fastfile before being relied on.
    draw = start + 396
    vertex_count = _u32(data, draw + 28)
    size0 = _u32(data, draw + 32)
    size1 = _u32(data, draw + 44)
    index_count = _u32(data, draw + 56)

    if not (1 <= vertex_count < 10_000_000):
        return None
    if not (0 < size0 < 256_000_000 and 0 < size1 < 256_000_000):
        return None
    if not (3 <= index_count < 30_000_000):
        return None
    for off in (36, 48, 60):
        if not _ptrish(_u32(data, draw + off)):
            return None

    return GfxWorldHeader(
        start,
        plane_count,
        node_count,
        surface_count,
        primary_light_count,
        cell_count,
        vertex_count,
        size0,
        size1,
        index_count,
    )


def locate_gfxworld(data: bytes) -> GfxWorldHeader:
    hits: list[GfxWorldHeader] = []
    for start in range(0, max(0, len(data) - 1028), 4):
        hit = _candidate(data, start)
        if hit is not None:
            hits.append(hit)

    if len(hits) != 1:
        raise GfxWorldLocateError(
            f"expected exactly one GfxWorld root, found {len(hits)}"
        )
    return hits[0]
