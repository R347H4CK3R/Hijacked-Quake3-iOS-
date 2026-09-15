import importlib.util


def test_full_diagnostics_patcher_exists_and_covers_critical_boundaries():
    spec = importlib.util.find_spec("tools.patch_full_diagnostics_ios")
    assert spec is not None, "full diagnostics patcher is not implemented yet"

    from tools.patch_full_diagnostics_ios import (
        patch_common,
        patch_filesystem,
        patch_server,
        patch_world,
    )

    common = '''
void QDECL Com_Printf( const char *fmt, ... ) {
    va_list argptr;
    char msg[MAXPRINTMSG];
    va_start (argptr,fmt);
    Q_vsnprintf (msg, sizeof(msg), fmt, argptr);
    va_end (argptr);
}
void QDECL Com_Error( int code, const char *fmt, ... ) {
    va_list argptr;
    va_start (argptr,fmt);
    Q_vsnprintf (com_errorMessage, sizeof(com_errorMessage),fmt,argptr);
    va_end (argptr);
}
'''
    patched_common = patch_common(common)
    assert "HIJACKED_DIAG|Com_Error" in patched_common
    assert "HijackedLaunchTrace.txt" in patched_common

    filesystem = '''
long FS_FOpenFileRead(const char *filename, fileHandle_t *file, qboolean uniqueFILE)
{
    *file = 0;
    return -1;
}
'''
    patched_fs = patch_filesystem(filesystem)
    assert "HIJACKED_RESOLVE|request" in patched_fs
    assert "HIJACKED_RESOLVE|result" in patched_fs

    server = '''
void SV_SpawnServer( char *server, qboolean killBots ) {
    CL_MapLoading();
    CM_LoadMap( va("maps/%s.bsp", server), qfalse, &checksum );
    SV_InitGameProgs();
    sv.state = SS_GAME;
}
'''
    patched_server = patch_server(server)
    assert "HIJACKED_SERVER|SpawnServer:begin" in patched_server
    assert "HIJACKED_SERVER|CM_LoadMap:after" in patched_server
    assert "HIJACKED_SERVER|InitGameProgs:after" in patched_server
    assert "HIJACKED_SERVER|SpawnServer:ready" in patched_server

    world = '''
void RE_LoadWorldMap( const char *name ) {
    ri.FS_ReadFile( name, &buffer.v );
    header = (dheader_t *)buffer.b;
    R_LoadShaders( &header->lumps[LUMP_SHADERS] );
    R_LoadLightmaps( &header->lumps[LUMP_LIGHTMAPS] );
    R_LoadPlanes (&header->lumps[LUMP_PLANES]);
    R_LoadFogs( &header->lumps[LUMP_FOGS], &header->lumps[LUMP_BRUSHES], &header->lumps[LUMP_BRUSHSIDES] );
    R_LoadSurfaces( &header->lumps[LUMP_SURFACES], &header->lumps[LUMP_DRAWVERTS], &header->lumps[LUMP_DRAWINDEXES] );
    R_LoadMarksurfaces (&header->lumps[LUMP_LEAFSURFACES]);
    R_LoadNodesAndLeafs (&header->lumps[LUMP_NODES], &header->lumps[LUMP_LEAFS]);
    R_LoadSubmodels (&header->lumps[LUMP_MODELS]);
    R_LoadVisibility( &header->lumps[LUMP_VISIBILITY] );
    R_LoadEntities( &header->lumps[LUMP_ENTITIES] );
    R_LoadLightGrid( &header->lumps[LUMP_LIGHTGRID] );
    tr.world = &s_worldData;
}
'''
    patched_world = patch_world(world)
    assert "HIJACKED_WORLD|LoadWorld:begin" in patched_world
    assert "HIJACKED_WORLD|FS_ReadFile:after" in patched_world
    assert "HIJACKED_WORLD|Lump:surfaces:after" in patched_world
    assert "HIJACKED_WORLD|LoadWorld:complete" in patched_world
