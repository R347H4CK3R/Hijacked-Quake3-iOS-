from __future__ import annotations

from dataclasses import dataclass
import re
import struct

FOLLOW = 0xFFFFFFFF
_ENTITY_BLOCK_RE = re.compile(r"\{([^{}]*)\}", re.S)
_ENTITY_KV_RE = re.compile(r'"([^"]+)"\s+"([^"]*)"')


class MapEntsError(ValueError):
    pass


@dataclass(frozen=True)
class MapEntsView:
    offset: int
    name_pointer: int
    num_entity_chars: int
    entity_string: str
    entities: tuple[dict[str, str], ...]


def _parse_entities(raw: bytes) -> tuple[str, tuple[dict[str, str], ...]]:
    if not raw or raw[-1] != 0:
        raise MapEntsError("entity string is not NUL terminated")
    text = raw[:-1].decode("latin-1")
    entities: list[dict[str, str]] = []
    for match in _ENTITY_BLOCK_RE.finditer(text):
        item = {key: value for key, value in _ENTITY_KV_RE.findall(match.group(1))}
        if item:
            entities.append(item)
    if not entities:
        raise MapEntsError("entity string contains no entities")
    return text, tuple(entities)


def locate_mapents(data: bytes) -> MapEntsView:
    candidates: list[MapEntsView] = []
    marker = FOLLOW.to_bytes(4, "big")
    search = 0
    while True:
        entity_ptr_offset = data.find(marker, search)
        if entity_ptr_offset < 0:
            break
        search = entity_ptr_offset + 1
        root = entity_ptr_offset - 4
        if root < 0 or root + 36 > len(data):
            continue
        name_ptr, entity_ptr, num_chars = struct.unpack_from(">III", data, root)
        if entity_ptr != FOLLOW or not (10 <= num_chars <= 2_000_000):
            continue
        trigger_count, trigger_models, hull_count, hulls, slab_count, slabs = struct.unpack_from(">IIIIII", data, root + 12)
        if trigger_count > 100_000 or hull_count > 100_000 or slab_count > 100_000:
            continue
        start = root + 36
        end = start + num_chars
        if end > len(data) or data[start:start + 1] != b"{" or data[end - 1:end] != b"\0":
            continue
        try:
            text, entities = _parse_entities(data[start:end])
        except MapEntsError:
            continue
        candidates.append(MapEntsView(root, name_ptr, num_chars, text, entities))

    if len(candidates) != 1:
        raise MapEntsError(f"expected exactly one MapEnts root, found {len(candidates)}")
    return candidates[0]
