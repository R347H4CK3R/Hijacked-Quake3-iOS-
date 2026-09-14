from __future__ import annotations

from pathlib import Path
import argparse


def _replace_once(source: str, old: str, new: str, label: str) -> str:
    if new in source and old not in source:
        return source
    count = source.count(old)
    if count != 1:
        raise ValueError(f"expected exactly one {label} marker, found {count}")
    return source.replace(old, new, 1)


def patch_game_view_controller(source: str) -> str:
    source = _replace_once(
        source,
        'var selectedMap = ""',
        'var selectedMap = "hijacked"',
        "selectedMap",
    )
    source = _replace_once(
        source,
        "var botMatch = false",
        "var botMatch = true",
        "botMatch",
    )
    source = _replace_once(
        source,
        'self.defaults.string(forKey: "playerName")',
        'self.defaults.string(forKey: "playerName") ?? "HijackedPlayer"',
        "playerName argv",
    )
    return source


def patch_storyboard(source: str) -> str:
    old = '<viewController id="BYZ-38-t0r" customClass="GameViewController"'
    new = '<viewController storyboardIdentifier="HijackedGameVC" id="BYZ-38-t0r" customClass="GameViewController"'
    return _replace_once(source, old, new, "GameViewController storyboard")


def patch_app_delegate(source: str) -> str:
    old = '''    rootNavigationController = (UINavigationController *)[mainStoryboard instantiateViewControllerWithIdentifier:@"RootNC"];

    self.uiwindow.rootViewController = self.rootNavigationController;'''
    new = '''    UIViewController *hijackedGameController = [mainStoryboard instantiateViewControllerWithIdentifier:@"HijackedGameVC"];

    self.uiwindow.rootViewController = hijackedGameController;'''
    return _replace_once(source, old, new, "AppDelegate root controller")


def patch_runtime(root: Path) -> None:
    targets = (
        (root / "Quake3-iOS" / "GameViewController.swift", patch_game_view_controller),
        (root / "Quake3-iOS" / "Base.lproj" / "Main.storyboard", patch_storyboard),
        (root / "Quake3-iOS" / "AppDelegate.m", patch_app_delegate),
    )
    for path, patcher in targets:
        original = path.read_text(encoding="utf-8")
        patched = patcher(original)
        if patched == original:
            raise ValueError(f"startup patch made no change to {path}")
        path.write_text(patched, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Patch pinned Quake3-iOS to boot Hijacked directly.")
    parser.add_argument("runtime_root", type=Path)
    args = parser.parse_args(argv)
    patch_runtime(args.runtime_root)
    print("patched Quake3-iOS for deterministic Hijacked startup")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
