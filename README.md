# Found in Space Catalogs

Curated data products for Found in Space.

This repository is intended to hold citable, versioned catalogue inputs and
build records, not pipeline implementation code. The pipeline and octree
builders consume these files as inputs and record the exact catalogue release
that was used.

Status: draft repository layout. No public catalogue release has been made yet.

## Repository Roles

- `overrides/` - curated stellar record additions, replacements, and drops.
- `crossmatches/` - supplemental identity maps, starting with Gaia-HIP.
- `evidence/` - compact audit evidence that explains curated rows.
- `builds/` - versioned build configs and post-build counts/checksums.
- `schemas/` - machine-readable schemas for published tables and manifests.
- `templates/` - starter files for new catalogue releases and builds.
- `docs/` - maintenance rules, naming conventions, and release process.

## Principles

- This repo publishes curated inputs and compact provenance, not raw Gaia,
  Hipparcos, or full generated octree payloads.
- Every released table must have a manifest, schema, version, and provenance.
- Build configs are versioned here because they define the published data
  product.
- Post-build records should be objective and compact: row counts, artifact
  sizes, checksums, and dataset identifiers.
- Pipeline and octree code are referenced by upstream repository URL and git
  commit SHA. The code itself is not vendored into this repo.

## Key Docs

- [Repository layout](docs/layout.md)
- [Naming conventions](docs/naming.md)
- [Configuration locations](docs/configuration.md)
- [Overrides catalog](docs/overrides.md)
- [Supplemental crossmatches](docs/crossmatches.md)
- [Audit maintenance commands](docs/audit.md)
- [Build records](docs/build-records.md)
- [Release process](docs/release-process.md)

## Related Repositories

- `Found-in-Space/pipeline` - catalogue processing and merge pipeline.
- `Found-in-Space/found-in-space-octree` - octree packaging pipeline.

## uv Environment

This repo is a uv project so catalogue maintenance commands can run against a
pinned pipeline checkout:

```bash
uv sync
```

The pipeline dependency is pinned in `pyproject.toml` by git SHA. Build records
should repeat that SHA in `build.lock.toml`.

Use the optional audit group for local catalog-quality analysis:

```bash
uv sync --group audit
```

## License

License is not selected yet. Choose and document the data license before the
first public release.
