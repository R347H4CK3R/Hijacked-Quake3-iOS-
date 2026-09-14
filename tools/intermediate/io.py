from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

from .model import MapAssetSet


@dataclass(frozen=True)
class WriteResult:
    metadata_path: Path
    sha256: str


def canonical_json_bytes(asset_set: MapAssetSet) -> bytes:
    payload = asset_set.to_primitive()
    return (json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def write_asset_set(asset_set: MapAssetSet, out_dir: Path) -> WriteResult:
    errors = asset_set.validate()
    if errors:
        raise ValueError("; ".join(errors))
    digest = asset_set.digest()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{digest}.json"
    path.write_bytes(canonical_json_bytes(asset_set))
    return WriteResult(metadata_path=path, sha256=digest)
