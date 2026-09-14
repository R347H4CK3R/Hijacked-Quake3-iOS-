import io
import struct

from tools.t6ps3.clipmesh import CollisionMeshView
from tools.t6ps3.mapents import MapEntsView
from tools.q3.export import write_obj, build_map_text, build_shader_text


def mesh_fixture():
    verts = [(0.0, 0.0, 0.0), (64.0, 0.0, 0.0), (0.0, 64.0, 0.0)]
    data = bytearray()
    for v in verts:
        data += struct.pack('>3f', *v)
    index_offset = len(data)
    data += struct.pack('>3H', 0, 1, 2)
    mesh = CollisionMeshView(0, index_offset, 3, 1, 0, (0.0, 0.0, 0.0), (64.0, 64.0, 0.0))
    return bytes(data), mesh


def test_obj_uses_q3_shader_material_and_one_based_indices():
    data, mesh = mesh_fixture()
    out = io.StringIO()
    write_obj(data, mesh, out)
    text = out.getvalue()
    assert 'usemtl textures/hijacked/collision' in text
    assert 'v 64 0 0' in text
    assert 'f 1 2 3' in text


def test_map_contains_model_and_translated_dm_spawn():
    mapents = MapEntsView(
        0, 0, 0, '',
        ({'classname': 'mp_dm_spawn', 'origin': '100 200 50', 'angles': '0 135 0'},)
    )
    text = build_map_text(mapents, mins=(-100.0, -200.0, -20.0), maxs=(300.0, 400.0, 100.0))
    assert '"classname" "misc_model"' in text
    assert '"spawnflags" "2"' in text
    assert '"classname" "info_player_deathmatch"' in text
    assert '"origin" "100 200 50"' in text
    assert '"angle" "135"' in text


def test_shader_is_fullbright_and_autoclipped():
    shader = build_shader_text()
    assert 'q3map_clipModel' in shader
    assert 'map $whiteimage' in shader
    assert 'rgbGen const' in shader
