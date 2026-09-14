from __future__ import annotations

from dataclasses import dataclass
from . import ParseError

CHUNK_SIZE = 0x8000


@dataclass(frozen=True)
class IpakSection:
    type: int
    offset: int
    size: int
    item_count: int


@dataclass(frozen=True)
class IpakHeader:
    version: int
    declared_size: int
    sections: tuple[IpakSection, ...]


def parse_ipak_header(data: bytes, *, actual_size: int | None = None) -> IpakHeader:
    if len(data) < 16:
        raise ParseError(
            f"IPAK truncated at offset 0x{len(data):X}: header needs 0x10 bytes"
        )
    if data[:4] != b"IPAK":
        raise ParseError("invalid IPAK magic at offset 0x0")

    version = int.from_bytes(data[4:8], "big")
    if version != 0x50000:
        raise ParseError(f"unsupported IPAK version 0x{version:X} at offset 0x4")

    declared = int.from_bytes(data[8:12], "big")
    count = int.from_bytes(data[12:16], "big")
    if count > 64:
        raise ParseError(f"implausible IPAK section count {count} at offset 0xC")

    table_end = 16 + 16 * count
    if len(data) < table_end:
        raise ParseError(
            f"IPAK truncated at offset 0x{len(data):X}: "
            f"section table needs 0x{table_end:X}"
        )

    limit = actual_size if actual_size is not None else declared
    sections: list[IpakSection] = []
    for index in range(count):
        p = 16 + index * 16
        section_type = int.from_bytes(data[p : p + 4], "big")
        offset = int.from_bytes(data[p + 4 : p + 8], "big")
        size = int.from_bytes(data[p + 8 : p + 12], "big")
        item_count = int.from_bytes(data[p + 12 : p + 16], "big")

        if offset % CHUNK_SIZE:
            raise ParseError(
                f"IPAK section {index} offset 0x{offset:X} is not chunk-aligned"
            )
        if offset > limit or size > limit - offset:
            raise ParseError(
                f"IPAK section {index} out of bounds: offset=0x{offset:X} "
                f"size=0x{size:X} file=0x{limit:X}"
            )
        sections.append(IpakSection(section_type, offset, size, item_count))

    return IpakHeader(version, declared, tuple(sections))
