#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"expected one {label} patch point, found {count}")
    return source.replace(old, new, 1)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch_direct_map_render_ios.py <Quake3-iOS-root>")

    root = Path(sys.argv[1])
    path = root / "Quake3" / "client" / "cl_scrn.c"
    source = path.read_text(encoding="utf-8")

    # Quake3-iOS normally stops all frame submission when the UI VM is absent.
    # Hijacked intentionally skips UI startup and launches the map directly, so
    # that old gate leaves an otherwise CA_ACTIVE cgame running behind a black
    # screen. Permit the render loop whenever cgame is alive/loading.
    source = replace_once(
        source,
        "\tif( uivm || com_dedicated->integer )\n\t{",
        "\tif( uivm || cgvm || clc.state >= CA_LOADING || com_dedicated->integer )\n\t{",
        "SCR_UpdateScreen render gate",
    )

    # SCR_DrawScreenField has a second UI-dependent gate around the client-state
    # switch. Direct-map mode must be allowed through it when cgame exists.
    source = replace_once(
        source,
        "\tif ( uivm && !uiFullscreen ) {",
        "\tif ( (uivm && !uiFullscreen) || (!uivm && cgvm && clc.state >= CA_LOADING) ) {",
        "SCR_DrawScreenField state gate",
    )

    # Loading/primed frames may execute before UI exists. Keep cgame rendering,
    # but never VM_Call a null UI VM.
    source = replace_once(
        source,
        "\t\t\tVM_Call( uivm, UI_REFRESH, cls.realtime );\n\t\t\tVM_Call( uivm, UI_DRAW_CONNECT_SCREEN, qtrue );",
        "\t\t\tif ( uivm ) {\n\t\t\t\tVM_Call( uivm, UI_REFRESH, cls.realtime );\n\t\t\t\tVM_Call( uivm, UI_DRAW_CONNECT_SCREEN, qtrue );\n\t\t\t}",
        "loading UI calls",
    )

    # Add bounded breadcrumbs around the now-enabled direct-map render path.
    signature = "void SCR_DrawScreenField( stereoFrame_t stereoFrame ) {\n\tqboolean uiFullscreen;"
    replacement = "void SCR_DrawScreenField( stereoFrame_t stereoFrame ) {\n\tqboolean uiFullscreen;\n#ifdef IOS\n\tstatic int hijackedDirectDrawTraceCount = 0;\n\tif ( hijackedDirectDrawTraceCount < 64 )\n\t\tCom_Printf( \"HIJACKED_DRAW|ScreenField:enter|state=%d|uivm=%p|cgvm=%p|stereo=%d\\n\", clc.state, (void *)uivm, (void *)cgvm, stereoFrame );\n#endif"
    source = replace_once(source, signature, replacement, "SCR_DrawScreenField trace entry")

    active = "\t\tcase CA_ACTIVE:\n\t\t\t// always supply STEREO_CENTER as vieworg offset is now done by the engine.\n\t\t\tCL_CGameRendering(stereoFrame);"
    active_new = "\t\tcase CA_ACTIVE:\n\t\t\t// always supply STEREO_CENTER as vieworg offset is now done by the engine.\n#ifdef IOS\n\t\t\tif ( hijackedDirectDrawTraceCount < 64 ) Com_Printf( \"HIJACKED_DRAW|Active:beforeCGame|time=%d\\n\", cl.serverTime );\n#endif\n\t\t\tCL_CGameRendering(stereoFrame);\n#ifdef IOS\n\t\t\tif ( hijackedDirectDrawTraceCount < 64 ) Com_Printf( \"HIJACKED_DRAW|Active:afterCGame|time=%d\\n\", cl.serverTime );\n#endif"
    source = replace_once(source, active, active_new, "CA_ACTIVE cgame trace")

    tail = "\tif ( cl_debuggraph->integer || cl_timegraph->integer || cl_debugMove->integer ) {\n\t\tSCR_DrawDebugGraph ();\n\t}\n}"
    tail_new = "\tif ( cl_debuggraph->integer || cl_timegraph->integer || cl_debugMove->integer ) {\n\t\tSCR_DrawDebugGraph ();\n\t}\n#ifdef IOS\n\tif ( hijackedDirectDrawTraceCount < 64 ) {\n\t\tCom_Printf( \"HIJACKED_DRAW|ScreenField:exit|state=%d\\n\", clc.state );\n\t\thijackedDirectDrawTraceCount++;\n\t}\n#endif\n}"
    source = replace_once(source, tail, tail_new, "SCR_DrawScreenField trace exit")

    path.write_text(source, encoding="utf-8")
    print("patched direct-map rendering so frame submission no longer depends on uivm")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
