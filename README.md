# Hijacked-Quake3-iOS

An iOS port project that runs the **Hijacked** map through a Quake 3-derived runtime, packaged as an unsigned IPA for sideloading on supported iOS devices.

## Project overview

This repository combines a native iOS Quake 3 runtime with project-specific patches, configuration, QVMs, runtime assets, and the converted Hijacked BSP needed to launch the map on iPhone.

The current build pipeline is designed to:

- build the native arm64 iOS application;
- apply the Hijacked runtime patches;
- stage the required Quake 3/OpenArena-compatible runtime assets;
- inject the Hijacked BSP and QVMs into `baseq3`;
- package the finished app as an unsigned IPA;
- verify that the IPA contains the expected map, VM, executable, and runtime files before publishing the artifact.

## Build pipeline

GitHub Actions performs the automated build using:

- a pinned Quake3-iOS runtime revision;
- project runtime patches and configuration;
- the Hijacked BSP;
- `qagame.qvm`, `cgame.qvm`, and `ui.qvm`;
- redistributable OpenArena-compatible runtime resources required by the map/runtime.

The primary workflow is:

`.github/workflows/build-stabilized-ipa-v2.yml`

The expected output artifact is:

`Hijacked-Quake3-iOS-stabilized-v2-unsigned.ipa`

## Installation

The generated IPA is unsigned. It must be signed or loaded with a compatible sideloading/runtime solution before use on an iPhone.

This project is being tested with an iPhone-focused sideloading workflow and does not require the user to build the app manually in Xcode when using the provided GitHub Actions pipeline.

## Runtime layout

Important packaged files include:

```text
Payload/Quake3-iOS.app/
└── baseq3/
    ├── maps/hijacked.bsp
    ├── vm/qagame.qvm
    ├── vm/cgame.qvm
    ├── vm/ui.qvm
    ├── hijacked.cfg
    └── runtime assets
```

The CI verification stage checks representative runtime files and validates the IPA archive before it is uploaded as a workflow artifact.

## Current status

The native arm64 iOS application build is functional in CI. The remaining stabilization work is focused on making runtime-asset staging reproducible and ensuring the final packaged IPA consistently contains every dependency required to load and render Hijacked correctly.

## Legal / asset notice

This repository does not grant rights to proprietary game content. Only use proprietary assets that you lawfully possess and are authorized to use.

Redistributable third-party runtime assets remain subject to their respective licenses. OpenArena-derived content included by the build process must retain the applicable license and attribution files.