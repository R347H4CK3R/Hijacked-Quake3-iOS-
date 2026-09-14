from __future__ import annotations

from pathlib import Path
import argparse


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise ValueError(f"expected exactly one {label} marker, found {count}")
    return source.replace(old, new, 1)


def patch_game_controller(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    old = '"+set", "fs_homepath", documentsDir]'
    new = '"+set", "fs_homepath", documentsDir, "+set", "com_standalone", "1"]'
    source = replace_once(source, old, new, "standalone argv")
    path.write_text(source, encoding="utf-8")


def patch_common(path: Path) -> None:
    source = path.read_text(encoding="utf-8")

    old_header = '''/*
=================
Com_Init
=================
*/
void Com_Init( char *commandLine ) {'''
    new_header = '''/*
=================
Com_Init
=================
*/
#ifdef IOS
static void HijackedComTrace(const char *message)
{
    const char *home = Sys_DefaultHomePath();
    char path[MAX_OSPATH];
    FILE *f;

    if (!home || !*home || !message)
        return;

    snprintf(path, sizeof(path), "%sHijackedLaunchTrace.txt", home);
    f = fopen(path, "a");
    if (!f)
        return;

    fprintf(f, "%s\\n", message);
    fclose(f);
}
#define HIJACKED_COM_TRACE(x) HijackedComTrace(x)
#else
#define HIJACKED_COM_TRACE(x) ((void)0)
#endif

void Com_Init( char *commandLine ) {'''
    source = replace_once(source, old_header, new_header, "Com_Init header")

    start = source.index("void Com_Init( char *commandLine ) {")
    end_marker = "\n}\n\n/*\n===============\nCom_ReadFromPipe"
    end = source.index(end_marker, start) + 2
    block = source[start:end]

    replacements = (
        ('\tchar\t*s;\n\tint\tqport;\n\n\tCom_Printf(',
         '\tchar\t*s;\n\tint\tqport;\n\n\tHIJACKED_COM_TRACE("Com_Init:entered");\n\tCom_Printf('),
        ('\tCom_InitRand();\n', '\tCom_InitRand();\n\tHIJACKED_COM_TRACE("Com_Init:afterRand");\n'),
        ('\tCom_InitPushEvent();\n', '\tCom_InitPushEvent();\n\tHIJACKED_COM_TRACE("Com_Init:afterPushEvent");\n'),
        ('\tCom_InitSmallZoneMemory();\n\tCvar_Init ();\n',
         '\tCom_InitSmallZoneMemory();\n\tHIJACKED_COM_TRACE("Com_Init:afterSmallZone");\n\tCvar_Init ();\n\tHIJACKED_COM_TRACE("Com_Init:afterCvarInit");\n'),
        ('\tCom_ParseCommandLine( commandLine );\n',
         '\tCom_ParseCommandLine( commandLine );\n\tHIJACKED_COM_TRACE("Com_Init:afterParseCommandLine");\n'),
        ('\tCbuf_Init ();\n', '\tCbuf_Init ();\n\tHIJACKED_COM_TRACE("Com_Init:afterCbufInit");\n'),
        ('\tCom_StartupVariable( NULL );\n\n\tCom_InitZoneMemory();\n\tCmd_Init ();\n',
         '\tCom_StartupVariable( NULL );\n\tHIJACKED_COM_TRACE("Com_Init:afterStartupVariable1");\n\n\tCom_InitZoneMemory();\n\tHIJACKED_COM_TRACE("Com_Init:afterZoneMemory");\n\tCmd_Init ();\n\tHIJACKED_COM_TRACE("Com_Init:afterCmdInit");\n'),
        ('\tCL_InitKeyCommands();\n', '\tCL_InitKeyCommands();\n\tHIJACKED_COM_TRACE("Com_Init:afterKeyCommands");\n'),
        ('\tFS_InitFilesystem ();\n',
         '\tHIJACKED_COM_TRACE("Com_Init:beforeFilesystem");\n\tFS_InitFilesystem ();\n\tHIJACKED_COM_TRACE("Com_Init:afterFilesystem");\n'),
        ('\tCom_ExecuteCfg();\n', '\tCom_ExecuteCfg();\n\tHIJACKED_COM_TRACE("Com_Init:afterExecuteCfg");\n'),
        ('\tCom_InitHunkMemory();\n', '\tCom_InitHunkMemory();\n\tHIJACKED_COM_TRACE("Com_Init:afterHunkMemory");\n'),
        ('\tSys_Init();\n', '\tSys_Init();\n\tHIJACKED_COM_TRACE("Com_Init:afterSysInit");\n'),
        ('\tVM_Init();\n\tSV_Init();\n',
         '\tVM_Init();\n\tHIJACKED_COM_TRACE("Com_Init:afterVMInit");\n\tSV_Init();\n\tHIJACKED_COM_TRACE("Com_Init:afterSVInit");\n'),
        ('\tCL_Init();\n#endif\n',
         '\tHIJACKED_COM_TRACE("Com_Init:beforeCLInit");\n\tCL_Init();\n\tHIJACKED_COM_TRACE("Com_Init:afterCLInit");\n#endif\n'),
        ('\tCL_StartHunkUsers( qfalse );\n',
         '\tHIJACKED_COM_TRACE("Com_Init:beforeStartHunkUsers");\n\tCL_StartHunkUsers( qfalse );\n\tHIJACKED_COM_TRACE("Com_Init:afterStartHunkUsers");\n'),
        ('\tCom_Printf ("--- Common Initialization Complete ---\\n");\n',
         '\tCom_Printf ("--- Common Initialization Complete ---\\n");\n\tHIJACKED_COM_TRACE("Com_Init:complete");\n'),
    )

    for index, (old, new) in enumerate(replacements, 1):
        block = replace_once(block, old, new, f"Com_Init stage {index}")

    source = source[:start] + block + source[end:]

    required = (
        'HijackedComTrace',
        'Com_Init:entered',
        'Com_Init:beforeFilesystem',
        'Com_Init:afterFilesystem',
        'Com_Init:beforeCLInit',
        'Com_Init:afterCLInit',
        'Com_Init:complete',
    )
    for marker in required:
        if marker not in source:
            raise ValueError(f"missing required common.c marker: {marker}")

    path.write_text(source, encoding="utf-8")


def patch_filesystem(path: Path) -> None:
    source = path.read_text(encoding="utf-8")

    init_header = '''/*
================
FS_InitFilesystem

Called only at initial startup, not when the filesystem
is resetting due to a game change
================
*/
void FS_InitFilesystem( void ) {'''
    traced_header = '''/*
================
FS_InitFilesystem

Called only at initial startup, not when the filesystem
is resetting due to a game change
================
*/
#ifdef IOS
static void HijackedFsTrace(const char *message)
{
    const char *home = Sys_DefaultHomePath();
    char path[MAX_OSPATH];
    FILE *f;

    if (!home || !*home || !message)
        return;

    snprintf(path, sizeof(path), "%sHijackedLaunchTrace.txt", home);
    f = fopen(path, "a");
    if (!f)
        return;

    fprintf(f, "%s\\n", message);
    fclose(f);
}
#define HIJACKED_FS_TRACE(x) HijackedFsTrace(x)
#else
#define HIJACKED_FS_TRACE(x) ((void)0)
#endif

void FS_InitFilesystem( void ) {'''
    source = replace_once(source, init_header, traced_header, "FS_InitFilesystem header")

    init_start = source.index("void FS_InitFilesystem( void ) {")
    init_end = source.index("\n}\n\n\n/*\n================\nFS_Restart", init_start) + 2
    block = source[init_start:init_end]
    replacements = (
        ('void FS_InitFilesystem( void ) {\n',
         'void FS_InitFilesystem( void ) {\n\tHIJACKED_FS_TRACE("FS_InitFilesystem:entered");\n'),
        ('\tCom_StartupVariable("fs_basepath");\n',
         '\tHIJACKED_FS_TRACE("FS_InitFilesystem:beforeBasepathVariable");\n\tCom_StartupVariable("fs_basepath");\n\tHIJACKED_FS_TRACE("FS_InitFilesystem:afterBasepathVariable");\n'),
        ('\tCom_StartupVariable("fs_homepath");\n',
         '\tHIJACKED_FS_TRACE("FS_InitFilesystem:beforeHomepathVariable");\n\tCom_StartupVariable("fs_homepath");\n\tHIJACKED_FS_TRACE("FS_InitFilesystem:afterHomepathVariable");\n'),
        ('\tCom_StartupVariable("fs_game");\n',
         '\tHIJACKED_FS_TRACE("FS_InitFilesystem:beforeGameVariable");\n\tCom_StartupVariable("fs_game");\n\tHIJACKED_FS_TRACE("FS_InitFilesystem:afterGameVariable");\n'),
        ('\tFS_Startup(com_basegame->string);\n',
         '\tHIJACKED_FS_TRACE("FS_InitFilesystem:beforeStartup");\n\tFS_Startup(com_basegame->string);\n\tHIJACKED_FS_TRACE("FS_InitFilesystem:afterStartup");\n'),
        ('\tif ( FS_ReadFile( "default.cfg", NULL ) <= 0 ) {\n',
         '\tHIJACKED_FS_TRACE("FS_InitFilesystem:beforeDefaultCfgRead");\n\tif ( FS_ReadFile( "default.cfg", NULL ) <= 0 ) {\n'),
        ('\tQ_strncpyz(lastValidBase, fs_basepath->string, sizeof(lastValidBase));\n',
         '\tHIJACKED_FS_TRACE("FS_InitFilesystem:afterDefaultCfgRead");\n\tQ_strncpyz(lastValidBase, fs_basepath->string, sizeof(lastValidBase));\n'),
        ('\tQ_strncpyz(lastValidGame, fs_gamedirvar->string, sizeof(lastValidGame));\n',
         '\tQ_strncpyz(lastValidGame, fs_gamedirvar->string, sizeof(lastValidGame));\n\tHIJACKED_FS_TRACE("FS_InitFilesystem:complete");\n'),
    )
    for index, (old, new) in enumerate(replacements, 1):
        block = replace_once(block, old, new, f"FS_InitFilesystem stage {index}")
    source = source[:init_start] + block + source[init_end:]

    startup_start = source.index("static void FS_Startup( const char *gameName )")
    startup_end = source.index("\n}\n\n#ifndef STANDALONE", startup_start) + 2
    startup = source[startup_start:startup_end]
    startup_replacements = (
        ('static void FS_Startup( const char *gameName )\n{\n\tconst char *homePath;\n',
         'static void FS_Startup( const char *gameName )\n{\n\tconst char *homePath;\n\n\tHIJACKED_FS_TRACE("FS_Startup:entered");\n'),
        ('\tfs_debug = Cvar_Get( "fs_debug", "0", 0 );\n',
         '\tfs_debug = Cvar_Get( "fs_debug", "0", 0 );\n\tHIJACKED_FS_TRACE("FS_Startup:afterDebugCvar");\n'),
        ('\tfs_basepath = Cvar_Get ("fs_basepath", Sys_DefaultInstallPath(), CVAR_INIT|CVAR_PROTECTED );\n',
         '\tHIJACKED_FS_TRACE("FS_Startup:beforeBasepathCvar");\n\tfs_basepath = Cvar_Get ("fs_basepath", Sys_DefaultInstallPath(), CVAR_INIT|CVAR_PROTECTED );\n\tHIJACKED_FS_TRACE("FS_Startup:afterBasepathCvar");\n'),
        ('\thomePath = Sys_DefaultHomePath();\n',
         '\tHIJACKED_FS_TRACE("FS_Startup:beforeDefaultHomePath");\n\thomePath = Sys_DefaultHomePath();\n\tHIJACKED_FS_TRACE("FS_Startup:afterDefaultHomePath");\n'),
        ('\tfs_homepath = Cvar_Get ("fs_homepath", homePath, CVAR_INIT|CVAR_PROTECTED );\n',
         '\tfs_homepath = Cvar_Get ("fs_homepath", homePath, CVAR_INIT|CVAR_PROTECTED );\n\tHIJACKED_FS_TRACE("FS_Startup:afterHomepathCvar");\n'),
        ('\tfs_gamedirvar = Cvar_Get ("fs_game", "", CVAR_INIT|CVAR_SYSTEMINFO );\n',
         '\tfs_gamedirvar = Cvar_Get ("fs_game", "", CVAR_INIT|CVAR_SYSTEMINFO );\n\tHIJACKED_FS_TRACE("FS_Startup:afterGameCvar");\n'),
        ('\tif (fs_basepath->string[0]) {\n\t\tFS_AddGameDirectory( fs_basepath->string, gameName );\n\t}\n',
         '\tif (fs_basepath->string[0]) {\n\t\tHIJACKED_FS_TRACE("FS_Startup:beforeAddBasepath");\n\t\tFS_AddGameDirectory( fs_basepath->string, gameName );\n\t\tHIJACKED_FS_TRACE("FS_Startup:afterAddBasepath");\n\t}\n'),
        ('\tfs_apppath = Cvar_Get ("fs_apppath", Sys_DefaultAppPath(), CVAR_INIT|CVAR_PROTECTED );\n',
         '\tHIJACKED_FS_TRACE("FS_Startup:beforeAppPathCvar");\n\tfs_apppath = Cvar_Get ("fs_apppath", Sys_DefaultAppPath(), CVAR_INIT|CVAR_PROTECTED );\n\tHIJACKED_FS_TRACE("FS_Startup:afterAppPathCvar");\n'),
        ('\tif (fs_apppath->string[0])\n\t\tFS_AddGameDirectory(fs_apppath->string, gameName);\n',
         '\tif (fs_apppath->string[0]) {\n\t\tHIJACKED_FS_TRACE("FS_Startup:beforeAddAppPath");\n\t\tFS_AddGameDirectory(fs_apppath->string, gameName);\n\t\tHIJACKED_FS_TRACE("FS_Startup:afterAddAppPath");\n\t}\n'),
        ('\t\tFS_CreatePath ( fs_homepath->string );\n\t\tFS_AddGameDirectory ( fs_homepath->string, gameName );\n',
         '\t\tHIJACKED_FS_TRACE("FS_Startup:beforeCreateHomePath");\n\t\tFS_CreatePath ( fs_homepath->string );\n\t\tHIJACKED_FS_TRACE("FS_Startup:afterCreateHomePath");\n\t\tHIJACKED_FS_TRACE("FS_Startup:beforeAddHomePath");\n\t\tFS_AddGameDirectory ( fs_homepath->string, gameName );\n\t\tHIJACKED_FS_TRACE("FS_Startup:afterAddHomePath");\n'),
        ('\tFS_ReorderPurePaks();\n',
         '\tHIJACKED_FS_TRACE("FS_Startup:beforeReorderPurePaks");\n\tFS_ReorderPurePaks();\n\tHIJACKED_FS_TRACE("FS_Startup:afterReorderPurePaks");\n'),
        ('\tFS_Path_f();\n',
         '\tHIJACKED_FS_TRACE("FS_Startup:beforePathPrint");\n\tFS_Path_f();\n\tHIJACKED_FS_TRACE("FS_Startup:afterPathPrint");\n'),
        ('\tCom_Printf( "%d files in pk3 files\\n", fs_packFiles );\n',
         '\tCom_Printf( "%d files in pk3 files\\n", fs_packFiles );\n\tHIJACKED_FS_TRACE("FS_Startup:complete");\n'),
    )
    for index, (old, new) in enumerate(startup_replacements, 1):
        startup = replace_once(startup, old, new, f"FS_Startup stage {index}")
    source = source[:startup_start] + startup + source[startup_end:]

    required = (
        'HijackedFsTrace',
        'FS_InitFilesystem:entered',
        'FS_InitFilesystem:beforeStartup',
        'FS_InitFilesystem:afterStartup',
        'FS_InitFilesystem:beforeDefaultCfgRead',
        'FS_InitFilesystem:complete',
        'FS_Startup:entered',
        'FS_Startup:beforeAddBasepath',
        'FS_Startup:beforeAddAppPath',
        'FS_Startup:beforeAddHomePath',
        'FS_Startup:complete',
    )
    for marker in required:
        if marker not in source:
            raise ValueError(f"missing required files.c marker: {marker}")

    path.write_text(source, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Harden standalone Hijacked startup and instrument Com_Init/filesystem startup.")
    parser.add_argument("runtime_root", type=Path)
    args = parser.parse_args(argv)

    patch_game_controller(args.runtime_root / "Quake3-iOS" / "GameViewController.swift")
    patch_common(args.runtime_root / "Quake3" / "qcommon" / "common.c")
    patch_filesystem(args.runtime_root / "Quake3" / "qcommon" / "files.c")
    print("forced com_standalone=1 and instrumented Com_Init/filesystem startup stages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
