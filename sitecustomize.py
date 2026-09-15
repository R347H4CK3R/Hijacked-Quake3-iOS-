from __future__ import annotations

import atexit
import sys
from pathlib import Path


def _patch_forced_hijacked_launch(sys_main: Path) -> None:
    if not sys_main.exists():
        return

    source = sys_main.read_text()
    old = '''\tNET_Init( );
#ifdef IOS
\tHijackedEngineTrace("Sys_Startup:afterNetInit");
#endif'''
    new = '''\tNET_Init( );
#ifdef IOS
\tHijackedEngineTrace("Sys_Startup:afterNetInit");
\tHijackedEngineTrace("HijackedMapLaunch:beforeQueue");
\tCbuf_AddText("map hijacked\\n");
\tCbuf_Execute();
\tHijackedEngineTrace("HijackedMapLaunch:afterExecute");
#endif'''

    if new in source:
        return
    if source.count(old) != 1:
        raise RuntimeError(
            f"expected exactly one post-NET_Init trace block, found {source.count(old)}"
        )

    sys_main.write_text(source.replace(old, new, 1))
    print("sitecustomize: forced Hijacked map launch applied")


def _apply_after_com_init_patch() -> None:
    if not sys.argv or not sys.argv[0].endswith("patch_com_init_ios.py"):
        return
    if len(sys.argv) < 2:
        return

    runtime_root = Path(sys.argv[1])

    def _run() -> None:
        files_c = runtime_root / "Quake3" / "qcommon" / "files.c"
        if files_c.exists():
            from tools.patch_fs_flight_recorder import patch_filesystem
            patch_filesystem(files_c)
            print("sitecustomize: filesystem flight recorder applied")

            from tools.patch_map_open_trace import patch_filesystem_reads
            patch_filesystem_reads(files_c)
            print("sitecustomize: Hijacked BSP/map-open trace applied")

        sys_main = runtime_root / "Quake3" / "sys" / "sys_main.c"
        _patch_forced_hijacked_launch(sys_main)

    atexit.register(_run)


_apply_after_com_init_patch()
