from __future__ import annotations

from pathlib import Path
import argparse


def _replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise ValueError(f"expected exactly one {label} marker, found {count}")
    return source.replace(old, new, 1)


def _function_span(source: str, signature: str) -> tuple[int, int]:
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    i = brace
    in_string = False
    in_char = False
    escape = False
    while i < len(source):
        ch = source[i]
        if escape:
            escape = False
        elif ch == "\\" and (in_string or in_char):
            escape = True
        elif ch == '"' and not in_char:
            in_string = not in_string
        elif ch == "'" and not in_string:
            in_char = not in_char
        elif not in_string and not in_char:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return start, i + 1
        i += 1
    raise ValueError(f"unterminated function: {signature}")


def patch_common(source: str) -> str:
    printf_sig = "void QDECL Com_Printf( const char *fmt, ... )"
    p0, p1 = _function_span(source, printf_sig)
    block = source[p0:p1]
    marker = "\tQ_vsnprintf (msg, sizeof(msg), fmt, argptr);\n\tva_end (argptr);"
    if marker not in block:
        marker = "    Q_vsnprintf (msg, sizeof(msg), fmt, argptr);\n    va_end (argptr);"
    injected = marker + '''
#ifdef IOS
    if (!strncmp(msg, "HIJACKED_", 9)) {
        const char *hijackedHome = Sys_DefaultHomePath();
        if (hijackedHome && *hijackedHome) {
            char hijackedPath[MAX_OSPATH];
            FILE *hijackedFile;
            snprintf(hijackedPath, sizeof(hijackedPath), "%sHijackedLaunchTrace.txt", hijackedHome);
            hijackedFile = fopen(hijackedPath, "a");
            if (hijackedFile) {
                fputs(msg, hijackedFile);
                if (!*msg || msg[strlen(msg) - 1] != '\\n')
                    fputc('\\n', hijackedFile);
                fclose(hijackedFile);
            }
        }
    }
#endif'''
    block = _replace_once(block, marker, injected, "Com_Printf diagnostic mirror")
    source = source[:p0] + block + source[p1:]

    error_sig = "void QDECL Com_Error( int code, const char *fmt, ... )"
    e0, e1 = _function_span(source, error_sig)
    block = source[e0:e1]
    marker = "\tQ_vsnprintf (com_errorMessage, sizeof(com_errorMessage),fmt,argptr);\n\tva_end (argptr);"
    if marker not in block:
        marker = "    Q_vsnprintf (com_errorMessage, sizeof(com_errorMessage),fmt,argptr);\n    va_end (argptr);"
    injected = marker + '\n\tCom_Printf("HIJACKED_DIAG|Com_Error|code=%d|message=%s\\n", code, com_errorMessage);'
    block = _replace_once(block, marker, injected, "Com_Error diagnostic")
    return source[:e0] + block + source[e1:]


def patch_filesystem(source: str) -> str:
    signature = "long FS_FOpenFileRead(const char *filename, fileHandle_t *file, qboolean uniqueFILE)"
    start = source.index(signature)
    next_fn = source.index("\n/*\n=================\nFS_FindVM", start)
    block = source[start:next_fn]
    entry = signature + "\n{"
    block = _replace_once(
        block,
        entry,
        entry + '\n\tCom_Printf("HIJACKED_RESOLVE|request|file=%s|unique=%d\\n", filename ? filename : "<null>", uniqueFILE);',
        "FS_FOpenFileRead entry",
    )
    block = block.replace(
        "\t\t\t\treturn len;",
        '\t\t\t\t{ Com_Printf("HIJACKED_RESOLVE|result|file=%s|len=%ld|handle=%d|errno=%d\\n", filename, len, file ? *file : 0, errno); return len; }',
    )
    block = block.replace(
        "\t\t\t\treturn len;",
        '\t\t\t\t{ Com_Printf("HIJACKED_RESOLVE|result|file=%s|len=%ld|handle=%d|errno=%d\\n", filename, len, file ? *file : 0, errno); return len; }',
    )
    block = _replace_once(
        block,
        "\t\treturn -1;",
        '\t\t{ Com_Printf("HIJACKED_RESOLVE|result|file=%s|len=-1|handle=0|errno=%d\\n", filename, errno); return -1; }',
        "FS_FOpenFileRead missing return",
    )
    block = _replace_once(
        block,
        "\t\treturn 0;",
        '\t\t{ Com_Printf("HIJACKED_RESOLVE|result|file=%s|len=0|handle=0|errno=%d\\n", filename, errno); return 0; }',
        "FS_FOpenFileRead existence return",
    )
    return source[:start] + block + source[next_fn:]


