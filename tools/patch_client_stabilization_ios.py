from __future__ import annotations

from pathlib import Path
import argparse


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f"{label}: expected exactly one patch point, found {count}")
    return text.replace(old, new, 1)


def patch(root: Path) -> None:
    sys_main = root / "Quake3/sys/sys_main.c"
    cl_main = root / "Quake3/client/cl_main.c"
    cl_cgame = root / "Quake3/client/cl_cgame.c"

    s = sys_main.read_text()
    s = replace_once(
        s,
        "static void HijackedEngineTrace(const char *message)",
        "void HijackedEngineTrace(const char *message)",
        "export trace helper",
    )
    sys_main.write_text(s)

    s = cl_main.read_text()
    s = replace_once(
        s,
        '#include "../sys/sys_loadlib.h"\n',
        '#include "../sys/sys_loadlib.h"\n\n#ifdef IOS\nextern void HijackedEngineTrace(const char *message);\n#endif\n',
        "cl_main trace declaration",
    )

    old = r'''void CL_StartHunkUsers( qboolean rendererOnly ) {
	if (!com_cl_running) {
		return;
	}

	if ( !com_cl_running->integer ) {
		return;
	}

	if ( !cls.rendererStarted ) {
		cls.rendererStarted = qtrue;
		CL_InitRenderer();
	}

	if ( rendererOnly ) {
		return;
	}

	if ( !cls.soundStarted ) {
		cls.soundStarted = qtrue;
		S_Init();
	}

	if ( !cls.soundRegistered ) {
		cls.soundRegistered = qtrue;
		S_BeginRegistration();
	}

	if( com_dedicated->integer ) {
		return;
	}

	if ( !cls.uiStarted ) {
		cls.uiStarted = qtrue;
		CL_InitUI();
	}
}'''

    new = r'''void CL_StartHunkUsers( qboolean rendererOnly ) {
#ifdef IOS
	HijackedEngineTrace("HIJACKED_CLIENT|StartHunkUsers:entered");
#endif
	if (!com_cl_running) {
#ifdef IOS
		HijackedEngineTrace("HIJACKED_CLIENT|StartHunkUsers:noComClient");
#endif
		return;
	}

	if ( !com_cl_running->integer ) {
#ifdef IOS
		HijackedEngineTrace("HIJACKED_CLIENT|StartHunkUsers:clientDisabled");
#endif
		return;
	}

	if ( !cls.rendererStarted ) {
#ifdef IOS
		HijackedEngineTrace("HIJACKED_CLIENT|Renderer:beforeInit");
#endif
		cls.rendererStarted = qtrue;
		CL_InitRenderer();
#ifdef IOS
		HijackedEngineTrace("HIJACKED_CLIENT|Renderer:afterInit");
#endif
	}

	if ( rendererOnly ) {
#ifdef IOS
		HijackedEngineTrace("HIJACKED_CLIENT|StartHunkUsers:rendererOnlyComplete");
#endif
		return;
	}

	if ( !cls.soundStarted ) {
#ifdef IOS
		HijackedEngineTrace("HIJACKED_CLIENT|Sound:beforeInit");
#endif
		cls.soundStarted = qtrue;
		S_Init();
#ifdef IOS
		HijackedEngineTrace("HIJACKED_CLIENT|Sound:afterInit");
#endif
	}

	if ( !cls.soundRegistered ) {
#ifdef IOS
		HijackedEngineTrace("HIJACKED_CLIENT|Sound:beforeRegistration");
#endif
		cls.soundRegistered = qtrue;
		S_BeginRegistration();
#ifdef IOS
		HijackedEngineTrace("HIJACKED_CLIENT|Sound:afterRegistration");
#endif
	}

	if( com_dedicated->integer ) {
#ifdef IOS
		HijackedEngineTrace("HIJACKED_CLIENT|StartHunkUsers:dedicatedComplete");
#endif
		return;
	}

	if ( !cls.uiStarted ) {
#ifdef IOS
		if ( Cvar_VariableIntegerValue("hijacked_direct") ) {
			HijackedEngineTrace("HIJACKED_CLIENT|UI:skippedDirectMap");
		} else
#endif
		{
#ifdef IOS
			HijackedEngineTrace("HIJACKED_CLIENT|UI:beforeInit");
#endif
			cls.uiStarted = qtrue;
			CL_InitUI();
#ifdef IOS
			HijackedEngineTrace("HIJACKED_CLIENT|UI:afterInit");
#endif
		}
	}
#ifdef IOS
	HijackedEngineTrace("HIJACKED_CLIENT|StartHunkUsers:complete");
#endif
}'''
    s = replace_once(s, old, new, "CL_StartHunkUsers stabilization")
    cl_main.write_text(s)

    s = cl_cgame.read_text()
    s = replace_once(
        s,
        '#include "../botlib/botlib.h"\n',
        '#include "../botlib/botlib.h"\n\n#ifdef IOS\nextern void HijackedEngineTrace(const char *message);\n#endif\n',
        "cl_cgame trace declaration",
    )
    s = replace_once(
        s,
        "\tt1 = Sys_Milliseconds();\n",
        '#ifdef IOS\n\tHijackedEngineTrace("HIJACKED_CGAME|Init:entered");\n#endif\n\tt1 = Sys_Milliseconds();\n',
        "cgame init entry",
    )
    s = replace_once(
        s,
        '\tcgvm = VM_Create( "cgame", CL_CgameSystemCalls, interpret );\n',
        '#ifdef IOS\n\tHijackedEngineTrace("HIJACKED_CGAME|VMCreate:before");\n#endif\n\tcgvm = VM_Create( "cgame", CL_CgameSystemCalls, interpret );\n#ifdef IOS\n\tHijackedEngineTrace(cgvm ? "HIJACKED_CGAME|VMCreate:after" : "HIJACKED_CGAME|VMCreate:failed");\n#endif\n',
        "cgame VM create trace",
    )
    s = replace_once(
        s,
        "\tVM_Call( cgvm, CG_INIT, clc.serverMessageSequence, clc.lastExecutedServerCommand, clc.clientNum );\n",
        '#ifdef IOS\n\tHijackedEngineTrace("HIJACKED_CGAME|CG_INIT:before");\n#endif\n\tVM_Call( cgvm, CG_INIT, clc.serverMessageSequence, clc.lastExecutedServerCommand, clc.clientNum );\n#ifdef IOS\n\tHijackedEngineTrace("HIJACKED_CGAME|CG_INIT:after");\n#endif\n',
        "cgame CG_INIT trace",
    )
    s = replace_once(
        s,
        "\tre.EndRegistration();\n\n\t// make sure everything is paged in\n\tif (!Sys_LowPhysicalMemory()) {\n\t\tCom_TouchMemory();\n\t}\n",
        '#ifdef IOS\n\tHijackedEngineTrace("HIJACKED_CGAME|EndRegistration:before");\n#endif\n\tre.EndRegistration();\n#ifdef IOS\n\tHijackedEngineTrace("HIJACKED_CGAME|EndRegistration:after");\n#endif\n\n\t// Avoid a launch-time full-hunk touch for the direct Hijacked iOS path.\n#ifdef IOS\n\tif ( Cvar_VariableIntegerValue("hijacked_direct") ) {\n\t\tHijackedEngineTrace("HIJACKED_CGAME|TouchMemory:skippedDirectMap");\n\t} else\n#endif\n\tif (!Sys_LowPhysicalMemory()) {\n#ifdef IOS\n\t\tHijackedEngineTrace("HIJACKED_CGAME|TouchMemory:before");\n#endif\n\t\tCom_TouchMemory();\n#ifdef IOS\n\t\tHijackedEngineTrace("HIJACKED_CGAME|TouchMemory:after");\n#endif\n\t}\n',
        "cgame end registration and memory stabilization",
    )
    s = replace_once(
        s,
        "\tCon_ClearNotify ();\n}",
        '\tCon_ClearNotify ();\n#ifdef IOS\n\tHijackedEngineTrace("HIJACKED_CGAME|Init:complete");\n#endif\n}',
        "cgame init completion",
    )
    cl_cgame.write_text(s)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    patch(args.root)
    print("client stabilization patch applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
