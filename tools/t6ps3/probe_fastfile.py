from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import struct

T6_ASSET_NAMES = (
    'XMODELPIECES','PHYSPRESET','PHYSCONSTRAINTS','DESTRUCTIBLEDEF','XANIMPARTS','XMODEL','MATERIAL','TECHNIQUE_SET','IMAGE','SOUND','SOUND_PATCH','CLIPMAP','CLIPMAP_PVS','COMWORLD','GAMEWORLD_SP','GAMEWORLD_MP','MAP_ENTS','GFXWORLD','LIGHT_DEF','UI_MAP','FONT','FONTICON','MENULIST','MENU','LOCALIZE_ENTRY','WEAPON','WEAPONDEF','WEAPON_VARIANT','WEAPON_FULL','ATTACHMENT','ATTACHMENT_UNIQUE','WEAPON_CAMO','SNDDRIVER_GLOBALS','FX','IMPACT_FX','AITYPE','MPTYPE','MPBODY','MPHEAD','CHARACTER','XMODELALIAS','RAWFILE','STRINGTABLE','LEADERBOARD','XGLOBALS','DDL','GLASSES','EMBLEMSET','SCRIPTPARSETREE','KEYVALUEPAIRS','VEHICLEDEF','MEMORYBLOCK','ADDON_MAP_ENTS','TRACER','SKINNEDVERTS','QDB','SLUG','FOOTSTEP_TABLE','FOOTSTEPFX_TABLE','ZBARRIER'
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
        return {
            (T6_ASSET_NAMES[t] if 0 <= t < len(T6_ASSET_NAMES) else f'UNKNOWN_{t}'): count
            for t, count in sorted(self.asset_type_counts.items())
        }


def _require(data: bytes, offset: int, size: int, what: str) -> None:
    if offset < 0 or size < 0 or offset + size > len(data):
        raise ValueError(f'{what} out of bounds at 0x{offset:X}: need 0x{size:X}, file=0x{len(data):X}')


def parse_asset_inventory(decoded: bytes) -> AssetInventory:
    if len(decoded) < 40 + 24:
        raise ValueError('decoded zone too short for XFile header + XAssetList')
    content = decoded[40:]
    string_count, strings_ptr, dependency_count, dependencies_ptr, asset_count, assets_ptr = struct.unpack('>6I', content[:24])
    if string_count > 100_000 or asset_count > 1_000_000 or dependency_count > 100_000:
        raise ValueError('implausible XAssetList counts')

    pos = 24
    if strings_ptr:
        _require(content, pos, string_count * 4, 'string pointer table')
        string_ptrs = [int.from_bytes(content[pos+i*4:pos+i*4+4], 'big') for i in range(string_count)]
        pos += string_count * 4
    else:
        string_ptrs = []

    strings: list[str | None] = []
    for p in string_ptrs:
        if p == 0:
            strings.append(None)
        elif p == 0xFFFFFFFF:
            end = content.find(b'\0', pos)
            if end < 0:
                raise ValueError(f'unterminated script string at 0x{40+pos:X}')
            strings.append(content[pos:end].decode('latin-1'))
            pos = end + 1
        else:
            strings.append(f'<offset:{p:08x}>')

    if dependencies_ptr:
        _require(content, pos, dependency_count * 4, 'dependency pointer table')
        dep_ptrs = [int.from_bytes(content[pos+i*4:pos+i*4+4], 'big') for i in range(dependency_count)]
        pos += dependency_count * 4
        for p in dep_ptrs:
            if p == 0xFFFFFFFF:
                end = content.find(b'\0', pos)
                if end < 0:
                    raise ValueError(f'unterminated dependency string at 0x{40+pos:X}')
                pos = end + 1

    asset_array_offset = 40 + pos
    if assets_ptr:
        _require(content, pos, asset_count * 8, 'asset array')
        type_counter: Counter[int] = Counter()
        pointer_counter: Counter[int] = Counter()
        for i in range(asset_count):
            off = pos + i * 8
            asset_type = int.from_bytes(content[off:off+4], 'big')
            pointer = int.from_bytes(content[off+4:off+8], 'big')
            type_counter[asset_type] += 1
            pointer_counter[pointer] += 1
    else:
        type_counter = Counter()
        pointer_counter = Counter()

    return AssetInventory(
        script_string_count=string_count,
        dependency_count=dependency_count,
        asset_count=asset_count,
        asset_array_offset=asset_array_offset,
        asset_type_counts=dict(type_counter),
        pointer_counts=dict(pointer_counter),
        sample_strings=tuple(strings[:32]),
    )


@dataclass(frozen=True)
class GfxWorldSummary:
    decoded_offset: int
    plane_count: int
    node_count: int
    surface_count: int
    cell_count: int
    reflection_probe_count: int
    lightmap_count: int
    vertex_count: int
    vertex_data_size0: int
    vertex_data_size1: int
    index_count: int


def _pointer_like(v: int) -> bool:
    return v in (0, 0xFFFFFFFF, 0xFFFFFFFE) or v >= 0x80000000


def find_gfxworld_summaries(decoded: bytes) -> tuple[GfxWorldSummary, ...]:
    results: list[GfxWorldSummary] = []
    for p in range(40, max(40, len(decoded) - 464), 4):
        try:
            name_ptr, base_ptr, plane, node, surface, aabb_count, aabb_ptr, leaf_count, leaf_ptr, sky_ptr = struct.unpack_from('>10I', decoded, p)
        except struct.error:
            break
        if not (0 < plane < 500000 and 0 < node < 500000 and 0 < surface < 500000):
            continue
        if not (0 <= aabb_count < 500000 and 0 <= leaf_count < 5000000):
            continue
        if not all(_pointer_like(v) for v in (name_ptr, base_ptr, aabb_ptr, leaf_ptr, sky_ptr)):
            continue
        cell_count = struct.unpack_from('>I', decoded, p + 372)[0]
        if not (0 < cell_count < 65536):
            continue
        draw = struct.unpack_from('>17I', decoded, p + 396)
        refl_count, refl_ptr, refl_tex, lightmap_count, lm_ptr, lm_primary, lm_secondary, vertex_count, vdata0_size, vd0_ptr, vd0_vb, vdata1_size, vd1_ptr, vd1_vb, index_count, indices_ptr, index_buffer = draw
        if not (0 < vertex_count < 10_000_000 and 0 < index_count < 30_000_000):
            continue
        if not (0 < vdata0_size < 200_000_000 and 0 < vdata1_size < 200_000_000):
            continue
        if not (0 <= refl_count < 4096 and 0 <= lightmap_count < 4096):
            continue
        if not all(_pointer_like(v) for v in (refl_ptr, refl_tex, lm_ptr, lm_primary, lm_secondary, vd0_ptr, vd0_vb, vd1_ptr, vd1_vb, indices_ptr, index_buffer)):
            continue
        results.append(GfxWorldSummary(
            decoded_offset=p,
            plane_count=plane,
            node_count=node,
            surface_count=surface,
            cell_count=cell_count,
            reflection_probe_count=refl_count,
            lightmap_count=lightmap_count,
            vertex_count=vertex_count,
            vertex_data_size0=vdata0_size,
            vertex_data_size1=vdata1_size,
            index_count=index_count,
        ))
    return tuple(results)
