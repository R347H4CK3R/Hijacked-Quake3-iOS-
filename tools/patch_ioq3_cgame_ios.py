#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_ioq3_cgame_ios.py <ioq3-root>")

path = Path(sys.argv[1]) / "code/cgame/cg_players.c"
source = path.read_text()

old_fatal = 'CG_Error( "DEFAULT_MODEL (%s) failed to register", DEFAULT_MODEL );'
new_fatal = 'CG_Printf( "WARNING: DEFAULT_MODEL (%s) unavailable; continuing without player media\\n", DEFAULT_MODEL );'
if source.count(old_fatal) != 1:
    raise SystemExit(f"expected one DEFAULT_MODEL fatal path, found {source.count(old_fatal)}")
source = source.replace(old_fatal, new_fatal, 1)

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
new_sounds = '''\t// iOS Hijacked test build: optional player voice registration can stall
\t// during client initialization. Keep handles empty so map loading can proceed.
\tCG_Printf( "HIJACKED_CGAME|ClientSounds:skip|client=%d|model=%s\\n", clientNum, ci->modelName );
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
