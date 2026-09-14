# Hijacked → Quake 3 iOS Design

## Goal
Build an isolated, native ARM64 iOS application based on Quake3-iOS that loads a converted version of the Call of Duty: Black Ops II PS3 multiplayer map Hijacked and can be sideloaded into LiveContainer without using a Windows/PS3 emulator.

## Source Assets
The input archive is `Hijacked.zip` from the user's Google Drive. Verified payload:
- `mp_hijacked.ff` — 28,642,816 bytes, PS3/T6 fastfile, magic `TAff0100`.
- `mp_hijacked.ipak` — 90,963,968 bytes, IPAK image container, magic `IPAK`.
- `mpl_hijacked.all.sabs` — 3,262,464 bytes, BO2 sound bank.
- macOS metadata entries are ignored.

## Project Isolation
This repository is independent from every other user project. No code, assets, manifests, Git history, build outputs, workflow state, or dependencies are copied from BO2-Native-iOS, Zombies-IOS, NativeZombies-IOS, DukeX, or any other project unless the user explicitly changes this requirement.

## Runtime
Use `tomkidd/Quake3-iOS` as the native iOS runtime base. The finished app must run ARM64 code directly on iOS. Quake 3 is used as the renderer/game runtime; it is not an emulator.

## Conversion Architecture
1. `tools/t6ps3/` parses PS3 T6 containers and exposes typed metadata without assuming PC byte order/layout.
2. `tools/intermediate/` normalizes decoded geometry, materials, images, entities, collision, spawn data, and optional audio references into a deterministic JSON + binary intermediate representation.
3. `tools/q3export/` emits Quake 3-compatible assets: BSP/map geometry inputs, shaders, textures, entities, collision, and PK3 layout.
4. `runtime/` contains the Quake3-iOS integration layer and startup configuration that launches Hijacked directly.
5. GitHub Actions builds the unsigned ARM64 IPA and stores it as an artifact.

## Decoder Rules
- Detect and preserve source endianness explicitly.
- Every parser must bounds-check offsets and sizes before reading.
- Unknown structures are recorded, not silently skipped.
- No fabricated geometry, texture, entity, or collision data may be labeled as decoded Hijacked content.
- Conversion must be deterministic from the same input files.
- Reverse-engineering probes must produce machine-readable reports committed only when they contain no copyrighted source payload.

## Quake 3 Map Representation
The exporter targets an id Tech 3 BSP/PK3 representation. Static map surfaces become Quake 3 world geometry or static models depending on source semantics. Material references become Quake 3 shader definitions. Collision is emitted as clip/solid geometry. Spawn points are translated to Quake 3 player spawn entities. Unsupported BO2 gameplay entities are either mapped to a documented Quake 3 equivalent or excluded with a conversion warning.

## Textures
IPAK decoding is handled separately from the fastfile. Images are exported into a Quake 3-supported texture format. Material-to-image references are preserved through stable asset IDs. Missing or undecoded textures must be reported and must not be silently replaced in the final playable milestone.

## Audio
Audio is non-blocking for the first playable milestone. `mpl_hijacked.all.sabs` is inventoried and may be converted later. The initial playable definition does not require BO2 ambient audio if geometry, textures, collision, spawning, movement, and rendering are correct.

## iOS Integration
- Target: ARM64 iPhone/iOS build.
- Touch controls remain enabled using the Quake3-iOS control path.
- The app launches into a Hijacked map-loading flow without requiring desktop files.
- Converted map assets are bundled with the application or staged into the Quake 3 base directory during packaging.
- The produced IPA is unsigned so the user can sign/install it with their existing sideload/LiveContainer workflow.

## Build Pipeline
GitHub Actions runs on macOS, installs/builds required open-source tools, builds the native iOS target, packages `Payload/<App>.app`, and uploads an IPA artifact. The workflow must fail if required converted assets are missing.

## Verification
The project is not called playable merely because CI succeeds. Playable requires all of the following:
- native ARM64 IPA is produced;
- app launches without immediate crash;
- Hijacked loads as recognizable map geometry;
- Hijacked textures render rather than placeholder-only output;
- player can spawn and move;
- world collision prevents walking through primary floors/walls;
- no emulator is involved.

Automated verification includes parser tests, deterministic conversion checks, PK3/BSP sanity checks, Xcode build success, packaged IPA structure checks, and runtime asset-presence checks. Device-level behavior that cannot be simulated faithfully is explicitly separated from build verification.

## Failure Handling
Parser failures include byte offset, structure name, expected range, and actual file size. Conversion reports list decoded, skipped, and unresolved assets. CI logs preserve enough information to reproduce failures without exposing the original copyrighted BO2 files in the public repository.

## Source Asset Policy
The public repository does not commit `Hijacked.zip`, BO2 fastfiles, IPAKs, SABS files, or extracted copyrighted source assets. Conversion tooling and metadata/report outputs are safe to commit. CI that requires source assets must obtain them from a user-controlled private source or run conversion before public build packaging.
