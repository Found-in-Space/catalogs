# Naming Conventions

Names should be boring, stable, lowercase, and easy to sort.

## Catalogue Versions

Catalogue versions use semantic version tags:

```text
v0.1.0
v0.2.0
v1.0.0
```

Use a new patch version for corrections that do not change schema. Use a new
minor version when rows are added or policy changes materially. Use a new major
version when schemas or interpretation change incompatibly.

Directory names keep the dots:

```text
overrides/v0.1.0/
crossmatches/gaia-hip/v0.1.0/
```

File stems use snake case:

```text
supplemental_gaia_hip.parquet
distance_quality_summary.csv
```

## Build IDs

Build IDs use lowercase kebab case:

```text
bright-mag10-v0.1.0
full-dr3-v0.1.0
nearby-100pc-v0.1.0
```

Recommended pattern:

```text
<scope>-<selection>-<catalog_version>
```

Examples:

- `bright-mag10-v0.1.0`
- `full-dr3-v1.0.0`
- `nearby-100pc-v0.2.0`

## Override IDs

Existing override IDs such as `manual.alpha_cen_a.replace.v1` remain valid.
New override IDs should use this shape:

```text
fis.override.<object_slug>.<action>.v<record_version>
```

Examples:

```text
fis.override.alpha_cen_a.replace.v1
fis.override.sirius_b.replace.v1
fis.override.hip_90910.drop.v1
fis.override.sun.add.v1
```

Rules:

- `object_slug` is lowercase ASCII with underscores.
- `action` is one of `add`, `replace`, or `drop`.
- Increment `record_version` only when changing the same logical override.
- Do not reuse an override ID for a different target.

## Crossmatch Families

Crossmatch family names use kebab case:

```text
gaia-hip
```

Published Gaia-HIP supplemental rows should use a stable `mapping_source`
string. The current pipeline prototype emits `local_close_pair_v1`; a public
catalogue may wrap that with manifest metadata, but do not silently change the
table value without updating the pipeline consumer and schema.

## Manifest Names

Every versioned directory should include:

```text
manifest.toml
```

Build directories should include:

```text
build.lock.toml
```

Post-build records should use:

```text
counts.json
artifacts.json
checksums.sha256
```
