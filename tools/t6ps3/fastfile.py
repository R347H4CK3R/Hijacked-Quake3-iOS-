from __future__ import annotations

from dataclasses import dataclass
from . import ParseError


@dataclass(frozen=True)
class FastFileHeader:
    magic: str
    version: int
    unknown_magic: str
    unknown1: int
    map_name: str


def _need(data: bytes, end: int, offset: int) -> None:
    if len(data) < end:
        raise ParseError(
            f"fastfile truncated at offset 0x{offset:X}: "
            f"need through 0x{end:X}, size=0x{len(data):X}"
        )


def parse_fastfile_header(data: bytes) -> FastFileHeader:
    _need(data, 8, 0)
    magic = data[:8].decode("ascii", errors="strict")
    if magic != "TAff0100":
        raise ParseError(f"unsupported fastfile magic at offset 0x0: {magic!r}")

    _need(data, 56, 8)
    version = int.from_bytes(data[8:12], "big")
    unknown_magic = data[12:20].rstrip(b"\0").decode("ascii", errors="replace")
    unknown1 = int.from_bytes(data[20:24], "big")
    raw_name = data[24:56].split(b"\0", 1)[0]
    map_name = raw_name.decode("ascii", errors="replace")
    return FastFileHeader(magic, version, unknown_magic, unknown1, map_name)
