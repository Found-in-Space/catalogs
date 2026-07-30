# Found in Space Stellar Overrides

Release: `20260730.2`
Series ID: `fis.overrides`
Status: release candidate

This is the first complete publication candidate for the original Found in
Space stellar override collection. It is cumulative: the three original Alpha
Centauri overrides are retained, and 48 reviewed distance replacements are
added.

The executable set contains exactly 51 `replace` actions:

- 3 retained records: Alpha Cen A, Alpha Cen B, and Proxima Centauri; and
- 48 additions selected from the 81-row distance-review tracker.

Sirius B and Procyon B are not part of the legacy base. They were deliberately
retired in pipeline history before publication. The Sun is also absent: it is a
separate opt-in application reference, not a stellar override in this series.

## Version History

The three Alpha Centauri entries preserve the `override_id`, target, policy,
coordinates, distance, absolute magnitude, temperature, and photometry fields
from public pipeline commit
`74635226a917ec4c2c1c08c46b38cd05d227732a`. A byte-identical copy of that
historical YAML is published as
`evidence/alpha_cen_legacy_source.yaml`.

The executable Alpha catalog adds structured provenance and corrects stale
explanatory text. In the current controlled Gaia DR3
`hipparcos2_best_neighbour` artifact, Alpha Cen B and Proxima are mapped to
their HIP rows; Alpha Cen A is not. The release continues to use the published
best-neighbour table as the only automatic Gaia-Hipparcos pairing authority.
No supplemental pairing map is applied.

The 48 additions are byte-identical to the deterministic output at public
pipeline commit `ffd569dd1e733c5bd39bb2dd6050763d98e06a43`. Exactly 48 tracker
rows have `status == resolved`; the other 33 are evidence only.

Repository candidate `20260730.1` incorrectly presented those 48 additions as
a standalone catalog. It was never deposited with Zenodo and has no DOI.
Release `20260730.2` supersedes that unpublished candidate and restores the
intended cumulative publication.

## Catalog Components

- `catalog/alpha_cen.yaml` — the three retained original overrides, with
  refreshed provenance.
- `catalog/distance_resolution_v1_resolved.yaml` — the 48 reviewed additions.

The files remain separate so their distinct provenance can be audited. Together
they form one version of series `fis.overrides`.

## Pipeline Use

Controlled projects must select both files explicitly:

```toml
[overrides]
output_parquet = "pipeline/overrides.parquet"
source_paths = [
  "/path/to/catalogs/publications/20260730.2/catalog/alpha_cen.yaml",
  "/path/to/catalogs/publications/20260730.2/catalog/distance_resolution_v1_resolved.yaml",
]
```

The pipeline's packaged default override set remains empty. Explicit source
selection makes the publication release and checksums part of each controlled
run's provenance.

## References and Evidence

Every executable row has a selected distance reference, explanatory notes, an
uncertainty, and traceable astrometry, photometry, and temperature inputs.
`REFERENCES.md` gives complete citations for the three retained rows and the
source groups used by the 48 reviewed additions.

Published evidence includes:

- `evidence/alpha_cen_legacy_source.yaml` — byte-identical historical source;
- `evidence/alpha_cen_pairing_review.json` — current H2BN result for all three
  legacy targets, including source artifact checksums;
- `evidence/distance-resolution-v1.csv` — the complete 81-row review tracker;
- four compact staged/review Parquet inputs for the 48 additions;
- `evidence/build_report.json` — deterministic 48-row component report;
- `evidence/publication_build_report.json` — generated cumulative counts,
  exclusions, identities, hashes, and policy checks;
- `evidence/override_quality_report.json` — generated per-row results for all
  51 overrides; and
- `evidence/input_provenance.json` — exact public commits, transformations,
  exclusions, dependency resolution, and evidence hashes.

## Quality Checks

The assembler applies 19 checks to every row. They cover required identity
fields, finite and bounded coordinates, positive physical values, `replace`
semantics, review status, distance uncertainty and citation, apparent-to-
absolute magnitude reconstruction, astrometry/photometry/temperature
traceability, runtime loader values, Cartesian distance, and exclusion of the
Sun and retired binary records. It fails the release if any row fails.

From a clean `catalogs` checkout:

```bash
UV_CACHE_DIR=.cache/uv uv sync --locked --all-groups
UV_CACHE_DIR=.cache/uv uv run fis-catalogs audit \
  assemble-overrides-publication \
  --release-dir publications/20260730.2
UV_CACHE_DIR=.cache/uv uv run pytest
cd publications/20260730.2
sha256sum --check checksums.sha256
```
