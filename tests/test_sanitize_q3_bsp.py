import struct

from tools.sanitize_q3_bsp import sanitize_bsp_bytes


def _fixture():
    header = bytearray(b"IBSP" + struct.pack("<i", 46) + b"\0" * (17 * 8))
    verts = bytearray()
    for xyz in ((0,0,0),(10,0,0),(0,10,0),(5000,0,0)):
        verts += struct.pack("<3f2f2f3f4B", *xyz, 0,0, 0,0, 0,0,1, 255,255,255,255)
    mesh = struct.pack("<6i", 0,1,2, 0,1,3)
    face = bytearray(104)
    struct.pack_into("<8i", face, 0, 0,-1,3, 0,4, 0,6,-1)
    off = len(header)
    lumps = [(0,0)] * 17
    lumps[10] = (off, len(verts)); off += len(verts)
    lumps[11] = (off, len(mesh)); off += len(mesh)
    lumps[13] = (off, len(face)); off += len(face)
    for i,(o,n) in enumerate(lumps):
        struct.pack_into("<ii", header, 8+i*8, o,n)
    return bytes(header + verts + mesh + face)


def test_sanitizer_degenerates_only_pathological_triangle():
    result, report = sanitize_bsp_bytes(_fixture(), max_edge=1000.0)
    assert report["triangles_scanned"] == 2
    assert report["triangles_degenerated"] == 1

    mo, _ = struct.unpack_from("<ii", result, 8 + 11*8)
    assert struct.unpack_from("<3i", result, mo) == (0,1,2)
    assert struct.unpack_from("<3i", result, mo + 12) == (0,0,0)
