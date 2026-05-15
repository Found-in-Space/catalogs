# Overrides Catalog

Overrides are curated stellar record edits. They are data, not pipeline config.

## Location

```text
overrides/<catalog_version>/
  manifest.toml
  yaml/
    *.yaml
  tables/
    overrides.parquet
    overrides.csv
```

The YAML files are the human-reviewed source. The Parquet/CSV tables are
normalized build inputs generated from the YAML.

## Actions

`add` inserts a manual-only star that is absent from source catalogues.

`replace` keeps the target identity but replaces the physical payload.

`drop` suppresses a target row.

## Required Metadata

Each override row must include:

- `override_id`
- `action`
- target identity: `source`, `source_id`
- `override_reason`
- `override_policy_version`
- enough provenance to justify the value

## Evidence

Published overrides should point at source literature or catalogue evidence in
the row notes or the version manifest. Do not rely on memory or issue comments
as the only provenance.

## Versioning

Additive changes can usually be a minor release. Corrections to values can be a
patch release if schema and policy are unchanged. Incompatible policy changes
require a major release.

## Pipeline Semantics

The pipeline treats overrides as authoritative inputs. Pair-aware behavior is
handled by the pipeline merge stage: if an override targets one side of a
crossmatch-linked pair, the pair is resolved by the override.
