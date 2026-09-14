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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Harden standalone Hijacked startup and instrument Com_Init.")
    parser.add_argument("runtime_root", type=Path)
    args = parser.parse_args(argv)

    patch_game_controller(args.runtime_root / "Quake3-iOS" / "GameViewController.swift")
    patch_common(args.runtime_root / "Quake3" / "qcommon" / "common.c")
    print("forced com_standalone=1 and instrumented Com_Init startup stages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
