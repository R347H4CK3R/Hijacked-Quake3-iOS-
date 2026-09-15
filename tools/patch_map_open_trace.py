from __future__ import annotations

from pathlib import Path
import argparse


def replace_once(source: str, old: str, new: str, label: str) -> str:
    if new in source:
        return source
    count = source.count(old)
    if count != 1:
        raise ValueError(f"expected exactly one {label} marker, found {count}")
    return source.replace(old, new, 1)


def patch_filesystem_reads(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    old = """long FS_FOpenFileRead(const char *filename, fileHandle_t *file, qboolean uniqueFILE)\n{\n\tsearchpath_t *search;\n"""
    new = """long FS_FOpenFileRead(const char *filename, fileHandle_t *file, qboolean uniqueFILE)\n{\n\tHIJACKED_FS_TRACE_DETAIL(\"FS_FOpenFileRead:filename\", filename);\n\tsearchpath_t *search;\n"""
    source = replace_once(source, old, new, "FS_FOpenFileRead entry")
    if 'FS_FOpenFileRead:filename' not in source:
        raise ValueError("missing FS_FOpenFileRead trace marker")
    path.write_text(source, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Trace every virtual filesystem read so Hijacked BSP/map load can be located precisely.")
    parser.add_argument("runtime_root", type=Path)
    args = parser.parse_args(argv)
    patch_filesystem_reads(args.runtime_root / "Quake3" / "qcommon" / "files.c")
    print("installed Hijacked map-open tracing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
