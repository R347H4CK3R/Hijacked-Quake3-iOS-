import struct
from tools.t6ps3.probe_fastfile import parse_asset_inventory, T6_ASSET_NAMES, find_gfxworld_summaries


def make_decoded_zone():
    strings = [None, 't6_skybox', 'p6_hijacked_engine_lod0']
    ptrs = [0, 0xFFFFFFFF, 0xFFFFFFFF]
    inline = b't6_skybox\0p6_hijacked_engine_lod0\0'
    assets = [(5, 0xFFFFFFFF), (17, 0xFFFFFFFF), (11, 0xFFFFFFFF)]
    content = (
        struct.pack('>6I', len(strings), 0xFFFFFFFF, 0, 0, len(assets), 0xFFFFFFFF)
        + b''.join(struct.pack('>I', p) for p in ptrs)
        + inline
        + b''.join(struct.pack('>II', t, p) for t, p in assets)
    )
    xfile = struct.pack('>10I', len(content), 0, 0,0,0,0,len(content),0,0,0)
    return xfile + content


def test_parses_strings_and_asset_type_counts():
    inv = parse_asset_inventory(make_decoded_zone())
    assert inv.script_string_count == 3
    assert inv.asset_count == 3
    assert inv.asset_array_offset == 40 + 24 + 12 + len(b't6_skybox\0p6_hijacked_engine_lod0\0')
    assert inv.asset_type_counts[5] == 1
    assert inv.asset_type_counts[17] == 1
    assert T6_ASSET_NAMES[17] == 'GFXWORLD'


def test_rejects_truncated_string_pointer_table():
    bad = make_decoded_zone()[:40+24+4]
    try:
        parse_asset_inventory(bad)
    except ValueError as exc:
        assert 'string pointer table' in str(exc)
    else:
        raise AssertionError('expected ValueError')


def test_finds_synthetic_gfxworld_layout():
    data = bytearray(40 + 1200)
    p = 40 + 128
    values = [0xA0000100,0xA0000200,100,200,50,10,0xFFFFFFFF,20,0xFFFFFFFF,0xA0000300]
    struct.pack_into('>10I', data, p, *values)
    struct.pack_into('>I', data, p+372, 8)
    draw = [4,0xFFFFFFFF,0xFFFFFFFF,1,0xFFFFFFFF,0xFFFFFFFF,0xFFFFFFFF,1000,8000,0xFFFFFFFF,0,16000,0xFFFFFFFF,0,3000,0xFFFFFFFF,0]
    struct.pack_into('>17I', data, p+396, *draw)
    found = find_gfxworld_summaries(bytes(data))
    assert len(found) == 1
    assert found[0].decoded_offset == p
    assert found[0].vertex_count == 1000
    assert found[0].index_count == 3000
