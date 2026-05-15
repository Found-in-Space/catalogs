# Repository Layout

This repo is a catalogue/data-product repository. It deliberately separates
curated input catalogues, audit evidence, and build records.

```text
overrides/
  v0.1.0/
    manifest.toml
    yaml/
      *.yaml
    tables/
      overrides.parquet
      overrides.csv

crossmatches/
  gaia-hip/
    v0.1.0/
      manifest.toml
      supplemental_gaia_hip.parquet
      supplemental_gaia_hip.csv

evidence/
  gaia-hip/
    v0.1.0/
      manifest.toml
      match_evidence.parquet
      audit_match_report.json
      distance_pct_histogram.png
      distance_pct_vs_astrometry_quality.png

builds/
  <build_id>/
    README.md
    build.lock.toml
    config/
      pipeline.project.toml
      octree.project.toml
    postbuild/
      counts.json
      artifacts.json
      checksums.sha256

schemas/
  <schema_name>/
    v1.json

templates/
  ...
```

## Top-Level Directories

`overrides/` contains the curated override catalogue. Overrides are source data:
they represent our published judgement about specific stellar records.

`crossmatches/` contains curated supplemental identity maps. The first catalog
family is `gaia-hip`, which augments the official Gaia-Hipparcos crossmatch.

`evidence/` contains compact evidence products used to justify curated rows.
Evidence is not necessarily loaded by the production build, but it must be
kept for reviewability.

`builds/` contains reproducible build records. These are the public answer to
"what inputs and code produced this output?" Store build configs, code SHAs,
row counts, and checksums here.

`schemas/` contains machine-readable schemas for stable public artifacts.

`templates/` contains starter files for new catalogue versions and builds.

## Do Not Store

- Full raw Gaia or Hipparcos catalogues.
- Full generated octree payloads unless we explicitly decide a release should
  publish one.
- Machine-specific absolute paths in public manifests.
- Credentials, tokens, private download URLs, or local environment files.
- Large one-off debugging outputs that cannot be explained by a manifest.
