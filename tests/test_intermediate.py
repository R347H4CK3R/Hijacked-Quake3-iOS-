from dataclasses import replace
from pathlib import Path
import json

from tools.intermediate.model import (
    CollisionBrush,
    ImageRef,
    MapAssetSet,
    Material,
    SpawnPoint,
    Surface,
    UnresolvedAsset,
)
from tools.intermediate.io import canonical_json_bytes, write_asset_set


def sample() -> MapAssetSet:
    return MapAssetSet(
        map_name="mp_hijacked",
        surfaces=(
            Surface(
                name="deck",
                material="m_deck",
                vertices=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
                indices=(0, 1, 2),
            ),
        ),
        materials=(Material(name="m_deck", diffuse=ImageRef(name="deck_d", key="0123456789abcdef")),),
        collision=(CollisionBrush(mins=(0.0, 0.0, -8.0), maxs=(64.0, 64.0, 0.0), contents="solid"),),
        spawns=(SpawnPoint(kind="info_player_deathmatch", origin=(8.0, 8.0, 16.0), angles=(0.0, 90.0, 0.0)),),
        unresolved=(UnresolvedAsset(kind="image", name="normal_missing", reason="not required for first render"),),
        source_sha256="a" * 64,
    )


def test_canonical_json_is_stable_and_key_sorted():
    a = canonical_json_bytes(sample())
    b = canonical_json_bytes(sample())
    assert a == b
    parsed = json.loads(a)
    assert list(parsed.keys()) == sorted(parsed.keys())
    assert parsed["map_name"] == "mp_hijacked"


def test_asset_set_digest_changes_when_geometry_changes():
    base = sample()
    changed_surface = replace(
        base.surfaces[0],
        vertices=((0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
    )
    changed = replace(base, surfaces=(changed_surface,))
    assert base.digest() != changed.digest()


def test_write_asset_set_uses_content_addressed_metadata(tmp_path: Path):
    asset_set = sample()
    result = write_asset_set(asset_set, tmp_path)
    assert result.metadata_path.exists()
    assert result.sha256 == asset_set.digest()
    assert result.metadata_path.name == f"{result.sha256}.json"
    assert result.metadata_path.read_bytes() == canonical_json_bytes(asset_set)


def test_validation_rejects_surface_with_out_of_range_index():
    broken = replace(
        sample(),
        surfaces=(Surface(name="bad", material="m_deck", vertices=((0, 0, 0),), indices=(0, 1, 0)),),
    )
    errors = broken.validate()
    assert any("index 1 out of range" in e for e in errors)
