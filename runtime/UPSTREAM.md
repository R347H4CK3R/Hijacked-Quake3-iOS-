# Native runtime provenance

This project uses `tomkidd/Quake3-iOS` as the native iOS Quake 3 runtime base.

- Repository: `https://github.com/tomkidd/Quake3-iOS`
- Pinned commit: `f4b38931a765315fa4c7201dfbed2dd4a9b2d65c`
- Upstream target: `Quake3-iOS`
- Runtime lineage: Beben III / ioquake3

The upstream source is fetched at build time rather than copied into this repository. This keeps the Hijacked project independent and makes the exact upstream revision reproducible.

No Quake III retail `baseq3` data and no BO2 source assets are committed here.
