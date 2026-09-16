#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_ioq3_draw_trace.py <ioq3-root>")

path = Path(sys.argv[1]) / "code/cgame/cg_view.c"
source = path.read_text(encoding="utf-8")

old_entry = "void CG_DrawActiveFrame( int serverTime, stereoFrame_t stereoView, qboolean demoPlayback ) {\n\tint\t\tinwater;"
new_entry = "void CG_DrawActiveFrame( int serverTime, stereoFrame_t stereoView, qboolean demoPlayback ) {\n\tint\t\tinwater;\n\tstatic int hijackedDrawTraceCount = 0;\n\tif ( hijackedDrawTraceCount < 64 )\n\t\tCG_Printf( \"HIJACKED_CGAME_DRAW|enter|time=%d|info=%d|snap=%p\\n\", serverTime, cg.infoScreenText[0] != 0, (void *)cg.snap );"
if source.count(old_entry) != 1:
    raise SystemExit(f"expected one CG_DrawActiveFrame entry, found {source.count(old_entry)}")
source = source.replace(old_entry, new_entry, 1)

old_info = "\tif ( cg.infoScreenText[0] != 0 ) {\n\t\tCG_DrawInformation();\n\t\treturn;\n\t}"
new_info = "\tif ( cg.infoScreenText[0] != 0 ) {\n\t\tif ( hijackedDrawTraceCount < 64 ) CG_Printf( \"HIJACKED_CGAME_DRAW|return|reason=infoScreen\\n\" );\n\t\tCG_DrawInformation();\n\t\thijackedDrawTraceCount++;\n\t\treturn;\n\t}"
if source.count(old_info) != 1:
    raise SystemExit(f"expected one info-screen return, found {source.count(old_info)}")
source = source.replace(old_info, new_info, 1)

old_snap = "\tif ( !cg.snap || ( cg.snap->snapFlags & SNAPFLAG_NOT_ACTIVE ) ) {\n\t\tCG_DrawInformation();\n\t\treturn;\n\t}"
new_snap = "\tif ( !cg.snap || ( cg.snap->snapFlags & SNAPFLAG_NOT_ACTIVE ) ) {\n\t\tif ( hijackedDrawTraceCount < 64 ) CG_Printf( \"HIJACKED_CGAME_DRAW|return|reason=snapshot|snap=%p|flags=%d\\n\", (void *)cg.snap, cg.snap ? cg.snap->snapFlags : -1 );\n\t\tCG_DrawInformation();\n\t\thijackedDrawTraceCount++;\n\t\treturn;\n\t}"
if source.count(old_snap) != 1:
    raise SystemExit(f"expected one snapshot return, found {source.count(old_snap)}")
source = source.replace(old_snap, new_snap, 1)

old_draw = "\t// actually issue the rendering calls\n\tCG_DrawActive( stereoView );"
new_draw = "\t// actually issue the rendering calls\n\tif ( hijackedDrawTraceCount < 64 )\n\t\tCG_Printf( \"HIJACKED_CGAME_DRAW|beforeActive|clientFrame=%d|view=%dx%d|origin=%.1f,%.1f,%.1f\\n\", cg.clientFrame, cg.refdef.width, cg.refdef.height, cg.refdef.vieworg[0], cg.refdef.vieworg[1], cg.refdef.vieworg[2] );\n\tCG_DrawActive( stereoView );\n\tif ( hijackedDrawTraceCount < 64 ) {\n\t\tCG_Printf( \"HIJACKED_CGAME_DRAW|afterActive|clientFrame=%d\\n\", cg.clientFrame );\n\t\thijackedDrawTraceCount++;\n\t}"
if source.count(old_draw) != 1:
    raise SystemExit(f"expected one CG_DrawActive call, found {source.count(old_draw)}")
source = source.replace(old_draw, new_draw, 1)

path.write_text(source, encoding="utf-8")
print(f"instrumented {path}")
