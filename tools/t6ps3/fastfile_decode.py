from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import struct
import zlib

class ParseError(ValueError):
    pass

PS3_T6_VERSION = 146
PS3_SALSA20_KEY = bytes.fromhex(
    "C8 0B 0E 0C 15 4B FF 91 76 A0 C5 C8 D2 4F A5 E3 "
    "EE 09 EE 90 6F 72 90 80 A3 92 75 FD 3E A7 13 39"
)
STREAM_COUNT = 4
BLOCK_HASHES_COUNT = 200
SHA1_SIZE = 20
XCHUNK_MAX_SIZE = 0x8000
AUTH_DATA_OFFSET = 0x138

@dataclass(frozen=True)
class XFileHeader:
    size: int
    external_size: int
    block_sizes: tuple[int, ...]

@dataclass(frozen=True)
class DecodeReport:
    zone_name: str
    version: int
    chunk_count: int
    compressed_payload_bytes: int
    decoded_bytes: int
    decoded_sha256: str
    xfile: XFileHeader

def _rotl32(value: int, bits: int) -> int:
    return ((value << bits) & 0xFFFFFFFF) | (value >> (32 - bits))

def _salsa20_block(key: bytes, nonce: bytes, counter: int) -> bytes:
    if len(key) != 32 or len(nonce) != 8:
        raise ValueError("Salsa20 requires a 32-byte key and 8-byte nonce")
    constants = b"expand 32-byte k"
    k0 = struct.unpack("<4I", key[:16]); k1 = struct.unpack("<4I", key[16:]); c = struct.unpack("<4I", constants); n0, n1 = struct.unpack("<2I", nonce)
    state = [c[0], *k0, c[1], n0, n1, counter & 0xFFFFFFFF, (counter >> 32) & 0xFFFFFFFF, c[2], *k1, c[3]]
    x = state.copy()
    for _ in range(10):
        x[4] ^= _rotl32((x[0]+x[12])&0xFFFFFFFF,7); x[8] ^= _rotl32((x[4]+x[0])&0xFFFFFFFF,9); x[12] ^= _rotl32((x[8]+x[4])&0xFFFFFFFF,13); x[0] ^= _rotl32((x[12]+x[8])&0xFFFFFFFF,18)
        x[9] ^= _rotl32((x[5]+x[1])&0xFFFFFFFF,7); x[13] ^= _rotl32((x[9]+x[5])&0xFFFFFFFF,9); x[1] ^= _rotl32((x[13]+x[9])&0xFFFFFFFF,13); x[5] ^= _rotl32((x[1]+x[13])&0xFFFFFFFF,18)
        x[14] ^= _rotl32((x[10]+x[6])&0xFFFFFFFF,7); x[2] ^= _rotl32((x[14]+x[10])&0xFFFFFFFF,9); x[6] ^= _rotl32((x[2]+x[14])&0xFFFFFFFF,13); x[10] ^= _rotl32((x[6]+x[2])&0xFFFFFFFF,18)
        x[3] ^= _rotl32((x[15]+x[11])&0xFFFFFFFF,7); x[7] ^= _rotl32((x[3]+x[15])&0xFFFFFFFF,9); x[11] ^= _rotl32((x[7]+x[3])&0xFFFFFFFF,13); x[15] ^= _rotl32((x[11]+x[7])&0xFFFFFFFF,18)
        x[1] ^= _rotl32((x[0]+x[3])&0xFFFFFFFF,7); x[2] ^= _rotl32((x[1]+x[0])&0xFFFFFFFF,9); x[3] ^= _rotl32((x[2]+x[1])&0xFFFFFFFF,13); x[0] ^= _rotl32((x[3]+x[2])&0xFFFFFFFF,18)
        x[6] ^= _rotl32((x[5]+x[4])&0xFFFFFFFF,7); x[7] ^= _rotl32((x[6]+x[5])&0xFFFFFFFF,9); x[4] ^= _rotl32((x[7]+x[6])&0xFFFFFFFF,13); x[5] ^= _rotl32((x[4]+x[7])&0xFFFFFFFF,18)
        x[11] ^= _rotl32((x[10]+x[9])&0xFFFFFFFF,7); x[8] ^= _rotl32((x[11]+x[10])&0xFFFFFFFF,9); x[9] ^= _rotl32((x[8]+x[11])&0xFFFFFFFF,13); x[10] ^= _rotl32((x[9]+x[8])&0xFFFFFFFF,18)
        x[12] ^= _rotl32((x[15]+x[14])&0xFFFFFFFF,7); x[13] ^= _rotl32((x[12]+x[15])&0xFFFFFFFF,9); x[14] ^= _rotl32((x[13]+x[12])&0xFFFFFFFF,13); x[15] ^= _rotl32((x[14]+x[13])&0xFFFFFFFF,18)
    return struct.pack("<16I", *(((x[i]+state[i])&0xFFFFFFFF) for i in range(16)))

