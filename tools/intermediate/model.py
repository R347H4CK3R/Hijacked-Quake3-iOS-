from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
from typing import Any

Vec3 = tuple[float, float, float]


@dataclass(frozen=True)
class ImageRef:
    name: str
    key: str


@dataclass(frozen=True)
class Material:
    name: str
    diffuse: ImageRef | None = None


@dataclass(frozen=True)
class Surface:
    name: str
    material: str
    vertices: tuple[Vec3, ...]
    indices: tuple[int, ...]


@dataclass(frozen=True)
class CollisionBrush:
    mins: Vec3
    maxs: Vec3
    contents: str = "solid"


@dataclass(frozen=True)
class SpawnPoint:
    kind: str
    origin: Vec3
    angles: Vec3 = (0.0, 0.0, 0.0)


@dataclass(frozen=True)
class UnresolvedAsset:
    kind: str
    name: str
    reason: str


@dataclass(frozen=True)
class MapAssetSet:
    map_name: str
    surfaces: tuple[Surface, ...] = ()
    materials: tuple[Material, ...] = ()
    collision: tuple[CollisionBrush, ...] = ()
    spawns: tuple[SpawnPoint, ...] = ()
    unresolved: tuple[UnresolvedAsset, ...] = ()
    source_sha256: str = ""

    def validate(self) -> tuple[str, ...]:
        errors: list[str] = []
        material_names = {m.name for m in self.materials}
        for surface in self.surfaces:
            if surface.material not in material_names:
                errors.append(f"surface {surface.name!r} references missing material {surface.material!r}")
            vertex_count = len(surface.vertices)
            for index in surface.indices:
                if index < 0 or index >= vertex_count:
                    errors.append(
                        f"surface {surface.name!r} index {index} out of range for {vertex_count} vertices"
                    )
        for brush in self.collision:
            if any(lo > hi for lo, hi in zip(brush.mins, brush.maxs)):
                errors.append(f"collision brush has inverted bounds: {brush.mins}..{brush.maxs}")
        if self.source_sha256 and (
            len(self.source_sha256) != 64
            or any(c not in "0123456789abcdef" for c in self.source_sha256.lower())
        ):
            errors.append("source_sha256 must be a 64-character hexadecimal digest")
        return tuple(errors)

    def to_primitive(self) -> dict[str, Any]:
        return asdict(self)

    def digest(self) -> str:
        from .io import canonical_json_bytes

        return sha256(canonical_json_bytes(self)).hexdigest()
