# Naming Conventions

Names should be boring, stable, lowercase, and easy to sort.

## Catalogue Releases

Catalogue releases use a date plus release number:

```text
20260515.1
20260515.2
20260516.1
```

The date is `YYYYMMDD`. The number after the dot is the release sequence for
that date. Start each day at `.1`.

Use a new release number whenever published rows, manifests, configs, or
post-build records change. If a specific override or schema needs its own
revision, use an additional local suffix such as `.v1` or `.v2` in that row ID
or schema path, not in the catalogue release directory.

Schema versions remain separate and use simple compatibility numbers such as
`schemas/gaia-hip-supplemental/v1.json`.

Directory names keep the dots:

```text
overrides/20260515.1/
crossmatches/gaia-hip/20260515.1/
```

File stems use snake case:

```text
supplemental_gaia_hip.parquet
distance_quality_summary.csv
```

## Build IDs

Build IDs use lowercase kebab case:

```text
bright-mag10-20260515.1
full-dr3-20260515.1
nearby-100pc-20260515.1
```

Recommended pattern:

```text
<scope>-<selection>-<catalog_release>
```

Examples:

- `bright-mag10-20260515.1`
- `full-dr3-20260516.1`
- `nearby-100pc-20260515.2`

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
