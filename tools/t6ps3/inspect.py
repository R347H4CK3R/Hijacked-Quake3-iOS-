from __future__ import annotations

from pathlib import Path
import hashlib

_KINDS = (
    (b"TAff0100", "t6_fastfile"),
    (b"IPAK", "t6_ipak"),
    (b"2UX#", "t6_sabs"),
)


def inspect_file(path: Path) -> dict[str, object]:
    size = path.stat().st_size
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        preview = stream.read(64)
        digest.update(preview)
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)

    kind = "unknown"
    magic = b""
    for signature, name in _KINDS:
        if preview.startswith(signature):
            kind = name
            magic = signature
            break

    return {
        "path": str(path),
        "size": size,
        "sha256": digest.hexdigest(),
        "kind": kind,
        "magic_ascii": magic.decode("ascii", errors="replace"),
        "header_hex": preview.hex(),
    }
