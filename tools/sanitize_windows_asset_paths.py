#!/usr/bin/env python3
"""Remove Windows absolute paths embedded in OpenArena runtime assets."""
from __future__ import annotations

from pathlib import Path
import re
import sys

WINDOWS_BINARY = re.compile(rb"^[A-Za-z]:[\\/]")
WINDOWS_TEXT = re.compile(r"(?i)(?<![A-Za-z0-9_])([A-Z]):\\(?:[^\\,\s{}\"']+\\)*([^\\,\s{}\"']+)")
WINDOWS_ANY = re.compile(rb"[A-Za-z]:[\\/]")
PRINTABLE = set(range(0x20, 0x7F))
TEXT_SUFFIXES = {".skin", ".shader", ".cfg", ".arena", ".bot", ".txt"}
BINARY_SUFFIXES = {".md3", ".mdr", ".iqm"}


def portable_basename(raw: bytes) -> bytes:
    value = raw.replace(b"/", b"\\")
    base = value.rsplit(b"\\", 1)[-1]
    return base or b"missing_asset"


def sanitize_binary(path: Path) -> int:
    data = bytearray(path.read_bytes())
    changed = 0
    start = 0
    n = len(data)
    while start < n:
        end = data.find(0, start)
        if end < 0:
            break
        if end > start:
            segment = bytes(data[start:end])
            if segment and all(b in PRINTABLE for b in segment) and WINDOWS_BINARY.match(segment):
                replacement = portable_basename(segment)
                if len(replacement) <= len(segment):
                    data[start:end] = replacement + b"\x00" * (len(segment) - len(replacement))
                    changed += 1
        start = end + 1
    if changed:
        path.write_bytes(data)
    return changed


def sanitize_text(path: Path) -> int:
    try:
        source = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return 0

    count = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal count
        count += 1
        return match.group(2)

    updated = WINDOWS_TEXT.sub(repl, source)
    if updated != source:
        path.write_text(updated, encoding="utf-8")
    return count


def find_remaining(root: Path) -> list[str]:
    hits: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in (TEXT_SUFFIXES | BINARY_SUFFIXES):
            continue
        if WINDOWS_ANY.search(path.read_bytes()):
            hits.append(str(path.relative_to(root)))
    return hits


def sanitize_tree(root: Path) -> tuple[int, int]:
    binary_changes = 0
    text_changes = 0
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix in BINARY_SUFFIXES:
            binary_changes += sanitize_binary(path)
        elif suffix in TEXT_SUFFIXES:
            text_changes += sanitize_text(path)
    return binary_changes, text_changes


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: sanitize_windows_asset_paths.py <asset-root>")
    root = Path(sys.argv[1])
    if not root.is_dir():
        raise SystemExit(f"asset root not found: {root}")

    binary_changes, text_changes = sanitize_tree(root)
    remaining = find_remaining(root)
    print(f"WINDOWS_PATH_SANITIZER|binary={binary_changes}|text={text_changes}|remaining={len(remaining)}")
    if remaining:
        for item in remaining[:50]:
            print(f"WINDOWS_PATH_SANITIZER|remaining|{item}")
        raise SystemExit("Windows absolute asset paths remain after sanitization")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