def patch_server(source: str) -> str:
    source = _replace_once(source, "void SV_SpawnServer( char *server, qboolean killBots ) {", "void SV_SpawnServer( char *server, qboolean killBots ) {\n\tCom_Printf(\"HIJACKED_SERVER|SpawnServer:begin|map=%s|killBots=%d\\n\", server ? server : \"<null>\", killBots);", "SV_SpawnServer entry")
    source = _replace_once(source, "\tCL_MapLoading();", "\tCom_Printf(\"HIJACKED_SERVER|CL_MapLoading:before\\n\");\n\tCL_MapLoading();\n\tCom_Printf(\"HIJACKED_SERVER|CL_MapLoading:after\\n\");", "CL_MapLoading")
    source = _replace_once(source, '\tCM_LoadMap( va("maps/%s.bsp", server), qfalse, &checksum );', '\tCom_Printf("HIJACKED_SERVER|CM_LoadMap:before|map=%s\\n", server);\n\tCM_LoadMap( va("maps/%s.bsp", server), qfalse, &checksum );\n\tCom_Printf("HIJACKED_SERVER|CM_LoadMap:after|checksum=%d\\n", checksum);', "CM_LoadMap")
    source = _replace_once(source, "\tSV_InitGameProgs();", "\tCom_Printf(\"HIJACKED_SERVER|InitGameProgs:before\\n\");\n\tSV_InitGameProgs();\n\tCom_Printf(\"HIJACKED_SERVER|InitGameProgs:after\\n\");", "SV_InitGameProgs")
    source = _replace_once(source, "\tsv.state = SS_GAME;", "\tsv.state = SS_GAME;\n\tCom_Printf(\"HIJACKED_SERVER|SpawnServer:ready|map=%s\\n\", server);", "SV ready state")
    return source


def patch_world(source: str) -> str:
    source = _replace_once(source, "void RE_LoadWorldMap( const char *name ) {", "void RE_LoadWorldMap( const char *name ) {\n\tri.Printf( PRINT_ALL, \"HIJACKED_WORLD|LoadWorld:begin|%s\\n\", name ? name : \"<null>\" );", "RE_LoadWorldMap entry")
    fs_variants = ["    ri.FS_ReadFile( name, &buffer.v );", "\tri.FS_ReadFile( name, &buffer.v );"]
    matches = [v for v in fs_variants if v in source]
    if len(matches) != 1:
        raise ValueError(f"expected one FS_ReadFile world marker, found {len(matches)}")
    old = matches[0]
    source = _replace_once(source, old, old + '\n\tri.Printf( PRINT_ALL, "HIJACKED_WORLD|FS_ReadFile:after|buffer=%p\\n", buffer.v );', "world FS_ReadFile")
    stages = (
        ("R_LoadShaders( &header->lumps[LUMP_SHADERS] );", "shaders"),
        ("R_LoadLightmaps( &header->lumps[LUMP_LIGHTMAPS] );", "lightmaps"),
        ("R_LoadPlanes (&header->lumps[LUMP_PLANES]);", "planes"),
        ("R_LoadFogs( &header->lumps[LUMP_FOGS], &header->lumps[LUMP_BRUSHES], &header->lumps[LUMP_BRUSHSIDES] );", "fogs"),
        ("R_LoadSurfaces( &header->lumps[LUMP_SURFACES], &header->lumps[LUMP_DRAWVERTS], &header->lumps[LUMP_DRAWINDEXES] );", "surfaces"),
        ("R_LoadMarksurfaces (&header->lumps[LUMP_LEAFSURFACES]);", "marksurfaces"),
        ("R_LoadNodesAndLeafs (&header->lumps[LUMP_NODES], &header->lumps[LUMP_LEAFS]);", "nodes_leafs"),
        ("R_LoadSubmodels (&header->lumps[LUMP_MODELS]);", "submodels"),
        ("R_LoadVisibility( &header->lumps[LUMP_VISIBILITY] );", "visibility"),
        ("R_LoadEntities( &header->lumps[LUMP_ENTITIES] );", "entities"),
        ("R_LoadLightGrid( &header->lumps[LUMP_LIGHTGRID] );", "lightgrid"),
    )
    for statement, label in stages:
        tabbed = "\t" + statement
        candidate = tabbed if tabbed in source else "    " + statement
        replacement = f'\tri.Printf( PRINT_ALL, "HIJACKED_WORLD|Lump:{label}:before\\n" );\n' + candidate + f'\n\tri.Printf( PRINT_ALL, "HIJACKED_WORLD|Lump:{label}:after\\n" );'
        source = _replace_once(source, candidate, replacement, f"world {label}")
    source = _replace_once(source, "\ttr.world = &s_worldData;", "\ttr.world = &s_worldData;\n\tri.Printf( PRINT_ALL, \"HIJACKED_WORLD|LoadWorld:complete|surfaces=%d|shaders=%d\\n\", s_worldData.numsurfaces, s_worldData.numShaders );", "world completion")
    return source


def patch_runtime(root: Path) -> None:
    targets = (
        (root / "Quake3" / "qcommon" / "common.c", patch_common),
        (root / "Quake3" / "qcommon" / "files.c", patch_filesystem),
        (root / "Quake3" / "server" / "sv_init.c", patch_server),
        (root / "Quake3" / "renderergl1" / "tr_bsp.c", patch_world),
    )
    for path, patcher in targets:
        source = path.read_text(encoding="utf-8")
        patched = patcher(source)
        if patched == source:
            raise ValueError(f"full diagnostics patch made no change to {path}")
        path.write_text(patched, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Instrument pinned Quake3-iOS for single-pass Hijacked failure diagnosis.")
    parser.add_argument("runtime_root", type=Path)
    args = parser.parse_args(argv)
    patch_runtime(args.runtime_root)
    print("instrumented filesystem results, Com_Error, server spawn and BSP world loading")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
