from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import struct

T6_ASSET_NAMES = (
    "XMODELPIECES","PHYSPRESET","PHYSCONSTRAINTS","DESTRUCTIBLEDEF","XANIMPARTS","XMODEL","MATERIAL","TECHNIQUE_SET","IMAGE","SOUND","SOUND_PATCH","CLIPMAP","CLIPMAP_PVS","COMWORLD","GAMEWORLD_SP","GAMEWORLD_MP","MAP_ENTS","GFXWORLD","LIGHT_DEF","UI_MAP","FONT","FONTICON","MENULIST","MENU","LOCALIZE_ENTRY","WEAPON","WEAPONDEF","WEAPON_VARIANT","WEAPON_FULL","ATTACHMENT","ATTACHMENT_UNIQUE","WEAPON_CAMO","SNDDRIVER_GLOBALS","FX","IMPACT_FX","AITYPE","MPTYPE","MPBODY","MPHEAD","CHARACTER","XMODELALIAS","RAWFILE","STRINGTABLE","LEADERBOARD","XGLOBALS","DDL","GLASSES","EMBLEMSET","SCRIPTPARSETREE","KEYVALUEPAIRS","VEHICLEDEF","MEMORYBLOCK","ADDON_MAP_ENTS","TRACER","SKINNEDVERTS","QDB","SLUG","FOOTSTEP_TABLE","FOOTSTEPFX_TABLE","ZBARRIER"
)

@dataclass(frozen=True)
class AssetInventory:
    script_string_count: int
    dependency_count: int
    asset_count: int
    asset_array_offset: int
    asset_type_counts: dict[int, int]
    pointer_counts: dict[int, int]
    sample_strings: tuple[str | None, ...]

    def named_asset_counts(self) -> dict[str, int]:
        return {(T6_ASSET_NAMES[t] if 0 <= t < len(T6_ASSET_NAMES) else f"UNKNOWN_{t}"): count for t, count in sorted(self.asset_type_counts.items())}

def _require(data: bytes, offset: int, size: int, what: str) -> None:
    if offset < 0 or size < 0 or offset + size > len(data):
        raise ValueError(f"{what} out of bounds at 0x{offset:X}: need 0x{size:X}, file=0x{len(data):X}")

def parse_asset_inventory(decoded: bytes) -> AssetInventory:
    if len(decoded) < 64: raise ValueError("decoded zone too short for XFile header + XAssetList")
    content = decoded[40:]
    string_count, strings_ptr, dependency_count, dependencies_ptr, asset_count, assets_ptr = struct.unpack(">6I", content[:24])
    if string_count > 100000 or asset_count > 1000000 or dependency_count > 100000: raise ValueError("implausible XAssetList counts")
    pos = 24
    if strings_ptr:
        _require(content, pos, string_count*4, "string pointer table")
        string_ptrs = [int.from_bytes(content[pos+i*4:pos+i*4+4], "big") for i in range(string_count)]
        pos += string_count*4
    else: string_ptrs = []
    strings = []
    for p in string_ptrs:
        if p == 0: strings.append(None)
        elif p == 0xFFFFFFFF:
            end = content.find(b"\0", pos)
            if end < 0: raise ValueError(f"unterminated script string at 0x{40+pos:X}")
            strings.append(content[pos:end].decode("latin-1")); pos = end + 1
        else: strings.append(f"<offset:{p:08x}>")
    if dependencies_ptr:
        _require(content, pos, dependency_count*4, "dependency pointer table")
        dep_ptrs = [int.from_bytes(content[pos+i*4:pos+i*4+4], "big") for i in range(dependency_count)]
        pos += dependency_count*4
        for p in dep_ptrs:
            if p == 0xFFFFFFFF:
                end = content.find(b"\0", pos)
                if end < 0: raise ValueError(f"unterminated dependency string at 0x{40+pos:X}")
                pos = end + 1
    asset_array_offset = 40 + pos
    type_counter = Counter(); pointer_counter = Counter()
    if assets_ptr:
        _require(content, pos, asset_count*8, "asset array")
        for i in range(asset_count):
            off = pos + i*8
            asset_type = int.from_bytes(content[off:off+4], "big")
            pointer = int.from_bytes(content[off+4:off+8], "big")
            type_counter[asset_type] += 1; pointer_counter[pointer] += 1
    return AssetInventory(string_count, dependency_count, asset_count, asset_array_offset, dict(type_counter), dict(pointer_counter), tuple(strings[:32]))
