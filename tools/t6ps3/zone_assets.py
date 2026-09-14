from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import IntEnum
import struct


class ZoneAssetError(ValueError):
    pass


class XAssetType(IntEnum):
    XMODELPIECES = 0
    PHYSPRESET = 1
    PHYSCONSTRAINTS = 2
    DESTRUCTIBLEDEF = 3
    XANIMPARTS = 4
    XMODEL = 5
    MATERIAL = 6
    TECHNIQUE_SET = 7
    IMAGE = 8
    SOUND = 9
    SOUND_PATCH = 10
    CLIPMAP = 11
    CLIPMAP_PVS = 12
    COMWORLD = 13
    GAMEWORLD_SP = 14
    GAMEWORLD_MP = 15
    MAP_ENTS = 16
    GFXWORLD = 17
    LIGHT_DEF = 18
    UI_MAP = 19
    FONT = 20
    FONTICON = 21
    MENULIST = 22
    MENU = 23
    LOCALIZE_ENTRY = 24
    WEAPON = 25
    WEAPONDEF = 26
    WEAPON_VARIANT = 27
    WEAPON_FULL = 28
    ATTACHMENT = 29
    ATTACHMENT_UNIQUE = 30
    WEAPON_CAMO = 31
    SNDDRIVER_GLOBALS = 32
    FX = 33
    IMPACT_FX = 34
    AITYPE = 35
    MPTYPE = 36
    MPBODY = 37
    MPHEAD = 38
    CHARACTER = 39
    XMODELALIAS = 40
    RAWFILE = 41
    STRINGTABLE = 42
    LEADERBOARD = 43
    XGLOBALS = 44
    DDL = 45
    GLASSES = 46
    EMBLEMSET = 47
    SCRIPTPARSETREE = 48
    KEYVALUEPAIRS = 49
    VEHICLEDEF = 50
    MEMORYBLOCK = 51
    ADDON_MAP_ENTS = 52
    TRACER = 53
    SKINNEDVERTS = 54
    QDB = 55
    SLUG = 56
    FOOTSTEP_TABLE = 57
    FOOTSTEPFX_TABLE = 58
    ZBARRIER = 59


@dataclass(frozen=True)
class XAssetRecord:
    index: int
    raw_type: int
    pointer: int

    @property
    def type(self) -> XAssetType | int:
        try:
            return XAssetType(self.raw_type)
        except ValueError:
            return self.raw_type

    @property
    def type_name(self) -> str:
        try:
            return XAssetType(self.raw_type).name
        except ValueError:
            return f"UNKNOWN_{self.raw_type}"


@dataclass(frozen=True)
class XAssetListView:
    script_string_count: int
    script_strings: tuple[str | None, ...]
    dependency_count: int
    asset_count: int
    assets_offset: int
    assets: tuple[XAssetRecord, ...]
    data_offset: int

    def type_counts(self) -> dict[str, int]:
        counter = Counter(asset.type_name for asset in self.assets)
        return dict(sorted(counter.items()))

    def indices(self, asset_type: XAssetType) -> tuple[int, ...]:
        return tuple(a.index for a in self.assets if a.raw_type == int(asset_type))


def _align4(value: int) -> int:
    return (value + 3) & ~3


def parse_xasset_list(data: bytes, offset: int = 40) -> XAssetListView:
    if offset < 0 or offset + 24 > len(data):
        raise ZoneAssetError("XAssetList header is truncated")

    string_count, string_ptr, dep_count, dep_ptr, asset_count, asset_ptr = struct.unpack_from(
        ">6I", data, offset
    )

    if string_count > 1_000_000 or asset_count > 1_000_000:
        raise ZoneAssetError("implausible XAssetList counts")
    if string_count and string_ptr == 0:
        raise ZoneAssetError("script string list has a null pointer")
    if dep_count and dep_ptr == 0:
        raise ZoneAssetError("dependency list has a null pointer")
    if asset_count and asset_ptr == 0:
        raise ZoneAssetError("asset list has a null pointer")

    cursor = offset + 24
    ptr_table_size = string_count * 4
    if cursor + ptr_table_size > len(data):
        raise ZoneAssetError("script string pointer table is truncated")
    string_ptrs = struct.unpack_from(f">{string_count}I", data, cursor) if string_count else ()
    cursor += ptr_table_size

    strings: list[str | None] = []
    for index, ptr in enumerate(string_ptrs):
        if ptr == 0:
            strings.append(None)
            continue
        if ptr == 0xFFFFFFFF:
            try:
                end = data.index(0, cursor)
            except ValueError as exc:
                raise ZoneAssetError(f"unterminated script string {index}") from exc
            raw = data[cursor:end]
            try:
                value = raw.decode("utf-8")
            except UnicodeDecodeError:
                value = raw.decode("latin-1")
            strings.append(value)
            cursor = end + 1
            continue
        strings.append(None)

    if dep_count:
        dep_table_size = dep_count * 4
        if cursor + dep_table_size > len(data):
            raise ZoneAssetError("dependency pointer table is truncated")
        dep_ptrs = struct.unpack_from(f">{dep_count}I", data, cursor)
        cursor += dep_table_size
        for index, ptr in enumerate(dep_ptrs):
            if ptr == 0xFFFFFFFF:
                try:
                    end = data.index(0, cursor)
                except ValueError as exc:
                    raise ZoneAssetError(f"unterminated dependency string {index}") from exc
                cursor = end + 1

    cursor = _align4(cursor)
    assets_offset = cursor
    asset_bytes = asset_count * 8
    if assets_offset + asset_bytes > len(data):
        raise ZoneAssetError("XAsset array is truncated")

    assets = []
    for index in range(asset_count):
        raw_type, pointer = struct.unpack_from(">II", data, assets_offset + index * 8)
        assets.append(XAssetRecord(index, raw_type, pointer))

    return XAssetListView(
        script_string_count=string_count,
        script_strings=tuple(strings),
        dependency_count=dep_count,
        asset_count=asset_count,
        assets_offset=assets_offset,
        assets=tuple(assets),
        data_offset=assets_offset + asset_bytes,
    )
