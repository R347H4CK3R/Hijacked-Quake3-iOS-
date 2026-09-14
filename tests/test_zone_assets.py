import struct
from tools.t6ps3.zone_assets import parse_xasset_list, XAssetType


def _fixture():
    header = struct.pack('>6I', 2, 0xffffffff, 0, 0, 3, 0xffffffff)
    ptrs = struct.pack('>2I', 0, 0xffffffff)
    strings = b'hello\0'
    pad = b'\0' * ((4 - ((len(header)+len(ptrs)+len(strings)) % 4)) % 4)
    assets = b''.join([
        struct.pack('>II', XAssetType.XMODEL, 0xffffffff),
        struct.pack('>II', XAssetType.GFXWORLD, 0xffffffff),
        struct.pack('>II', XAssetType.CLIPMAP, 0xffffffff),
    ])
    return header + ptrs + strings + pad + assets


def test_parse_xasset_list_walks_script_strings_and_assets():
    parsed = parse_xasset_list(_fixture(), 0)
    assert parsed.script_string_count == 2
    assert parsed.script_strings == (None, 'hello')
    assert parsed.asset_count == 3
    assert [a.type for a in parsed.assets] == [XAssetType.XMODEL, XAssetType.GFXWORLD, XAssetType.CLIPMAP]
    assert parsed.assets_offset % 4 == 0


def test_parse_realistic_asset_type_counts():
    parsed = parse_xasset_list(_fixture(), 0)
    counts = parsed.type_counts()
    assert counts['XMODEL'] == 1
    assert counts['GFXWORLD'] == 1
    assert counts['CLIPMAP'] == 1
