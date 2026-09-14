from __future__ import annotations

import atexit
import sys
from pathlib import Path


def _apply_after_com_init_patch() -> None:
    if not sys.argv or not sys.argv[0].endswith("patch_com_init_ios.py"):
        return
    if len(sys.argv) < 2:
        return

    runtime_root = Path(sys.argv[1])

    def _run() -> None:
        files_c = runtime_root / "Quake3" / "qcommon" / "files.c"
        if not files_c.exists():
            return
        from tools.patch_fs_flight_recorder import patch_filesystem
        patch_filesystem(files_c)
        print("sitecustomize: filesystem flight recorder applied")

    atexit.register(_run)


_apply_after_com_init_patch()
