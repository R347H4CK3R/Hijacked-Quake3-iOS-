import struct

from tools.t6ps3.clipmesh import locate_collision_mesh


def test_locates_vec3_mesh_followed_by_u16_triangles():
    vertices = [(float(i), float(i % 7), float(i % 3)) for i in range(1000)]
    triangles = [(i, i + 1, i + 2) for i in range(0, 900, 3)]
    data = bytearray(b"\x7f" * 37)
    start = len(data)
    for vertex in vertices:
        data += struct.pack(">3f", *vertex)
    index_offset = len(data)
    for triangle in triangles:
        data += struct.pack(">3H", *triangle)
    data += b"\xff\xff"

    mesh = locate_collision_mesh(bytes(data), min_vertices=900, min_triangles=250)
    assert mesh.vertex_offset == start
    assert mesh.index_offset == index_offset
    assert mesh.vertex_count == 1000
    assert mesh.triangle_count == 300
    assert mesh.degenerate_triangles == 0


def test_prefers_non_degenerate_candidate():
    bad_vertices = [(float(i), 1.0, 2.0) for i in range(900)]
    data = bytearray()
    for vertex in bad_vertices:
        data += struct.pack(">3f", *vertex)
    for _ in range(300):
        data += struct.pack(">3H", 1, 1, 2)
    data += b"\xff\xff"
    data += b"X" * 13

    good_start = len(data)
    good_vertices = [(float(i), float(i % 11), 3.0) for i in range(1000)]
    for vertex in good_vertices:
        data += struct.pack(">3f", *vertex)
    for i in range(0, 900, 3):
        data += struct.pack(">3H", i, i + 1, i + 2)
    data += b"\xff\xff"

    mesh = locate_collision_mesh(bytes(data), min_vertices=850, min_triangles=250)
    assert mesh.vertex_offset == good_start
    assert mesh.degenerate_triangles == 0
