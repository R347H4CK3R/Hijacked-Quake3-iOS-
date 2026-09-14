import struct

from tools.t6ps3.gfxworld_locator import locate_gfxworld


def test_locate_unique_gfxworld():
    data = bytearray(4096)
    start = 512

    def write(off: int, value: int) -> None:
        struct.pack_into(">I", data, start + off, value)

    write(0, 0xA0000001)
    write(4, 0xA0000002)
    write(8, 5570)
    write(12, 19219)
    write(16, 2366)
    write(24, 0xFFFFFFFF)
    write(32, 0xFFFFFFFF)
    write(36, 0xA0000003)
    write(256, 0xFFFFFFFF)
    write(264, 22)
    write(372, 37)
    write(376, 0xFFFFFFFF)
    write(380, 0xFFFFFFFF)
    write(392, 0xFFFFFFFF)

    draw = 396
    write(draw + 28, 109415)
    write(draw + 32, 888912)
    write(draw + 36, 0xFFFFFFFF)
    write(draw + 44, 1967176)
    write(draw + 48, 0xFFFFFFFF)
    write(draw + 56, 232677)
    write(draw + 60, 0xFFFFFFFF)

    header = locate_gfxworld(bytes(data))
    assert header.offset == start
    assert header.surface_count == 2366
    assert header.vertex_count == 109415
    assert header.index_count == 232677
