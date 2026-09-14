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


def _replace_once_if_present(source: str, old: str, new: str, label: str) -> str:
    if new in source and old not in source:
        return source
    count = source.count(old)
    if count == 0:
        return source
    if count != 1:
        raise ValueError(f"expected at most one {label} marker, found {count}")
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
    source = _replace_once_if_present(
        source,
        '        Sys_SetHomeDir(documentsDir)\n',
        '''        Sys_SetHomeDir(documentsDir)\n\n        let traceURL = URL(fileURLWithPath: documentsDir).appendingPathComponent("HijackedLaunchTrace.txt")\n        func hijackedTrace(_ message: String) {\n            let line = message + "\\n"\n            if !FileManager.default.fileExists(atPath: traceURL.path) {\n                try? line.write(to: traceURL, atomically: true, encoding: .utf8)\n            } else if let handle = try? FileHandle(forWritingTo: traceURL) {\n                handle.seekToEndOfFile()\n                handle.write(line.data(using: .utf8)!)\n                handle.closeFile()\n            }\n        }\n        hijackedTrace("GameViewController.viewDidLoad")\n''',
        "GameViewController trace setup",
    )
    source = _replace_once_if_present(
        source,
        '            Sys_Startup(argc, &cargs)\n',
        '            hijackedTrace("before Sys_Startup")\n            Sys_Startup(argc, &cargs)\n            hijackedTrace("after Sys_Startup")\n',
        "Sys_Startup trace",
    )
    return source


def patch_storyboard(source: str) -> str:
    old = '<viewController id="BYZ-38-t0r" customClass="GameViewController"'
    new = '<viewController storyboardIdentifier="HijackedGameVC" id="BYZ-38-t0r" customClass="GameViewController"'
    return _replace_once(source, old, new, "GameViewController storyboard")


def patch_app_delegate(source: str) -> str:
    source = _replace_once_if_present(
        source,
        '#endif\n\n@implementation SDLUIKitDelegate (customDelegate)',
        '''#endif\n\nstatic void HijackedTrace(NSString *message) {\n    NSArray *paths = NSSearchPathForDirectoriesInDomains(NSDocumentDirectory, NSUserDomainMask, YES);\n    NSString *documents = [paths firstObject];\n    NSString *path = [documents stringByAppendingPathComponent:@"HijackedLaunchTrace.txt"];\n    NSString *line = [NSString stringWithFormat:@"%@\\n", message];\n    NSFileManager *fm = [NSFileManager defaultManager];\n    if (![fm fileExistsAtPath:path]) {\n        [line writeToFile:path atomically:YES encoding:NSUTF8StringEncoding error:nil];\n    } else {\n        NSFileHandle *handle = [NSFileHandle fileHandleForWritingAtPath:path];\n        [handle seekToEndOfFile];\n        [handle writeData:[line dataUsingEncoding:NSUTF8StringEncoding]];\n        [handle closeFile];\n    }\n}\n\n@implementation SDLUIKitDelegate (customDelegate)''',
        "AppDelegate trace helper",
    )
    old_root = '''    rootNavigationController = (UINavigationController *)[mainStoryboard instantiateViewControllerWithIdentifier:@"RootNC"];\n\n    self.uiwindow.rootViewController = self.rootNavigationController;'''
    instrumented_root = '''    UIViewController *hijackedGameController = [mainStoryboard instantiateViewControllerWithIdentifier:@"HijackedGameVC"];\n\n    self.uiwindow.rootViewController = hijackedGameController;'''
    source = _replace_once(source, old_root, instrumented_root, "AppDelegate root controller")

    if 'static void HijackedTrace' in source:
        source = _replace_once_if_present(
            source,
            '- (void)postFinishLaunch\n{\n    [self performSelector:@selector(hideLaunchScreen) withObject:nil afterDelay:0.0];',
            '- (void)postFinishLaunch\n{\n    HijackedTrace(@"postFinishLaunch:begin");\n    [self performSelector:@selector(hideLaunchScreen) withObject:nil afterDelay:0.0];\n    HijackedTrace(@"postFinishLaunch:afterHideLaunchScreenSchedule");',
            "postFinishLaunch begin trace",
        )
        source = _replace_once_if_present(
            source,
            '    self.uiwindow.backgroundColor = [UIColor blackColor];\n',
            '    self.uiwindow.backgroundColor = [UIColor blackColor];\n    HijackedTrace(@"postFinishLaunch:windowCreated");\n',
            "window trace",
        )
        source = _replace_once_if_present(
            source,
            '    UIStoryboard *mainStoryboard = [UIStoryboard storyboardWithName:@"Main" bundle: nil];\n',
            '    UIStoryboard *mainStoryboard = [UIStoryboard storyboardWithName:@"Main" bundle: nil];\n    HijackedTrace(@"postFinishLaunch:storyboardLoaded");\n',
            "storyboard trace",
        )
        source = _replace_once_if_present(
            source,
            '    UIViewController *hijackedGameController = [mainStoryboard instantiateViewControllerWithIdentifier:@"HijackedGameVC"];\n',
            '    UIViewController *hijackedGameController = [mainStoryboard instantiateViewControllerWithIdentifier:@"HijackedGameVC"];\n    HijackedTrace(@"postFinishLaunch:gameControllerInstantiated");\n',
            "controller trace",
        )
        source = _replace_once_if_present(
            source,
            '    self.uiwindow.rootViewController = hijackedGameController;\n',
            '    self.uiwindow.rootViewController = hijackedGameController;\n    HijackedTrace(@"postFinishLaunch:rootControllerSet");\n',
            "root trace",
        )
        source = _replace_once_if_present(
            source,
            '    [self.uiwindow makeKeyAndVisible];\n',
            '    [self.uiwindow makeKeyAndVisible];\n    HijackedTrace(@"postFinishLaunch:windowVisible");\n',
            "visible trace",
        )
    return source


def patch_runtime(root: Path) -> None:
    targets = (
        (root / "Quake3-iOS" / "GameViewController.swift", patch_game_view_controller),
        (root / "Quake3-iOS" / "Base.lproj" / "Main.storyboard", patch_storyboard),
        (root / "Quake3-iOS" / "AppDelegate.m", patch_app_delegate),
    )
    patched_text: dict[str, str] = {}
    for path, patcher in targets:
        original = path.read_text(encoding="utf-8")
        patched = patcher(original)
        if patched == original:
            raise ValueError(f"startup patch made no change to {path}")
        path.write_text(patched, encoding="utf-8")
        patched_text[path.name] = patched

    game = patched_text["GameViewController.swift"]
    delegate = patched_text["AppDelegate.m"]
    required_game = (
        'HijackedLaunchTrace.txt',
        'hijackedTrace("GameViewController.viewDidLoad")',
        'hijackedTrace("before Sys_Startup")',
    )
    required_delegate = (
        'static void HijackedTrace',
        'HijackedTrace(@"postFinishLaunch:begin")',
        'HijackedTrace(@"postFinishLaunch:windowVisible")',
    )
    for marker in required_game:
        if marker not in game:
            raise ValueError(f"real GameViewController missing required breadcrumb marker: {marker}")
    for marker in required_delegate:
        if marker not in delegate:
            raise ValueError(f"real AppDelegate missing required breadcrumb marker: {marker}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Patch pinned Quake3-iOS to boot Hijacked directly with persistent startup breadcrumbs.")
    parser.add_argument("runtime_root", type=Path)
    args = parser.parse_args(argv)
    patch_runtime(args.runtime_root)
    print("patched Quake3-iOS for deterministic Hijacked startup with breadcrumbs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
