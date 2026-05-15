# Supplemental Crossmatches

Supplemental crossmatches are curated identity links between source catalogues.
They are separate from overrides because they assert identity, not replacement
payload values.

## Gaia-HIP Location

```text
crossmatches/gaia-hip/<catalog_version>/
  manifest.toml
  supplemental_gaia_hip.parquet
  supplemental_gaia_hip.csv
```

Evidence lives separately:

```text
evidence/gaia-hip/<catalog_version>/
  manifest.toml
  match_evidence.parquet
  audit_match_report.json
  distance_pct_histogram.png
  distance_pct_vs_astrometry_quality.png
```

## Scope

Do not republish the full official Gaia-Hipparcos crossmatch here. Publish only
our supplemental rows and enough evidence to understand them.

## Minimal Table Columns

The supplemental Gaia-HIP table should match the pipeline crossmatch schema:

- `gaia_source_id`
- `hip_source_id`
- `mapping_source`
- `number_of_neighbours`
- `angular_distance`

The combined official-plus-supplemental table is a build artifact, not the
primary curated source.

## Validation Rules

- Gaia IDs must be unique within a published supplemental map.
- HIP IDs must be unique within a published supplemental map.
- The official map plus supplemental map must also be one-to-one.
- Rows that conflict with the official map require manual review evidence.
- The table must have a manifest recording source data versions and policy.

## Decision Policy

Automatic supplemental rows should be conservative. Manual-review rows should
remain evidence until a reviewer promotes them into the curated map.
