from pathlib import Path

from tools.t6ps3.inspect import inspect_file


def test_identifies_fastfile(tmp_path: Path):
    path = tmp_path / "x.ff"
    path.write_bytes(b"TAff0100" + b"\0" * 24)
    report = inspect_file(path)
    assert report["kind"] == "t6_fastfile"
    assert report["magic_ascii"] == "TAff0100"


def test_identifies_ipak(tmp_path: Path):
    path = tmp_path / "x.ipak"
    path.write_bytes(b"IPAK" + b"\0" * 28)
    assert inspect_file(path)["kind"] == "t6_ipak"


def test_identifies_sabs(tmp_path: Path):
    path = tmp_path / "x.sabs"
    path.write_bytes(b"2UX#" + b"\0" * 28)
    assert inspect_file(path)["kind"] == "t6_sabs"
