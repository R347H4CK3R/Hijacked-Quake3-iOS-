from pathlib import Path
import struct

import pytest

from tools.q3.bsp import read_bsp_stats, validate_bsp


def _fake_bsp(path: Path, *, brushes: int, drawverts: int, drawfaces: int) -> None:
    header_size = 8 + 17 * 8
    lumps = [(header_size, 0) for _ in range(17)]
    chunks = bytearray()

    def add_lump(index: int, payload: bytes) -> None:
        offset = header_size + len(chunks)
        lumps[index] = (offset, len(payload))
        chunks.extend(payload)

    add_lump(8, b"\0" * (brushes * 12))
    add_lump(9, b"\0" * (brushes * 6 * 8))
    add_lump(10, b"\0" * (drawverts * 44))
    add_lump(11, b"\0" * (drawverts * 4))
    add_lump(13, b"\0" * (drawfaces * 104))

    data = bytearray(b"IBSP" + struct.pack("<i", 46))
    for offset, length in lumps:
        data += struct.pack("<ii", offset, length)
    data += chunks
    path.write_bytes(data)


def test_read_bsp_stats_counts_geometry(tmp_path: Path):
    bsp = tmp_path / "map.bsp"
    _fake_bsp(bsp, brushes=7, drawverts=9, drawfaces=2)
    stats = read_bsp_stats(bsp)
    assert stats.brushes == 7
    assert stats.drawverts == 9
    assert stats.drawfaces == 2


def test_validate_bsp_rejects_empty_draw_geometry(tmp_path: Path):
    bsp = tmp_path / "empty.bsp"
    _fake_bsp(bsp, brushes=6, drawverts=0, drawfaces=0)
    with pytest.raises(ValueError, match="draw vertices"):
        validate_bsp(bsp)
