from __future__ import annotations

from pathlib import Path
import argparse


def _replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise ValueError(f"expected exactly one {label} marker, found {count}")
    return source.replace(old, new, 1)


def _replace_after(source: str, anchor: str, old: str, new: str, label: str) -> str:
    start = source.index(anchor)
    pos = source.index(old, start)
    return source[:pos] + new + source[pos + len(old):]


def patch_cl_main(source: str) -> str:
    signature = "void CL_Frame ( int msec ) {"
    source = _replace_once(source, signature, signature + "\n#ifdef IOS\n\tstatic int hijackedFrameTraceCount = 0;\n#endif", "CL_Frame entry")
    source = _replace_after(source, signature, "\tCL_SetCGameTime();", '''#ifdef IOS
\tif (hijackedFrameTraceCount < 32)
\t\tCom_Printf("HIJACKED_FRAME|SetCGameTime:before|state=%d|serverTime=%d\\n", clc.state, cl.serverTime);
#endif
\tCL_SetCGameTime();
#ifdef IOS
\tif (hijackedFrameTraceCount < 32)
\t\tCom_Printf("HIJACKED_FRAME|SetCGameTime:after|state=%d|serverTime=%d\\n", clc.state, cl.serverTime);
#endif''', "CL_SetCGameTime")
    source = _replace_after(source, "HIJACKED_FRAME|SetCGameTime:after", "\tSCR_UpdateScreen();", '''#ifdef IOS
\tif (hijackedFrameTraceCount < 32)
\t\tCom_Printf("HIJACKED_FRAME|Screen:before|state=%d|serverTime=%d\\n", clc.state, cl.serverTime);
#endif
\tSCR_UpdateScreen();
#ifdef IOS
\tif (hijackedFrameTraceCount < 32) {
\t\tCom_Printf("HIJACKED_FRAME|Screen:after|state=%d|serverTime=%d\\n", clc.state, cl.serverTime);
\t\thijackedFrameTraceCount++;
\t}
#endif''', "SCR_UpdateScreen")
    return source


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
    signature = "void SCR_UpdateScreen( void ) {"
    source = _replace_once(source, signature, signature + "\n#ifdef IOS\n\tstatic int hijackedSwapTraceCount = 0;\n#endif", "SCR_UpdateScreen entry")
    source = _replace_after(source, signature, "\t\tre.EndFrame( &time_frontend, &time_backend );", '''#ifdef IOS
\t\tif (hijackedSwapTraceCount < 32) Com_Printf("HIJACKED_FRAME|EndFrame:before|timed=1\\n");
#endif
\t\tre.EndFrame( &time_frontend, &time_backend );
#ifdef IOS
\t\tif (hijackedSwapTraceCount < 32) { Com_Printf("HIJACKED_FRAME|EndFrame:after|timed=1\\n"); hijackedSwapTraceCount++; }
#endif''', "timed EndFrame")
    source = _replace_after(source, "HIJACKED_FRAME|EndFrame:after|timed=1", "\t\tre.EndFrame( NULL, NULL );", '''#ifdef IOS
\t\tif (hijackedSwapTraceCount < 32) Com_Printf("HIJACKED_FRAME|EndFrame:before|timed=0\\n");
#endif
\t\tre.EndFrame( NULL, NULL );
#ifdef IOS
\t\tif (hijackedSwapTraceCount < 32) { Com_Printf("HIJACKED_FRAME|EndFrame:after|timed=0\\n"); hijackedSwapTraceCount++; }
#endif''', "untimed EndFrame")
    return source


def patch_runtime(root: Path) -> None:
    targets = ((root / "Quake3" / "client" / "cl_main.c", patch_cl_main), (root / "Quake3" / "client" / "cl_cgame.c", patch_cl_cgame), (root / "Quake3" / "client" / "cl_scrn.c", patch_cl_scrn))
    for path, patcher in targets:
        source = path.read_text(encoding="utf-8")
        patched = patcher(source)
        if patched == source: raise ValueError(f"frame visibility patch made no change to {path}")
        path.write_text(patched, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("runtime_root", type=Path)
    args = parser.parse_args(argv)
    patch_runtime(args.runtime_root)
    print("instrumented frame visibility boundaries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
