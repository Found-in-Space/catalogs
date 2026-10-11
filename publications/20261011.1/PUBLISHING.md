# Publication and reproduction procedure

Release: `20261011.1`

This candidate is deliberately marked `draft`. Its generated readiness report
lists the remaining requirements. Completing metadata preparation does not
publish the tile payload or start a Zenodo DOI lineage.

## Before finalizing the payload

1. Make every producer commit enumerated in `manifest.toml` publicly retrievable
   and verify its exact SHA. Preserve the historical acquisition, raster-build,
   and tile-emission revisions rather than attributing all stages to the last one.
2. Preserve the source, project, public code, and matching uv lockfiles; record
   Python and GDAL/PROJ versions. Document representative source reprojection,
   geometry, pyramid, and visual checks. These are display textures: identical
   regenerated pixels or PNG bytes, a hermetic system image, and a full pyramid
   rebuild are not publication requirements.
3. Confirm the upstream product's image reuse terms from a primary source and
   record them in the licence, notice, manifest, and Zenodo metadata.
4. Record consumer acceptance at poles, the antimeridian, tile boundaries, and
   zoom transitions, including the target headset when relevant.

If a replay changes product identity, even when the images look similar, use
the new producer-generated identity and a new immutable prefix. Do not hand-edit
the recorded product or validation reports to make this candidate look complete.

## Historical stage recipe

The following is a replay recipe derived from recorded stages, not a claim
that a replay has occurred. Allocate distinct source, work, output, and
evidence roots with sufficient disk space. The existing state files preserve
exact GDAL arguments and run timings; `${RUN_ROOT}` and `${PRODUCER_ROOT}` in
exported JSON denote replaceable machine roots, not project-file environment
expansion.

Use a clean checkout of the publicly available producer at each recorded SHA,
its corresponding `uv.lock`, and `UV_CACHE_DIR=.cache/uv uv sync --frozen
--no-editable`. Record the external GDAL/PROJ versions and interpreter used for
any new checks; unknown historical interpreter details remain disclosed.

- Acquisition: commit `1f657ce91eb795b2af7ec6169bdb2a61637605ac`, command
  `download` with that revision's source specification and `--source-root`.
- Admission/raster construction: commit `56fd7a789cf31eea613d2f770a1042846090d587`, commands
  `inspect-source`, `preflight`, `build-base`, and `build-levels`.
  The recorded maximum-level build uses `--threads 4 --warp-memory-mb 1024`.
- Emission/validation: commit `deca93d4872bbbb3c75ccfa4083c9e865f331d86`, commands `preflight`,
  `emit-tiles`, and `validate-tiles` using the same run roots.

Run producer entrypoints as `UV_CACHE_DIR=.cache/uv uv run
pas-de-geant-textures <command>`. Preserve the resulting project, source
receipt, source inspection, lockfiles, software provenance, stage states,
pixel validation, and per-tile manifests. Published-file checksums protect
payload identity and transfer integrity; a fresh build need not match them.

Representative checks can be recorded using the public catalogs script:

```bash
uv run --frozen --no-editable scripts/check_lunar_samples.py \
  --run-root /path/to/controlled-run \
  --producer-root /path/to/clean-public-producer \
  --scratch-root /path/to/new-sample-work \
  --report /path/to/representative_checks.json
```

Pass that generated report to the assembler with `--sample-report`.

## Immutable S3 and CDN payload

The intended prefix is `textures/moon/lroc-wac-global-100m/20261011.1/` in bucket `foundinspace`.
Upload the exact tile tree, producer `product.json`, and per-level manifests.
Keep raw source images, intermediate rasters, temporary files, credentials,
and local environment files outside the public object tree.

Use a manifest-driven, restartable uploader that refuses conflicting existing
objects. Set PNG content type to `image/png`; set immutable object caching to
`public, max-age=31536000, immutable`. Metadata objects need their own correct
content types. Verify remote object counts, byte sizes and SHA-256 identities;
do not assume multipart ETags are SHA-256 checksums.

Generate and retain an upload receipt with bucket, prefix, product identity,
object checksums, upload completion, and S3/CDN header verification. Check CORS
and representative full-image responses through `data.foundin.space`, then
switch the viewer to the exact immutable template. Planned URLs become public
download links only after this verification succeeds.

## Zenodo lineage and final deposit

1. Start one initial record for `fis.textures.moon.lroc-wac-global-morphology-100m`; later releases use **New version**
   in that record lineage. Reserve the initial Version DOI before final packaging.
2. Confirm creator, licence scope, actual publication date, description,
   externally hosted payload links, and source attribution using
   `zenodo/draft-metadata.md`. This proposed deposit contains publication metadata
   and authentication manifests; its PNG tiles remain externally hosted.
3. Regenerate readiness metadata and checksums after all completed gates have
   generated supporting evidence. Commit the exact release to public `catalogs`.
4. From a clean checkout of that public commit, verify `checksums.sha256`,
   build a path-preserving archive outside this release directory, and record
   its SHA-256. Check its contents before upload and publication.
5. After publication, record Version DOI, Concept DOI, record IDs, public
   release commit, archive checksum, and URLs in `zenodo/published-record.toml`.
   Exclude that later tracking file from the deposited payload and checksums.

No reserved DOI, verified hosting receipt, consumer-acceptance record, or
completed independent replay is fabricated in this candidate.
