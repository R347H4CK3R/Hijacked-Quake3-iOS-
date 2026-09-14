import struct
from tools.t6ps3.probe_fastfile import parse_asset_inventory, T6_ASSET_NAMES


def make_decoded_zone():
    ptrs = [0, 0xFFFFFFFF, 0xFFFFFFFF]
    inline = b"t6_skybox\0p6_hijacked_engine_lod0\0"
    assets = [(5, 0xFFFFFFFF), (17, 0xFFFFFFFF), (11, 0xFFFFFFFF)]
    content = (
        struct.pack(">6I", 3, 0xFFFFFFFF, 0, 0, len(assets), 0xFFFFFFFF)
        + b"".join(struct.pack(">I", p) for p in ptrs)
        + inline
        + b"".join(struct.pack(">II", t, p) for t, p in assets)
    )
    return struct.pack(">10I", len(content), 0, 0,0,0,0,len(content),0,0,0) + content


def test_parses_strings_and_asset_type_counts():
    inv = parse_asset_inventory(make_decoded_zone())
    assert inv.script_string_count == 3
    assert inv.asset_count == 3
    assert inv.asset_array_offset == 40 + 24 + 12 + len(b"t6_skybox\0p6_hijacked_engine_lod0\0")
    assert inv.asset_type_counts[5] == 1
    assert inv.asset_type_counts[17] == 1
    assert T6_ASSET_NAMES[17] == "GFXWORLD"


def test_rejects_truncated_string_pointer_table():
    bad = make_decoded_zone()[:40+24+4]
    try:
        parse_asset_inventory(bad)
    except ValueError as exc:
        assert "string pointer table" in str(exc)
    else:
        raise AssertionError("expected ValueError")
