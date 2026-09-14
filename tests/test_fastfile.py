import pytest

from tools.t6ps3.fastfile import ParseError, parse_fastfile_header


def test_ps3_bo2_header_extracts_version_and_map():
    data = (
        b"TAff0100"
        + bytes.fromhex("00000092")
        + b"PHEEBs71"
        + b"\0" * 4
        + b"mp_hijacked"
        + b"\0" * (32 - len("mp_hijacked"))
        + b"\0" * 256
    )
    header = parse_fastfile_header(data)
    assert header.magic == "TAff0100"
    assert header.version == 0x92
    assert header.unknown_magic == "PHEEBs71"
    assert header.map_name == "mp_hijacked"


def test_fastfile_truncation_reports_offset():
    with pytest.raises(ParseError) as error:
        parse_fastfile_header(b"TAff0100")
    assert "offset" in str(error.value).lower()
