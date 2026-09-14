import struct
import pytest

from tools.t6ps3.ipak import ParseError, parse_ipak_header


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