def _salsa20_xor(key: bytes, nonce: bytes, data: bytes) -> bytes:
    result = bytearray(len(data))
    for block_index, start in enumerate(range(0, len(data), 64)):
        stream = _salsa20_block(key, nonce, block_index); part = data[start:start+64]
        result[start:start+len(part)] = bytes(a ^ b for a, b in zip(part, stream))
    return bytes(result)

def _initial_hash_blocks(zone_name: str) -> bytearray:
    name = zone_name.encode("ascii")[:31]
    if not name: raise ParseError("fastfile zone name is empty")
    result = bytearray(BLOCK_HASHES_COUNT * STREAM_COUNT * SHA1_SIZE); name_offset = 0
    for pos in range(0, len(result), 4):
        result[pos:pos+4] = bytes([name[name_offset]]) * 4; name_offset = (name_offset + 1) % len(name)
    return result

def _hash_block_view(blocks: bytearray, indices: list[int], stream: int) -> memoryview:
    pos = indices[stream] * STREAM_COUNT * SHA1_SIZE + stream * SHA1_SIZE
    return memoryview(blocks)[pos:pos+SHA1_SIZE]

def decode_fastfile_bytes(source: bytes) -> tuple[bytes, DecodeReport]:
    if len(source) < AUTH_DATA_OFFSET: raise ParseError(f"fastfile is too short: {len(source)} bytes")
    if source[:8] != b"TAff0100": raise ParseError("expected signed Treyarch T6 magic TAff0100")
    version = int.from_bytes(source[8:12], "big")
    if version != PS3_T6_VERSION: raise ParseError(f"expected PS3 T6 version {PS3_T6_VERSION}, got {version}")
    if source[12:20] != b"PHEEBs71": raise ParseError("invalid T6 authentication header magic")
    zone_name = source[24:56].split(b"\0",1)[0].decode("ascii")
    blocks = _initial_hash_blocks(zone_name); indices = [0] * STREAM_COUNT; offset = AUTH_DATA_OFFSET; chunk_count = 0; compressed_payload_bytes = 0; decoded = bytearray()
    while True:
        if offset + 4 > len(source): raise ParseError(f"missing XChunk length at offset 0x{offset:X}")
        chunk_size = int.from_bytes(source[offset:offset+4], "big"); offset += 4
        if chunk_size == 0: break
        if chunk_size > XCHUNK_MAX_SIZE: raise ParseError(f"invalid XChunk size 0x{chunk_size:X} at offset 0x{offset-4:X}")
        if offset + chunk_size > len(source): raise ParseError(f"XChunk at 0x{offset:X} overruns file")
        stream = chunk_count % STREAM_COUNT; hash_block = bytes(_hash_block_view(blocks, indices, stream)); encrypted = source[offset:offset+chunk_size]
        compressed = _salsa20_xor(PS3_SALSA20_KEY, hash_block[:8], encrypted); digest = hashlib.sha1(compressed).digest(); indices[stream] = (indices[stream] + 1) % BLOCK_HASHES_COUNT
        next_hash = _hash_block_view(blocks, indices, stream)
        for index, value in enumerate(digest): next_hash[index] ^= value
        try: decoded.extend(zlib.decompress(compressed, -zlib.MAX_WBITS))
        except zlib.error as exc: raise ParseError(f"raw DEFLATE failed for XChunk {chunk_count} (stream {stream}, file offset 0x{offset:X}): {exc}") from exc
        compressed_payload_bytes += chunk_size; chunk_count += 1; offset += chunk_size
    if len(decoded) < 40: raise ParseError("decoded zone does not contain a complete XFile header")
    words = struct.unpack(">10I", decoded[:40]); xfile = XFileHeader(words[0], words[1], tuple(words[2:]))
    if xfile.size != len(decoded)-40: raise ParseError(f"XFile size mismatch: header={xfile.size}, actual={len(decoded)-40}")
    report = DecodeReport(zone_name, version, chunk_count, compressed_payload_bytes, len(decoded), hashlib.sha256(decoded).hexdigest(), xfile)
    return bytes(decoded), report

def decode_fastfile(path: Path, output: Path | None = None) -> DecodeReport:
    decoded, report = decode_fastfile_bytes(path.read_bytes())
    if output is not None: output.write_bytes(decoded)
    return report
