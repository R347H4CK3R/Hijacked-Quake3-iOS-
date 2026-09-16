from pathlib import Path

from tools.sanitize_windows_asset_paths import (
    find_remaining,
    sanitize_binary,
    sanitize_text,
)


def test_sanitize_binary_rewrites_single_backslash_windows_path(tmp_path: Path):
    path = tmp_path / "player.md3"
    original = b"prefix\x00D:\\svnthis\\oa\\source\\assets\\models\\grism\\lambert2SG\x00suffix\x00"
    path.write_bytes(original)

    assert sanitize_binary(path) == 1
    data = path.read_bytes()
    assert b"D:\\" not in data
    assert b"lambert2SG\x00" in data
    assert len(data) == len(original)


def test_sanitize_text_rewrites_windows_asset_reference(tmp_path: Path):
    path = tmp_path / "player.skin"
    path.write_text("head,D:\\build\\assets\\models\\head.tga\n", encoding="utf-8")

    assert sanitize_text(path) == 1
    assert path.read_text(encoding="utf-8") == "head,head.tga\n"


def test_find_remaining_detects_drive_paths(tmp_path: Path):
    path = tmp_path / "bad.shader"
    path.write_text("map E:\\projects\\oa\\bad.tga\n", encoding="utf-8")
    assert find_remaining(tmp_path) == ["bad.shader"]
