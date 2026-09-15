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
        'self.defaults.string(forKey: "playerName")',
        'self.defaults.string(forKey: "playerName") ?? "HijackedPlayer"',
        "playerName argv",
    )
    source = _replace_once(
        source,
        'var argv: [String?] = [ Bundle.main.resourcePath! + "/quake3", "+set", "com_basegame", "baseq3", "+name", self.defaults.string(forKey: "playerName") ?? "HijackedPlayer"]',
        'var argv: [String?] = [ Bundle.main.resourcePath! + "/quake3", "+set", "com_basegame", "baseq3", "+name", self.defaults.string(forKey: "playerName") ?? "HijackedPlayer", "+set", "fs_basepath", Bundle.main.resourcePath!, "+set", "fs_apppath", Bundle.main.resourcePath!, "+set", "fs_homepath", documentsDir, "+set", "logfile", "2"]',
        "bundled baseq3 filesystem argv",
    )
    source = _replace_once_if_present(
        source,
        '''                if self.botMatch {
                    argv.append("+map")
                } else {
                    argv.append("+spmap")
                }
                argv.append(self.selectedMap)

                if !self.botMatch {
                    argv.append("+g_spSkill")
                    argv.append(String(self.selectedDifficulty))
                }
''',
        '''                argv.append("+map")
                argv.append(self.selectedMap)
''',
        "direct map launch",
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


def patch_sys_main(source: str) -> str:
    header = '''#ifdef IOS\nvoid Sys_Startup( int argc, char **argv )\n#else\nint main( int argc, char **argv )\n#endif // IOS'''
    helper = '''#ifdef IOS\nstatic void HijackedEngineTrace(const char *message)\n{\n    const char *home = Sys_DefaultHomePath();\n    char path[MAX_OSPATH];\n    FILE *f;\n\n    if (!home || !*home || !message)\n        return;\n\n    snprintf(path, sizeof(path), "%sHijackedLaunchTrace.txt", home);\n    f = fopen(path, "a");\n    if (!f)\n        return;\n\n    fprintf(f, "%s\\n", message);\n    fclose(f);\n}\n#endif\n\n''' + header
    source = _replace_once(source, header, helper, "Sys_Startup trace helper")
    source = _replace_once_if_present(
        source,
        'char  commandLine[ MAX_STRING_CHARS ] = { 0 };',
        'char  commandLine[ MAX_STRING_CHARS ] = { 0 };\n#ifdef IOS\n\tHijackedEngineTrace("Sys_Startup:entered");\n#endif',
        "Sys_Startup entered breadcrumb",
    )
    source = _replace_once_if_present(
        source,
        'SDL_GetVersion( &ver );',
        'SDL_GetVersion( &ver );\n#ifdef IOS\n\tHijackedEngineTrace("Sys_Startup:afterSDLVersion");\n#endif',
        "SDL version breadcrumb",
    )
    source = _replace_once_if_present(
        source,
        'Sys_PlatformInit( );',
        'Sys_PlatformInit( );\n#ifdef IOS\n\tHijackedEngineTrace("Sys_Startup:afterPlatformInit");\n#endif',
        "platform init breadcrumb",
    )
    source = _replace_once_if_present(
        source,
        'Sys_Milliseconds( );',
        'Sys_Milliseconds( );\n#ifdef IOS\n\tHijackedEngineTrace("Sys_Startup:afterMilliseconds");\n#endif',
        "milliseconds breadcrumb",
    )
    source = _replace_once_if_present(
        source,
        'Sys_ParseArgs( argc, argv );',
        'Sys_ParseArgs( argc, argv );\n#ifdef IOS\n\tHijackedEngineTrace("Sys_Startup:afterParseArgs");\n#endif',
        "parse args breadcrumb",
    )
    source = _replace_once_if_present(
        source,
        'Sys_SetBinaryPath( Sys_Dirname( argv[ 0 ] ) );',
        'Sys_SetBinaryPath( Sys_Dirname( argv[ 0 ] ) );\n#ifdef IOS\n\tHijackedEngineTrace("Sys_Startup:afterBinaryPath");\n#endif',
        "binary path breadcrumb",
    )
    source = _replace_once_if_present(
        source,
        'Sys_SetDefaultInstallPath( DEFAULT_BASEDIR );',
        'Sys_SetDefaultInstallPath( DEFAULT_BASEDIR );\n#ifdef IOS\n\tHijackedEngineTrace("Sys_Startup:afterInstallPath");\n#endif',
        "install path breadcrumb",
    )
    source = _replace_once_if_present(
        source,
        'CON_Init( );\n\tCom_Init( commandLine );\n\tNET_Init( );',
        'CON_Init( );\n#ifdef IOS\n\tHijackedEngineTrace("Sys_Startup:afterConsoleInit");\n\tHijackedEngineTrace("Sys_Startup:beforeComInit");\n#endif\n\tCom_Init( commandLine );\n#ifdef IOS\n\tHijackedEngineTrace("Sys_Startup:afterComInit");\n#endif\n\tNET_Init( );\n#ifdef IOS\n\tHijackedEngineTrace("Sys_Startup:afterNetInit");\n#endif',
        "engine init breadcrumbs",
    )
    source = _replace_once_if_present(
        source,
        'while( 1 )',
        '#ifdef IOS\n\tqboolean hijackedFirstFrame = qtrue;\n#endif\n\twhile( 1 )',
        "first frame state",
    )
    source = _replace_once_if_present(
        source,
        'Com_Frame( );',
        '#ifdef IOS\n\t\tif (hijackedFirstFrame)\n\t\t\tHijackedEngineTrace("Sys_Startup:firstFrame:before");\n#endif\n\t\tCom_Frame( );\n#ifdef IOS\n\t\tif (hijackedFirstFrame) {\n\t\t\tHijackedEngineTrace("Sys_Startup:firstFrame:after");\n\t\t\thijackedFirstFrame = qfalse;\n\t\t}\n#endif',
        "first frame breadcrumbs",
    )
    return source


def patch_runtime(root: Path) -> None:
    targets = (
        (root / "Quake3-iOS" / "GameViewController.swift", patch_game_view_controller),
        (root / "Quake3-iOS" / "Base.lproj" / "Main.storyboard", patch_storyboard),
        (root / "Quake3-iOS" / "AppDelegate.m", patch_app_delegate),
        (root / "Quake3" / "sys" / "sys_main.c", patch_sys_main),
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
    engine = patched_text["sys_main.c"]
    required_game = (
        'HijackedLaunchTrace.txt',
        'hijackedTrace("GameViewController.viewDidLoad")',
        'hijackedTrace("before Sys_Startup")',
        '"+set", "fs_basepath", Bundle.main.resourcePath!',
        '"+set", "fs_apppath", Bundle.main.resourcePath!',
        '"+set", "fs_homepath", documentsDir',
        '"+set", "logfile", "2"',
        'argv.append("+map")',
    )
    required_delegate = (
        'static void HijackedTrace',
        'HijackedTrace(@"postFinishLaunch:begin")',
        'HijackedTrace(@"postFinishLaunch:windowVisible")',
    )
    required_engine = (
        'static void HijackedEngineTrace',
        'HijackedEngineTrace("Sys_Startup:entered")',
        'HijackedEngineTrace("Sys_Startup:beforeComInit")',
        'HijackedEngineTrace("Sys_Startup:afterComInit")',
        'HijackedEngineTrace("Sys_Startup:firstFrame:before")',
        'HijackedEngineTrace("Sys_Startup:firstFrame:after")',
    )
    for marker in required_game:
        if marker not in game:
            raise ValueError(f"real GameViewController missing required breadcrumb marker: {marker}")
    for marker in required_delegate:
        if marker not in delegate:
            raise ValueError(f"real AppDelegate missing required breadcrumb marker: {marker}")
    for marker in required_engine:
        if marker not in engine:
            raise ValueError(f"real sys_main.c missing required breadcrumb marker: {marker}")
    if 'var botMatch = true' in game:
        raise ValueError("Hijacked direct launch must not force botMatch when bot_enable is disabled")
    if 'argv.append("+spmap")' in game:
        raise ValueError("Hijacked direct launch must not depend on single-player arena metadata")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Patch pinned Quake3-iOS to boot Hijacked directly with persistent startup breadcrumbs.")
    parser.add_argument("runtime_root", type=Path)
    args = parser.parse_args(argv)
    patch_runtime(args.runtime_root)
    print("patched Quake3-iOS for deterministic Hijacked startup with explicit LiveContainer-safe paths and first-frame diagnostics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
