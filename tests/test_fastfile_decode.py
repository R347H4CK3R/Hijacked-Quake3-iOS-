import struct
import zlib
import pytest
from tools.t6ps3.fastfile_decode import AUTH_DATA_OFFSET, PS3_SALSA20_KEY, _salsa20_xor, decode_fastfile_bytes, ParseError


def make_one_chunk_fastfile(payload: bytes) -> bytes:
    xfile = struct.pack(">10I", len(payload), 0, 0, 0, 0, 0, len(payload), 0, 0, 0)
    plain = xfile + payload
    compressor = zlib.compressobj(level=9, wbits=-15)
    compressed = compressor.compress(plain) + compressor.flush()
    encrypted = _salsa20_xor(PS3_SALSA20_KEY, b"mmmmpppp", compressed)
    header = b"TAff0100" + struct.pack(">I", 146) + b"PHEEBs71" + b"\0"*4 + b"mp_hijacked" + b"\0"*(32-len("mp_hijacked")) + b"\0"*256
    assert len(header) == AUTH_DATA_OFFSET
    return header + struct.pack(">I", len(encrypted)) + encrypted + b"\0\0\0\0"


def test_salsa20_standard_zero_vector():
    assert _salsa20_xor(bytes(32), bytes(8), bytes(16)).hex() == "9a97f65b9b4c721b960a672145fca8d4"


def test_decodes_ps3_t6_chunk_and_validates_xfile_size():
    decoded, report = decode_fastfile_bytes(make_one_chunk_fastfile(b"hello-hijacked"))
    assert decoded[40:] == b"hello-hijacked"
    assert report.zone_name == "mp_hijacked"
    assert report.version == 146
    assert report.chunk_count == 1
    assert report.xfile.size == len(b"hello-hijacked")


def test_rejects_wrong_platform_version():
    source = bytearray(make_one_chunk_fastfile(b"x"))
    source[8:12] = struct.pack(">I", 147)
    with pytest.raises(ParseError, match="version"):
        decode_fastfile_bytes(bytes(source))
