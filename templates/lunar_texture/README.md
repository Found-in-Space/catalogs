# @TITLE@

Release: `@RELEASE@`  
Series: `@SERIES@`  
Status: draft publication candidate; external payload is not yet published.

This is the first proposed release of an evolving series of lunar display
imagery derived from the LROC WAC global morphology mosaic distributed by USGS.
It provides opaque grayscale PNG tiles for interactive exploration and reuse,
with the exact source, coordinate definitions, processing history, and payload
checksums available alongside the imagery.

The payload has **@TILE_COUNT@ tiles and @TILE_BYTES@ bytes**. The producer
validated all PNGs and reconstructed every level raster exactly; preparation
also rehashed the source and every tile. These checks authenticate the existing
candidate. They do not establish an independently reproduced build or consumer
acceptance. The remaining requirements are recorded in
`evidence/publication_readiness.json` and `PUBLISHING.md`.

## Tile contract and interpretation

- Geographic longitude/latitude on a Moon sphere of radius 1,737,400 metres.
- Extent: longitude −180° to +180°, latitude −90° to +90°.
- XYZ: x increases eastward; y increases southward.
- One whole-body tile at zoom 0; square `2^z × 2^z` matrix at zoom z.
- Zooms 0–8; each tile is 512 × 512 pixels.
- Opaque, single-channel unsigned 8-bit grayscale PNG.
- Relative path: `imagery/{z}/{x}/{y}.png`.
- Missing coverage is opaque black. Black is not a transparency marker.

This is an equirectangular geographic matrix, not Web Mercator or the
two-column level-zero matrix used by some geographic tile servers.
Coordinates use planetocentric latitude and positive-east longitude.

| Zoom | Tiles | PNG bytes |
| --- | ---: | ---: |
@LEVEL_TABLE@

The input is approximately 100 m imagery. Resampling onto the zoom-8 grid
does not create finer observed detail. The square geographic matrix samples
latitude more densely than longitude; resolution varies with latitude.
These byte values are display samples, not a calibrated reflectance product.
No elevation, topography, colour imagery, uncertainty map, or scientific
height encoding is included.

The producer uses bilinear reprojection for the maximum level and derives
each lower level directly from that base using area averaging. Tile emission
copies aligned windows without another resampling or per-tile stretch.
The original band scale/offset are recorded in source inspection; the commands
operate on encoded bytes and do not apply an explicit unscale operation.
Viewer tone adjustment is a downstream presentation choice and is not baked
into this payload.

## Files and authentication

- `manifest.toml`: release identity, per-level counts, code history, and planned hosting.
- `payload/product.json`: byte-for-byte producer product metadata.
- `payload/manifests/`: byte-for-byte per-level tile SHA-256 manifests.
- `evidence/`: source inspection, acquisition receipt, stage states, logs,
  portable-export inventory, preparation verification, and readiness assessment.
- `reproduction/`: original project, source and CRS definitions, and software
  dependency files extracted from the recorded Git objects.
- `run_log.md`, `LICENSE.txt`, `NOTICE.md`, `REFERENCES.md`, and `PUBLISHING.md`:
  processing, rights, scientific attribution, and publication instructions.
- `zenodo/draft-metadata.md`: initial deposit metadata and future version policy.
- `checksums.sha256`: all metadata-deposit files except itself and future DOI tracking.

The tile payload and raw GeoTIFF are outside Git and the proposed metadata
deposit. This deposit authenticates the externally hosted product through
`payload/product.json` and the tile manifests. The full product identity is
`@IDENTITY@`.

From this directory, verify the metadata with `sha256sum --check checksums.sha256`.
From a downloaded tile root, verify each `payload/manifests/tiles-z*.sha256`
using `sha256sum --check` with that root as the working directory.

## Hosting and citation

The planned prefix is `@PREFIX@` in S3 bucket `foundinspace`, served through
`data.foundin.space`. These are intended locations, not verified download links.
Keep their status provisional until a generated upload receipt confirms the
objects and HTTP delivery metadata.

The initial Zenodo deposit starts one version lineage for `@SERIES@`.
Later substantive changes use **New version** in that lineage. Cite the
release-specific Version DOI for exact reproducibility and the Concept DOI
when referring to the series. No DOI is reserved or assigned in this candidate.
Credit the upstream LROC Team, Arizona State University, NASA, and USGS as
described in `NOTICE.md` and `REFERENCES.md`.
