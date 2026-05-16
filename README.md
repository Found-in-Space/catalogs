# Found in Space Catalogs

Curated data products for Found in Space.

This repository is intended to hold citable, versioned catalogue publications
and build records, not pipeline implementation code. Downstream builders can
consume these files as inputs and record the exact publication releases that
were used.

Status: draft repository layout. No public publication has been made yet.

## Repository Roles

- `publications/` - citable data publications.
- `docs/` - repository housekeeping.
- `schemas/` - shared schemas when formats stabilize.
- `templates/` - minimal starter files.

## Principles

- This repo publishes curated inputs and the provenance needed to understand
  them, not raw source catalogues or scratch build outputs.
- Each publication should explain itself from its own directory.
- Generated records, such as counts and checksums, should be generated from the
  final files rather than hand-edited.
- External code used to create a publication should be referenced by repository
  URL and git commit SHA. That code is not vendored into this repo.

## Key Docs

- [Repository layout](docs/layout.md)
- [Naming conventions](docs/naming.md)
- [First publications](docs/first-publications.md)
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

The pipeline dependency is pinned in `pyproject.toml` by git SHA for local
maintenance commands. Publications should record the code references that
matter for their own provenance.

Install optional dependency groups only when a maintenance command needs them:

```bash
uv sync --group <group>
```

## License

License is not selected yet. Choose and document the data license before the
first public release.
