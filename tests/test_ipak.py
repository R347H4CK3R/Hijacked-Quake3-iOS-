import struct
import pytest

from tools.t6ps3.ipak import ParseError, parse_ipak_header, parse_ipak_index


def fixture_header() -> bytes:
    return (
        b"IPAK"
        + struct.pack(">III", 0x50000, 0x056C0000, 2)
        + struct.pack(">IIII", 2, 0x00040000, 0x0561FE00, 0x72E)
        + struct.pack(">IIII", 1, 0x05680000, 0x000072E0, 0x72E)
    )


def test_ipak_v5_header_and_sections():
    header = parse_ipak_header(fixture_header(), actual_size=0x056C0000)
    assert header.version == 0x50000
    assert len(header.sections) == 2
    assert {section.type for section in header.sections} == {1, 2}
    assert header.sections[0].offset % 0x8000 == 0


def test_ipak_rejects_truncated_section_table():
    with pytest.raises(ParseError):
        parse_ipak_header(b"IPAK" + b"\0" * 12, actual_size=16)


def test_ipak_index_entries_parse_big_endian():
    section = (
        struct.pack(">IIII", 0x003E5508, 0x330BD9E9, 0x00908280, 0x00003D00)
        + struct.pack(">IIII", 0x00A34298, 0x3BBAE89C, 0x000ACC00, 0x00000100)
    )
    entries = parse_ipak_index(section, item_count=2, data_section_size=0x0561FE00)
    assert entries[0].data_hash == 0x003E5508
    assert entries[0].name_hash == 0x330BD9E9
    assert entries[0].offset == 0x00908280
    assert entries[1].size == 0x100


def test_ipak_index_rejects_out_of_range_data_span():
    section = struct.pack(">IIII", 1, 2, 0x1000, 0x1000)
    with pytest.raises(ParseError):
        parse_ipak_index(section, item_count=1, data_section_size=0x1800)
