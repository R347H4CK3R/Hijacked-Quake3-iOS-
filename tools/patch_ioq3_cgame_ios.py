#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_ioq3_cgame_ios.py <ioq3-root>")

path = Path(sys.argv[1]) / "code/cgame/cg_players.c"
source = path.read_text()

replacements = []

# Never abort the cgame because optional/default player media is incomplete.
replacements.append((
    'CG_Error( "DEFAULT_MODEL (%s) failed to register", DEFAULT_MODEL );',
    'CG_Printf( "HIJACKED_CGAME|DefaultModel:unavailable|%s\\n", DEFAULT_MODEL );'
))
replacements.append((
    'CG_Error( "DEFAULT_TEAM_MODEL / skin (%s/%s) failed to register", DEFAULT_TEAM_MODEL, ci->skinName );',
    'CG_Printf( "HIJACKED_CGAME|DefaultTeamModel:unavailable|%s/%s\\n", DEFAULT_TEAM_MODEL, ci->skinName );'
))
replacements.append((
    'CG_Error( "CG_RegisterClientModelname( %s, %s, %s, %s %s ) failed", ci->modelName, ci->skinName, ci->headModelName, ci->headSkinName, teamname );',
    'CG_Printf( "HIJACKED_CGAME|RequestedModel:unavailable|%s/%s\\n", ci->modelName, ci->skinName );'
))

# Player icons are UI-only. The device trace currently stops in the Sarge
# icon lookup/registration path, so do not enter renderer shader registration
# for model icons at all. Gameplay models, skins and animations still register.
icon_block = '''\tif ( CG_FindClientHeadFile( filename, sizeof(filename), ci, teamName, headName, headSkinName, "icon", "skin" ) ) {
\t\tci->modelIcon = trap_R_RegisterShaderNoMip( filename );
\t}
\telse if ( CG_FindClientHeadFile( filename, sizeof(filename), ci, teamName, headName, headSkinName, "icon", "tga" ) ) {
\t\tci->modelIcon = trap_R_RegisterShaderNoMip( filename );
\t}
'''
icon_skip = '''\tci->modelIcon = 0;
\tCG_Printf( "HIJACKED_CGAME|ModelIcon:skip|model=%s|skin=%s\\n", modelName, skinName );
'''
if source.count(icon_block) != 1:
    raise SystemExit(f"expected one player icon registration block, found {source.count(icon_block)}")
source = source.replace(icon_block, icon_skip, 1)

# Missing icons must never fail client registration.
replacements.append((
    '''\tif ( !ci->modelIcon ) {
\t\treturn qfalse;
\t}

\treturn qtrue;''',
    '''\tif ( !ci->modelIcon ) {
\t\tCG_Printf( "HIJACKED_CGAME|ModelIcon:missing|model=%s|skin=%s\\n", modelName, skinName );
\t}

\treturn qtrue;'''
))

for old, new in replacements:
    if source.count(old) != 1:
        raise SystemExit(f"expected one patch point, found {source.count(old)} for: {old[:80]!r}")
    source = source.replace(old, new, 1)

# Optional player voice registration is not required for map bring-up.
old_sounds = '''\t// sounds
\tdir = ci->modelName;
\tfallback = (cgs.gametype >= GT_TEAM) ? DEFAULT_TEAM_MODEL : DEFAULT_MODEL;

\tfor ( i = 0 ; i < MAX_CUSTOM_SOUNDS ; i++ ) {
\t\ts = cg_customSoundNames[i];
\t\tif ( !s ) {
\t\t\tbreak;
\t\t}
\t\tci->sounds[i] = 0;
\t\t// if the model didn't load use the sounds of the default model
\t\tif (modelloaded) {
\t\t\tci->sounds[i] = trap_S_RegisterSound( va("sound/player/%s/%s", dir, s + 1), qfalse );
\t\t}
\t\tif ( !ci->sounds[i] ) {
\t\t\tci->sounds[i] = trap_S_RegisterSound( va("sound/player/%s/%s", fallback, s + 1), qfalse );
\t\t}
\t}
'''
new_sounds = '''\tCG_Printf( "HIJACKED_CGAME|ClientSounds:skip|client=%d|model=%s\\n", clientNum, ci->modelName );
\tfor ( i = 0 ; i < MAX_CUSTOM_SOUNDS ; i++ ) {
\t\tci->sounds[i] = 0;
\t}
\tCG_Printf( "HIJACKED_CGAME|ClientSounds:complete|client=%d\\n", clientNum );
'''
if source.count(old_sounds) != 1:
    raise SystemExit(f"expected one player sound registration block, found {source.count(old_sounds)}")
source = source.replace(old_sounds, new_sounds, 1)

path.write_text(source)
print(f"patched {path}")
