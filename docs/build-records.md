# Build Records

Build records connect released catalogue inputs to produced artifacts.

## Location

```text
builds/<build_id>/
  build.lock.toml
  config/
    pipeline.project.toml
    octree.project.toml
  postbuild/
    counts.json
    artifacts.json
    checksums.sha256
```

## Counts

`counts.json` should contain compact aggregate counts:

- source rows loaded
- official crossmatch rows
- supplemental crossmatch rows
- override rows by action
- merged rows
- matched-pair counts
- audit/manual-review counts
- octree input rows
- sidecar row counts

Do not record per-row logs here.

## Artifacts

`artifacts.json` should describe released files:

- logical path
- artifact kind
- byte size
- row count when relevant
- SHA-256
- dataset UUID or sidecar UUID when relevant

## Checksums

`checksums.sha256` should use the standard format:

```text
<sha256>  <relative/path>
```

Include release-critical tables, configs, manifests, and compact post-build
records. Large generated outputs should be included only if they are part of
the actual release.
