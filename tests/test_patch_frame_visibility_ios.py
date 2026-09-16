from tools.patch_frame_visibility_ios import (
    patch_cl_cgame,
    patch_cl_main,
    patch_cl_scrn,
)


def test_cl_main_traces_cgame_time_and_screen_update_with_bounded_counter():
    source = '''
void CL_Frame ( int msec ) {
	CL_CheckForResend();

	// decide on the serverTime to render
	CL_SetCGameTime();

	// update the screen
	SCR_UpdateScreen();
}
'''
    patched = patch_cl_main(source)
    assert 'static int hijackedFrameTraceCount = 0;' in patched
    assert 'HIJACKED_FRAME|SetCGameTime:before' in patched
    assert 'HIJACKED_FRAME|SetCGameTime:after' in patched
    assert 'HIJACKED_FRAME|Screen:before' in patched
    assert 'HIJACKED_FRAME|Screen:after' in patched
    assert 'hijackedFrameTraceCount < 32' in patched
    assert 'hijackedFrameTraceCount++;' in patched


def test_cl_cgame_traces_active_frame_vm_call():
    source = '''
void CL_CGameRendering( stereoFrame_t stereo ) {
	VM_Call( cgvm, CG_DRAW_ACTIVE_FRAME, cl.serverTime, stereo, clc.demoplaying );
	VM_Debug( 0 );
}
'''
    patched = patch_cl_cgame(source)
    assert 'static int hijackedCGameFrameTraceCount = 0;' in patched
    assert 'HIJACKED_FRAME|CGameRender:before' in patched
    assert 'HIJACKED_FRAME|CGameRender:after' in patched
    assert 'hijackedCGameFrameTraceCount < 32' in patched
    assert 'hijackedCGameFrameTraceCount++;' in patched


def test_cl_scrn_traces_both_endframe_paths():
    source = '''
void SCR_UpdateScreen( void ) {
	if ( com_speeds->integer ) {
		re.EndFrame( &time_frontend, &time_backend );
	} else {
		re.EndFrame( NULL, NULL );
	}
}
'''
    patched = patch_cl_scrn(source)
    assert 'static int hijackedSwapTraceCount = 0;' in patched
    assert patched.count('HIJACKED_FRAME|EndFrame:before') == 2
    assert patched.count('HIJACKED_FRAME|EndFrame:after') == 2
    assert patched.count('hijackedSwapTraceCount++;') == 2
