# Hijacked Quake 3 iOS

An isolated iOS runtime project for launching a converted **Hijacked** map through a Quake 3-derived engine. The project is built as an unsigned arm64 IPA for sideloading and is intentionally kept independent from the user's other game-conversion projects.

## Current status

The device build now progresses through the full Quake 3 common initialization path and reaches the engine frame loop on iPhone under LiveContainer. The latest device trace confirmed:

- UIKit window and `GameViewController` initialization complete.
- `Sys_Startup` enters successfully.
- `Com_Init` completes.
- Filesystem initialization completes and finds bundled `baseq3` resources.
- Client/server/VM initialization completes.
- Networking initialization completes.
- The engine reaches its first `Com_Frame`.

The remaining device work is therefore after core startup: map/renderer/client-frame initialization rather than the earlier `Com_Init` / filesystem hang.

## LiveContainer path handling

LiveContainer virtualizes application storage, so the writable Documents path may appear nested inside LiveContainer's own container, for example:

```text
.../Documents/Data/Application/<UUID>/Documents
```

That shape is expected under LiveContainer and should not be treated as a malformed path by itself.

The runtime now explicitly supplies:

- `fs_basepath` -> the installed `.app` resource path
- `fs_apppath` -> the installed `.app` resource path
- `fs_homepath` -> the app's writable Documents directory
- `logfile 2` -> persistent Quake console logging for post-startup diagnosis
- `com_standalone 1` -> standalone runtime behavior

This prevents implicit path discovery from selecting a different app or host-container location.

## Direct Hijacked launch

Hijacked is launched with `+map hijacked` directly.

The previous launch patch forced `botMatch = true` even though the packaged configuration sets `bot_enable 0`. That mismatch has been removed. The app now keeps bot mode disabled and still launches Hijacked as a normal multiplayer map, avoiding a dependency on single-player arena metadata and `+spmap`.

## Diagnostics

`HijackedLaunchTrace.txt` records native startup breadcrumbs. The current instrumentation includes boundaries for:

```text
Sys_Startup:beforeComInit
Sys_Startup:afterComInit
Sys_Startup:afterNetInit
Sys_Startup:firstFrame:before
Sys_Startup:firstFrame:after
```

Filesystem initialization is also traced around `FS_InitFilesystem`, `FS_Startup`, game-directory registration, and script enumeration.

With `logfile 2` enabled, Quake's console log should also be written under the writable game directory and can be used to diagnose renderer, BSP, shader, QVM, or client-map errors that occur after the first frame begins.

## Build pipeline

The `Unsigned iPhone IPA` GitHub Actions workflow:

1. Runs regression tests for the iOS startup patcher.
2. Builds the standalone GPL baseq3 QVMs from a pinned ioquake3 revision.
3. Fetches the pinned Quake3-iOS runtime.
4. Applies the deterministic iOS/LiveContainer startup patches.
5. Verifies the expected path, map-launch, standalone, and trace markers.
6. Builds an unsigned arm64 iPhone application.
7. Injects the QVMs and verified Hijacked BSP into `baseq3`.
8. Packages and validates `Hijacked-Quake3-iOS-unsigned.ipa`.

The build artifact is named:

```text
Hijacked-Quake3-iOS-unsigned-IPA
```

## Important limitation

A successful IPA build proves that the native runtime, QVMs, bundle layout, BSP validation, and packaging stages succeeded. It does **not** by itself prove that the converted Hijacked content renders correctly on a physical iPhone. Device traces and Quake console logging remain the authoritative evidence for the remaining runtime issues.
