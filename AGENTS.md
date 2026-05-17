# Agent Instructions

## Python Tooling: Use `uv`

- Use `uv` for Python dependency and environment operations in this repository.
- Do not use `pip`, `poetry`, or `conda` commands directly.
- Run Python entrypoints and tools with `uv run <command>`.
- Run tests with `uv run pytest`.

## Publication Provenance

Catalog publications must be reproducible from immutable or public code inputs.

- Use only public package releases or Git dependencies pinned to an exact commit
  SHA in `pyproject.toml` and `uv.lock`.
- Do not use local dirty checkouts, path dependencies, editable installs,
  `PYTHONPATH`, `sys.path` injection, or environment overrides to generate or
  validate publication artifacts.
- If a publication needs unreleased pipeline or octree behavior, first commit
  and push that upstream change, then pin this repo to the exact public commit
  SHA before generating or validating release evidence.
- Local dirty checkouts may be used for exploratory scratch work only. Any
  artifacts created that way must be treated as non-release scratch outputs and
  must not be copied into `publications/`.
- Record the exact pinned upstream code versions in the publication run log and
  manifest before calling a release provenance-clean.

Before finalizing a publication, verify the imported package location and
version source are from the pinned environment, not a local checkout.
