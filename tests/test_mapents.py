import struct
import pytest

from tools.t6ps3.mapents import MapEntsError, locate_mapents


def fixture():
    text = b'{\n"classname" "worldspawn"\n}\n\x00'
    data = bytearray(256)
    root = 64
    struct.pack_into(">III", data, root, 0x20000100, 0xFFFFFFFF, len(text))
    struct.pack_into(">IIIIII", data, root + 12, 0, 0, 0, 0, 0, 0)
    data[root + 36 : root + 36 + len(text)] = text
    return bytes(data), root


def test_locates_following_entity_string():
    data, root = fixture()
    result = locate_mapents(data)
    assert result.offset == root
    assert result.num_entity_chars == 30
    assert result.entities[0]["classname"] == "worldspawn"


def test_rejects_ambiguous_roots():
    data, _ = fixture()
    with pytest.raises(MapEntsError):
        locate_mapents(data + data)
