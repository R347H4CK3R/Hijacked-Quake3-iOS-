from __future__ import annotations

from pathlib import Path
import argparse


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise ValueError(f"expected exactly one {label} marker, found {count}")
    return source.replace(old, new, 1)


def inject_after_once(source: str, marker: str, addition: str, label: str) -> str:
    count = source.count(marker)
    if count != 1:
        raise ValueError(f"expected exactly one {label} marker, found {count}")
    return source.replace(marker, marker + addition, 1)


def patch_filesystem(path: Path) -> None:
    source = path.read_text(encoding="utf-8")

    # Keep this exact legacy block intact because device-ipa.yml uses its
    # presence as the guard against inserting a duplicate declaration block.
    legacy_prefix = '''#ifdef IOS
static void HijackedFsTrace(const char *message);
#define HIJACKED_FS_TRACE(x) HijackedFsTrace(x)
#else
#define HIJACKED_FS_TRACE(x) ((void)0)
#endif

'''
    detail_prefix = '''#ifdef IOS
static void HijackedFsTraceDetail(const char *stage, const char *detail);
#define HIJACKED_FS_TRACE_DETAIL(stage, detail) HijackedFsTraceDetail((stage), (detail))
#else
#define HIJACKED_FS_TRACE_DETAIL(stage, detail) ((void)0)
#endif

'''

    # HIJACKED_FS_TRACE_DETAIL is used by filesystem helpers that appear before
    # FS_Startup in files.c, so its macro must be declared near the includes,
    # before the first injected call.  The implementation remains later.
    source = replace_once(
        source,
        '#include "unzip.h"\n',
        '#include "unzip.h"\n#include <errno.h>\n\n' + detail_prefix,
        "unzip include",
    )

    if legacy_prefix not in source:
        startup_marker = 'static void FS_Startup( const char *gameName )\n'
        source = replace_once(
            source,
            startup_marker,
            legacy_prefix + startup_marker,
            "FS_Startup trace declaration anchor",
        )

    old_trace = '''static void HijackedFsTrace(const char *message)
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
#define HIJACKED_FS_TRACE(x) HijackedFsTrace(x)'''

    new_trace = '''static unsigned long hijackedFsTraceSequence = 0;

static void HijackedFsTraceDetail(const char *stage, const char *detail)
{
    const char *home;
    char tracePath[MAX_OSPATH];
    FILE *f;
    int savedErrno = errno;
    unsigned long sequence = ++hijackedFsTraceSequence;
    int milliseconds = Sys_Milliseconds();

    if (!stage)
        stage = "(null-stage)";
    if (!detail)
        detail = "";

    /* Emit before path lookup or file I/O. If the trace file itself blocks,
       the device console still identifies the last operation entered. */
    fprintf(stderr, "HIJACKED_FS|%lu|%d|%s|%s|errno=%d\\n",
            sequence, milliseconds, stage, detail, savedErrno);
    fflush(stderr);

    home = Sys_DefaultHomePath();
    if (!home || !*home) {
        errno = savedErrno;
        return;
    }

    snprintf(tracePath, sizeof(tracePath), "%sHijackedLaunchTrace.txt", home);
    f = fopen(tracePath, "a");
    if (!f) {
        errno = savedErrno;
        return;
    }

    fprintf(f, "HIJACKED_FS|%lu|%d|%s|%s|errno=%d\\n",
            sequence, milliseconds, stage, detail, savedErrno);
    fflush(f);
    fclose(f);
    errno = savedErrno;
}

static void HijackedFsTrace(const char *message)
{
    HijackedFsTraceDetail(message, "");
}'''

    source = replace_once(source, old_trace, new_trace, "filesystem trace implementation")

    source = inject_after_once(
        source,
        'void FS_AddGameDirectory( const char *path, const char *dir ) {\n',
        '\tHIJACKED_FS_TRACE_DETAIL("FS_AddGameDirectory:path", path);\n'
        '\tHIJACKED_FS_TRACE_DETAIL("FS_AddGameDirectory:dir", dir);\n',
        "FS_AddGameDirectory",
    )

    source = inject_after_once(
        source,
        'static pack_t *FS_LoadZipFile(const char *zipfile, const char *basename)\n{\n',
        '\tHIJACKED_FS_TRACE_DETAIL("FS_LoadZipFile:zipfile", zipfile);\n'
        '\tHIJACKED_FS_TRACE_DETAIL("FS_LoadZipFile:basename", basename);\n',
        "FS_LoadZipFile",
    )

    source = inject_after_once(
        source,
        'char **FS_ListFilteredFiles( const char *path, const char *extension, char *filter, int *numfiles, qboolean allowNonPureFilesOnDisk ) {\n',
        '\tHIJACKED_FS_TRACE_DETAIL("FS_ListFilteredFiles:path", path);\n'
        '\tHIJACKED_FS_TRACE_DETAIL("FS_ListFilteredFiles:extension", extension);\n',
        "FS_ListFilteredFiles",
    )

    source = inject_after_once(
        source,
        'char **FS_ListFiles( const char *path, const char *extension, int *numfiles ) {\n',
        '\tHIJACKED_FS_TRACE_DETAIL("FS_ListFiles:path", path);\n'
        '\tHIJACKED_FS_TRACE_DETAIL("FS_ListFiles:extension", extension);\n',
        "FS_ListFiles",
    )

    source = replace_once(
        source,
        '\tHIJACKED_FS_TRACE("FS_Startup:afterBasepathCvar");\n',
        '\tHIJACKED_FS_TRACE("FS_Startup:afterBasepathCvar");\n'
        '\tHIJACKED_FS_TRACE_DETAIL("FS_Startup:basepath", fs_basepath ? fs_basepath->string : "(null)");\n',
        "basepath value trace",
    )
    source = replace_once(
        source,
        '\tHIJACKED_FS_TRACE("FS_Startup:afterHomepathCvar");\n',
        '\tHIJACKED_FS_TRACE("FS_Startup:afterHomepathCvar");\n'
        '\tHIJACKED_FS_TRACE_DETAIL("FS_Startup:homepath", fs_homepath ? fs_homepath->string : "(null)");\n',
        "homepath value trace",
    )
    source = replace_once(
        source,
        '\tHIJACKED_FS_TRACE("FS_Startup:afterGameCvar");\n',
        '\tHIJACKED_FS_TRACE("FS_Startup:afterGameCvar");\n'
        '\tHIJACKED_FS_TRACE_DETAIL("FS_Startup:game", fs_gamedirvar ? fs_gamedirvar->string : "(null)");\n',
        "game value trace",
    )

    required = (
        legacy_prefix.strip(),
        detail_prefix.strip(),
        'HIJACKED_FS_TRACE_DETAIL',
        'HIJACKED_FS|%lu|%d|%s|%s|errno=%d',
        'FS_AddGameDirectory:path',
        'FS_LoadZipFile:zipfile',
        'FS_ListFilteredFiles:path',
        'FS_ListFiles:path',
        'FS_Startup:basepath',
        'FS_Startup:homepath',
        'FS_Startup:game',
    )
    for marker in required:
        if marker not in source:
            raise ValueError(f"missing required flight-recorder marker: {marker}")

    first_detail_use = source.index('HIJACKED_FS_TRACE_DETAIL("FS_AddGameDirectory:path"')
    detail_declaration = source.index('#define HIJACKED_FS_TRACE_DETAIL(stage, detail)')
    if detail_declaration >= first_detail_use:
        raise ValueError("filesystem detail trace macro must be declared before first use")

    path.write_text(source, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Add broad iOS filesystem startup flight recording.")
    parser.add_argument("runtime_root", type=Path)
    args = parser.parse_args(argv)
    patch_filesystem(args.runtime_root / "Quake3" / "qcommon" / "files.c")
    print("installed filesystem startup flight recorder")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
