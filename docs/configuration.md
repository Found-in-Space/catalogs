# Configuration Locations

Build configuration is part of the published data product. Store the config
that defines a build under `builds/<build_id>/`.

## Build Directory

```text
builds/<build_id>/
  README.md
  build.lock.toml
  config/
    pipeline.project.toml
    octree.project.toml
  postbuild/
    counts.json
    artifacts.json
    checksums.sha256
```

## `build.lock.toml`

`build.lock.toml` records exact upstream inputs and code references:

- catalog repo version and commit
- pipeline repository URL and commit SHA
- octree repository URL and commit SHA
- source catalogue releases used
- correction catalogue versions used

This file should not contain local scratch paths. Use repository URLs, release
IDs, DOIs, and git SHAs.

## Project TOMLs

`config/pipeline.project.toml` is the pipeline project file used for the build.

`config/octree.project.toml` is the octree project file used for the build.

When possible, paths should be relative to the build directory or use logical
release paths. Avoid machine-specific absolute paths in published configs. If a
local run requires absolute paths, keep those in local scratch files and copy a
redacted/rebased config into the build directory for publication.

## Post-Build Records

`postbuild/counts.json` records row counts and compact quality counters.

`postbuild/artifacts.json` records published artifacts with path, kind, byte
size, row count when relevant, SHA-256, and dataset UUID when relevant.

`postbuild/checksums.sha256` is a standard checksum file for released artifacts
and important manifests.

## Templates

Starter files live under `templates/`. Copy them into a new build directory and
then fill in concrete values.
