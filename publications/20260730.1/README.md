# Reviewed Stellar Distance Overrides

Release: `20260730.1`
Status: release candidate

This publication contains 48 reviewed distance replacements for stellar rows
whose automatic pipeline distance was unsuitable for a controlled Found in
Space build. It is an opt-in pipeline input, not a replacement for Gaia,
Hipparcos, or the pipeline's normal astrometry policy.

## Catalog

`catalog/distance_resolution_v1_resolved.yaml` is the executable override
catalog. Every entry:

- has `action: replace`;
- preserves a canonical Gaia or Hipparcos identity;
- supplies a reviewed distance and uncertainty with a row-level reference;
- preserves the selected astrometry, photometry, and temperature donors; and
- rebases absolute magnitude so the staged apparent brightness is unchanged at
  the reviewed distance.

The source tracker contains 81 reviewed candidates. Exactly 48 rows with
`status == resolved` are published. The remaining 33 provisional rows are
retained as evidence and are deliberately not executable overrides.

## Pipeline Use

Controlled projects must select this release explicitly:

```toml
[overrides]
output_parquet = "pipeline/overrides.parquet"
source_paths = [
  "/path/to/catalogs/publications/20260730.1/catalog/distance_resolution_v1_resolved.yaml",
]
```

The pipeline's packaged default override set remains empty. This publication
does not add the Sun or change Gaia–Hipparcos pairing policy.

## Provenance

The catalog is byte-for-byte identical to the release candidate produced by
public pipeline commit
`ffd569dd1e733c5bd39bb2dd6050763d98e06a43`. The deterministic build was
rechecked against the included tracker and four included preflight inputs.
`evidence/build_report.json` records the result; all input hashes are also
embedded in the catalog document.

The evidence files are intentionally the compact review/preflight inputs, not
full Gaia or Hipparcos source catalogs.

## Files

- `catalog/distance_resolution_v1_resolved.yaml` — executable 48-row override
  catalog.
- `evidence/distance-resolution-v1.csv` — 81-row review tracker.
- `evidence/external-distance-required.parquet` — reviewed candidate cohort.
- `evidence/current-pipeline-candidates.parquet` — pipeline candidate payload.
- `evidence/gaia-staged.parquet` and `evidence/hip-staged.parquet` — compact
  staged rows used to preserve donor values.
- `evidence/build_report.json` — deterministic rebuild and cross-check result.
- `evidence/input_provenance.json` — public code and input identities.
- `manifest.toml` — release scope, inputs, outputs, and counts.
- `REFERENCES.md`, `NOTICE.md`, and `LICENSE.txt` — attribution and use terms.
- `run_log.md` — assembly and validation record.
- `checksums.sha256` — complete publication checksum manifest.

## Validation

From a clean `catalogs` checkout:

```bash
UV_CACHE_DIR=.cache/uv uv sync --locked --all-groups
UV_CACHE_DIR=.cache/uv uv run pytest
sha256sum --check publications/20260730.1/checksums.sha256
```

The publication test verifies the 48/33 selection boundary, runtime pipeline
compatibility, exact evidence hashes, absence of a Sun row, and complete
checksum coverage.
