# Run Log

Release: `20260730.1`

## Source State

- Pipeline repository:
  `https://github.com/Found-in-Space/pipeline`
- Public pipeline commit:
  `ffd569dd1e733c5bd39bb2dd6050763d98e06a43`
- Source catalog:
  `tools/curation/distance_resolution_v1/distance-resolution-v1-resolved.yaml`
- Source catalog SHA-256:
  `a53122ace82402969eace466adc9178ab184e7c4758ddd3e90a69372985a43c4`
- Catalogs release ID: `20260730.1`

The pipeline worktree was clean and its `HEAD` matched `origin/main`. GitHub
comparison confirmed that the source commit was identical to remote `main`.
The catalogs dependency and lockfile were advanced to that exact public commit
before publication validation.

## Deterministic Rebuild Check

The candidate was rebuilt in check mode from the 81-row tracker and compact
preflight inputs:

```bash
UV_CACHE_DIR=.cache/uv uv run python \
  -m tools.curation.distance_resolution_v1.build_overrides_cli --check
```

The check reported:

- tracker rows: `81`;
- resolved rows: `48`;
- provisional rows: `33`;
- output YAML rows: `48`;
- payload rows cross-checked: `48`;
- maximum apparent-magnitude rebase delta:
  `3.552713678800501e-15`;
- identity, distance, uncertainty, reference, notes, and candidate-review
  matches: all `true`;
- deterministic rebuild match: `true`.

The complete machine-readable result is `evidence/build_report.json`.

## Publication Assembly

The executable YAML was copied without modification from the exact public
pipeline commit. The tracker and four preflight inputs named by the catalog's
embedded input manifest were copied into `evidence/`. Their SHA-256 identities
match both the embedded manifest and the deterministic build report.

Publication documentation records the opt-in consumer contract, the 48/33
selection boundary, scientific attribution, absence of a Sun row, and the fact
that this release does not change Gaia–Hipparcos pairing policy.

## Validation

Final validation commands:

```bash
UV_CACHE_DIR=.cache/uv uv sync --locked --all-groups
UV_CACHE_DIR=.cache/uv uv run pytest
sha256sum --check publications/20260730.1/checksums.sha256
```

The publication-specific test also builds the runtime override DataFrame using
the pipeline package imported from the pinned Git dependency and verifies 48
valid `replace` rows.

Final results:

- deterministic rebuild from the published evidence: passed;
- complete catalog test suite: `13 passed`;
- publication checksum verification: every file passed;
- Git dependency import provenance: resolved and requested commit both
  `ffd569dd1e733c5bd39bb2dd6050763d98e06a43`;
- repository diff whitespace/error check: passed.

`checksums.sha256` was generated after all other release files were final and
does not include itself.
