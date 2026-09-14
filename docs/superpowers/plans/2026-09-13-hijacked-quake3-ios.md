# Hijacked Quake 3 iOS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a native ARM64 Quake3-iOS app that packages a converted PS3 BO2 Hijacked map and produces an unsigned IPA suitable for sideloading/LiveContainer.

**Architecture:** Parse PS3 T6 container metadata into a deterministic intermediate representation, export Quake 3-compatible map assets, integrate them with Quake3-iOS, and package the result through GitHub Actions. Source BO2 files remain outside the public repository.

**Tech Stack:** Python 3.11+, pytest, binary struct parsing, id Tech 3 BSP/PK3 formats, Objective-C/C/C++, Xcode/iOS toolchain, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-13-hijacked-quake3-ios-design.md`

## Global Constraints
- Keep this repository completely independent from the user's other projects.
- Native ARM64 iOS only; no Windows/PS3 emulator.
- Do not commit BO2 source archives or extracted copyrighted assets.
- Treat `TAff0100`, `IPAK`, and SABS inputs as PS3/T6 data; do not assume PC layouts.
- Bounds-check every binary read.
- Do not label placeholder geometry/textures as decoded Hijacked content.
- An IPA is only "playable" after recognizable map geometry, textures, spawning, movement, and primary collision work.

---

### Task 1: Repository foundation and source inspector

**Files:**
- Create: `.gitignore`
- Create: `pyproject.toml`
- Create: `tools/t6ps3/__init__.py`
- Create: `tools/t6ps3/inspect.py`
- Create: `tests/test_inspect.py`

**Interfaces:**
- Produces `inspect_file(path: Path) -> dict[str, object]`.
- Recognizes fastfile, IPAK, SABS, unknown.

- [ ] Write tests using synthetic byte strings for each magic and truncated inputs.
- [ ] Run `python -m pytest tests/test_inspect.py -v` and verify failures before implementation.
- [ ] Implement `inspect_file` with file size, SHA-256, magic, kind, and bounded header preview.
- [ ] Run tests and verify PASS.
- [ ] Commit `feat: add PS3 T6 source inspector`.

### Task 2: Fastfile header parser

**Files:**
- Create: `tools/t6ps3/fastfile.py`
- Create: `tests/test_fastfile.py`

**Interfaces:**
- Produces `parse_fastfile_header(data: bytes) -> FastFileHeader`.
- `FastFileHeader` exposes magic, platform/build marker bytes, map name, and validated raw header fields.

- [ ] Add fixtures reproducing the verified `TAff0100` header pattern without storing original payload.
- [ ] Verify the tests fail.
- [ ] Implement explicit big-endian-safe header parsing with range checks.
- [ ] Verify malformed/truncated headers raise typed `ParseError` containing byte offset.
- [ ] Run tests and commit `feat: parse PS3 T6 fastfile header`.

### Task 3: IPAK directory parser

**Files:**
- Create: `tools/t6ps3/ipak.py`
- Create: `tests/test_ipak.py`

**Interfaces:**
- Produces `parse_ipak_header(data: bytes) -> IpakHeader` and `parse_ipak_segments(path: Path) -> list[IpakSegment]`.

- [ ] Encode the verified `IPAK` v5 header shape as a synthetic test fixture.
- [ ] Test segment bounds, overlap rejection, count limits, and truncated table handling.
- [ ] Implement header/table decoding without texture decompression yet.
- [ ] Run tests and commit `feat: parse IPAK segment directory`.

### Task 4: SABS inventory parser

**Files:**
- Create: `tools/t6ps3/sabs.py`
- Create: `tests/test_sabs.py`

**Interfaces:**
- Produces `inventory_sabs(path: Path) -> SabsInventory`.

- [ ] Add tests for the observed SABS magic/header and malformed sizes.
- [ ] Implement a conservative bank inventory that records unknown fields instead of guessing codecs.
- [ ] Run tests and commit `feat: inventory BO2 SABS bank`.

### Task 5: Deterministic intermediate map model

**Files:**
- Create: `tools/intermediate/model.py`
- Create: `tools/intermediate/io.py`
- Create: `tests/test_intermediate.py`

**Interfaces:**
- Defines `MapAssetSet`, `Surface`, `Material`, `ImageRef`, `CollisionBrush`, `SpawnPoint`, and `UnresolvedAsset`.
- Produces/consumes canonical JSON metadata plus external binary blobs by SHA-256.

- [ ] Write canonical serialization tests that verify stable ordering and hashes.
- [ ] Implement dataclasses and canonical JSON output.
- [ ] Add unresolved-asset recording and validation.
- [ ] Run tests and commit `feat: add deterministic map intermediate model`.

### Task 6: PS3 T6 world/material extraction probes

**Files:**
- Create: `tools/t6ps3/probe_fastfile.py`
- Create: `tools/t6ps3/report.py`
- Create: `tests/test_probe.py`

**Interfaces:**
- Produces machine-readable reports describing candidate zones, strings, asset tables, offsets, endian interpretation, and unresolved structures.

- [ ] Implement safe scanning primitives with alignment/range validation.
- [ ] Add tests that reject out-of-range candidate pointers and false positives.
- [ ] Run probes against the locally retrieved `mp_hijacked.ff` without committing source bytes.
- [ ] Refine parser based on reproducible structure evidence.
- [ ] Commit only tooling and non-copyrighted metadata summaries.

### Task 7: Quake 3 exporter and PK3 validator

**Files:**
- Create: `tools/q3export/map_writer.py`
- Create: `tools/q3export/shader_writer.py`
- Create: `tools/q3export/pk3.py`
- Create: `tests/test_q3export.py`

**Interfaces:**
- `export_map(asset_set: MapAssetSet, out_dir: Path) -> ExportReport`.
- `build_pk3(source_dir: Path, output: Path) -> None`.
- `validate_pk3(path: Path) -> ValidationReport`.

- [ ] Add tests for entities, spawn mappings, collision brushes, shader names, deterministic ZIP ordering, and path traversal rejection.
- [ ] Implement minimal valid map/shader/PK3 output.
- [ ] Add validation that fails when required Hijacked assets are unresolved.
- [ ] Commit `feat: add Quake 3 Hijacked exporter`.

### Task 8: Quake3-iOS runtime integration

**Files:**
- Add upstream Quake3-iOS source under `runtime/quake3-ios/` with provenance documented.
- Create: `runtime/HijackedConfig.cfg`
- Modify iOS project resources/build settings as required.
- Create: `runtime/README.md`

**Interfaces:**
- App launches Quake 3 with bundled Hijacked PK3 available and executes the Hijacked startup config.

- [ ] Import the upstream native iOS runtime without linking to other user repos.
- [ ] Preserve touch controls and ARM64 target.
- [ ] Add startup config and bundle resource path.
- [ ] Build on macOS runner/simulator-compatible target where possible.
- [ ] Commit `feat: integrate Hijacked with Quake3-iOS runtime`.

### Task 9: Unsigned IPA GitHub Actions pipeline

**Files:**
- Create: `.github/workflows/build-ios.yml`
- Create: `scripts/package_ipa.sh`
- Create: `scripts/verify_ipa.py`
- Create: `tests/test_verify_ipa.py`

**Interfaces:**
- Workflow artifact contains `Hijacked-Quake3-iOS.ipa`.

- [ ] Test IPA verifier against synthetic valid/invalid Payload trees.
- [ ] Implement unsigned archive build and packaging.
- [ ] Fail workflow when required app executable/resources are absent.
- [ ] Upload IPA and conversion/build reports.
- [ ] Commit `ci: build unsigned Hijacked iOS IPA`.

### Task 10: Playability gate and release candidate

**Files:**
- Create: `PLAYABILITY.md`
- Create: `scripts/playability_gate.py`
- Update: `README.md`

**Interfaces:**
- `playability_gate.py` consumes build/conversion reports and exits nonzero unless all automatable playable criteria pass.

- [ ] Check native ARM64 Mach-O architecture, IPA structure, Hijacked PK3/BSP presence, non-placeholder texture inventory, spawn entities, and collision counts.
- [ ] Run parser/export/unit tests and iOS build verification.
- [ ] Produce release-candidate IPA artifact only when the gate passes.
- [ ] Record any device-only LiveContainer validation separately and never infer it from CI.
- [ ] Commit `release: prepare playable Hijacked iOS candidate`.

## Self-review
All spec requirements map to Tasks 1–10. No source BO2 assets are committed. Parser safety, deterministic conversion, Quake 3 export, native runtime integration, IPA packaging, and playability verification each have an explicit task and test surface.
