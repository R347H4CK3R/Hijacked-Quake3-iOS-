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
    in_string = False
    in_char = False
    escape = False
    i = brace
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


def patch_cl_main(source: str) -> str:
    start, end = _function_span(source, "void CL_Frame ( int msec )")
    block = source[start:end]
    block = _replace_once(
        block,
        "void CL_Frame ( int msec ) {",
        "void CL_Frame ( int msec ) {\n#ifdef IOS\n\tstatic int hijackedFrameTraceCount = 0;\n#endif",
        "CL_Frame entry",
    )
    block = _replace_once(
        block,
        "\tCL_SetCGameTime();",
        '''#ifdef IOS
\tif (hijackedFrameTraceCount < 32)
\t\tCom_Printf("HIJACKED_FRAME|SetCGameTime:before|state=%d|serverTime=%d\\n", clc.state, cl.serverTime);
#endif
\tCL_SetCGameTime();
#ifdef IOS
\tif (hijackedFrameTraceCount < 32)
\t\tCom_Printf("HIJACKED_FRAME|SetCGameTime:after|state=%d|serverTime=%d\\n", clc.state, cl.serverTime);
#endif''',
        "CL_SetCGameTime in CL_Frame",
    )
    block = _replace_once(
        block,
        "\tSCR_UpdateScreen();",
        '''#ifdef IOS
\tif (hijackedFrameTraceCount < 32)
\t\tCom_Printf("HIJACKED_FRAME|Screen:before|state=%d|serverTime=%d\\n", clc.state, cl.serverTime);
#endif
\tSCR_UpdateScreen();
#ifdef IOS
\tif (hijackedFrameTraceCount < 32) {
\t\tCom_Printf("HIJACKED_FRAME|Screen:after|state=%d|serverTime=%d\\n", clc.state, cl.serverTime);
\t\thijackedFrameTraceCount++;
\t}
#endif''',
        "SCR_UpdateScreen in CL_Frame",
    )
    return source[:start] + block + source[end:]


def patch_cl_cgame(source: str) -> str:
    old = '''void CL_CGameRendering( stereoFrame_t stereo ) {
\tVM_Call( cgvm, CG_DRAW_ACTIVE_FRAME, cl.serverTime, stereo, clc.demoplaying );
\tVM_Debug( 0 );
}'''
    new = '''void CL_CGameRendering( stereoFrame_t stereo ) {
#ifdef IOS
\tstatic int hijackedCGameFrameTraceCount = 0;
\tif (hijackedCGameFrameTraceCount < 32)
\t\tCom_Printf("HIJACKED_FRAME|CGameRender:before|serverTime=%d|stereo=%d\\n", cl.serverTime, stereo);
#endif
\tVM_Call( cgvm, CG_DRAW_ACTIVE_FRAME, cl.serverTime, stereo, clc.demoplaying );
#ifdef IOS
\tif (hijackedCGameFrameTraceCount < 32) {
\t\tCom_Printf("HIJACKED_FRAME|CGameRender:after|serverTime=%d|stereo=%d\\n", cl.serverTime, stereo);
\t\thijackedCGameFrameTraceCount++;
\t}
#endif
\tVM_Debug( 0 );
}'''
    return _replace_once(source, old, new, "CL_CGameRendering")


def patch_cl_scrn(source: str) -> str:
    start, end = _function_span(source, "void SCR_UpdateScreen( void )")
    block = source[start:end]
    block = _replace_once(
        block,
        "void SCR_UpdateScreen( void ) {",
        "void SCR_UpdateScreen( void ) {\n#ifdef IOS\n\tstatic int hijackedSwapTraceCount = 0;\n#endif",
        "SCR_UpdateScreen entry",
    )
    block = _replace_once(
        block,
        "\t\tre.EndFrame( &time_frontend, &time_backend );",
        '''#ifdef IOS
\t\tif (hijackedSwapTraceCount < 32)
\t\t\tCom_Printf("HIJACKED_FRAME|EndFrame:before|timed=1\\n");
#endif
\t\tre.EndFrame( &time_frontend, &time_backend );
#ifdef IOS
\t\tif (hijackedSwapTraceCount < 32) {
\t\t\tCom_Printf("HIJACKED_FRAME|EndFrame:after|timed=1\\n");
\t\t\thijackedSwapTraceCount++;
\t\t}
#endif''',
        "timed EndFrame",
    )
    block = _replace_once(
        block,
        "\t\tre.EndFrame( NULL, NULL );",
        '''#ifdef IOS
\t\tif (hijackedSwapTraceCount < 32)
\t\t\tCom_Printf("HIJACKED_FRAME|EndFrame:before|timed=0\\n");
#endif
\t\tre.EndFrame( NULL, NULL );
#ifdef IOS
\t\tif (hijackedSwapTraceCount < 32) {
\t\t\tCom_Printf("HIJACKED_FRAME|EndFrame:after|timed=0\\n");
\t\t\thijackedSwapTraceCount++;
\t\t}
#endif''',
        "untimed EndFrame",
    )
    return source[:start] + block + source[end:]


def patch_runtime(root: Path) -> None:
    targets = (
        (root / "Quake3" / "client" / "cl_main.c", patch_cl_main),
        (root / "Quake3" / "client" / "cl_cgame.c", patch_cl_cgame),
        (root / "Quake3" / "client" / "cl_scrn.c", patch_cl_scrn),
    )
    for path, patcher in targets:
        source = path.read_text(encoding="utf-8")
        patched = patcher(source)
        if patched == source:
            raise ValueError(f"frame visibility patch made no change to {path}")
        path.write_text(patched, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Instrument iOS cgame draw and frame swap boundaries for Hijacked black-screen diagnosis.")
    parser.add_argument("runtime_root", type=Path)
    args = parser.parse_args(argv)
    patch_runtime(args.runtime_root)
    print("instrumented CL_SetCGameTime, CG_DRAW_ACTIVE_FRAME, screen update and EndFrame boundaries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
