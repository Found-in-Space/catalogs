# Run Log

Release: `20260730.2`
Series: `fis.overrides`

## Corrected Publication Scope

The cumulative release contains:

- 3 retained Alpha Centauri overrides from the original override set;
- 48 reviewed additions from the distance-resolution tracker;
- 33 provisional tracker rows retained as evidence only;
- 2 historically retired binary overrides excluded; and
- the Sun excluded for separate publication.

All 51 executable rows use `action: replace`.

Candidate `20260730.1` contained only the 48 additions and therefore did not
represent the intended cumulative publication. It was not deposited with
Zenodo and has no DOI. This release supersedes that unpublished repository
candidate.

## Publication Lifecycle Decision

`fis.overrides` is maintained as one evolving Zenodo version chain. Every
published release is immutable and cumulative unless its manifest explicitly
states otherwise. Changes to executable rows, evidence, checksums, selection
rules, or methodology require a new repository release and Zenodo's **New
version** workflow in the existing lineage. Metadata may be edited in place
only when neither the release payload nor its scientific interpretation
changes.

Every published snapshot has a distinct Version DOI. The Concept DOI remains
stable across the chain. Controlled runs must record the release ID,
`checksums.sha256`, and Version DOI. The Concept DOI is for the evolving series
or latest-version references, not for pinning reproducible inputs.

No earlier `fis.overrides` Zenodo record exists. Consequently, `20260730.2`
will be the initial deposit rather than a Zenodo revision. Version DOI
[`10.5281/zenodo.21703732`](https://doi.org/10.5281/zenodo.21703732) was
reserved before the final package was assembled. Publishing the deposit will
register that Version DOI and assign the stable Concept DOI. Subsequent
releases must use **New version** on that record and must not create a separate
catalog record.

## Public Source State

Legacy Alpha source:

- repository: `https://github.com/Found-in-Space/pipeline`;
- commit: `74635226a917ec4c2c1c08c46b38cd05d227732a`;
- commit time: `2026-07-29T09:41:55+01:00`;
- path:
  `src/foundinspace/pipeline/overrides/data/alpha_cen.yaml`; and
- SHA-256:
  `8626f9a9f4a4550921108280a1092e0190503f4912a77549e1e50f228bbafb9f`.

Reviewed distance source:

- repository: `https://github.com/Found-in-Space/pipeline`;
- commit: `ffd569dd1e733c5bd39bb2dd6050763d98e06a43`;
- commit time: `2026-07-30T12:02:20+02:00`;
- path:
  `tools/curation/distance_resolution_v1/distance-resolution-v1-resolved.yaml`;
  and
- SHA-256:
  `a53122ace82402969eace466adc9178ab184e7c4758ddd3e90a69372985a43c4`.

At validation time the pipeline checkout was clean, its `HEAD` equalled
`origin/main`, and both were the reviewed-distance commit above.

## Legacy Reconstruction and Current-State Review

`evidence/alpha_cen_legacy_source.yaml` is byte-identical to the historical
three-row Alpha source. The publication catalog retains every executable field
from that file: override ID, action, target, reason, policy version,
coordinates, distance, absolute magnitude, temperature, and photometry.
Structured provenance and corrected explanatory text are the only changes.

The history review confirmed that `manual.sirius_b.replace.v1` and
`manual.procyon_b.replace.v1` were deliberately removed before publication.
The main-branch retirement commit is
`7fcb20d2506d50540445a6c990e9080e6faf6de6`. Neither record is executable in
this release.

The current controlled Gaia DR3 `hipparcos2_best_neighbour` artifact has
99,525 rows and SHA-256
`2590acdbfd6016527dcb028a76a4ee9ea7775e6c3161924f2a9844b1ce221159`.
The three-target review found:

- HIP 71683 / Alpha Cen A: no H2BN row;
- HIP 71681 / Alpha Cen B: Gaia DR3 `5877748442128924544`, one neighbour,
  `0.46895134 arcsec`; and
- HIP 70890 / Proxima: Gaia DR3 `5853498713190525696`, one neighbour,
  `0.042399194 arcsec`.

This corrects the obsolete historical statement that Proxima was absent from
H2BN. The published best-neighbour table remains the only automatic
Gaia-Hipparcos pairing authority; no supplemental map is used for merging.

## References

The three retained records were checked against exact bibliographic sources:

- Alpha Cen AB system parallax: Kervella et al. (2016),
  <https://doi.org/10.1051/0004-6361/201629201>;
- Hipparcos source astrometry: van Leeuwen (2007),
  <https://doi.org/10.1051/0004-6361:20078357>;
- Alpha Cen A/B temperatures: Heiter et al. (2015),
  <https://doi.org/10.1051/0004-6361/201526319>;
- Alpha Cen A/B Johnson V: Ducati (2002), VizieR II/237 via SIMBAD;
- Proxima astrometry/parallax: Gaia DR3 source
  `5853498713190525696`;
- Proxima Johnson V: SIMBAD record sourced to Jao et al. (2014),
  <https://doi.org/10.1088/0004-6256/147/1/21>; and
- Proxima temperature: Ribas et al. (2017),
  <https://doi.org/10.1051/0004-6361/201730582>.

The 48 additions retain their selected distance references, uncertainties,
notes, and staged astrometry/photometry/temperature donor identities.
`REFERENCES.md` gives the complete grouped bibliography.

## Deterministic 48-Row Rebuild

The reviewed-distance component was rebuilt in check mode from the published
tracker and compact preflight inputs using the clean public pipeline checkout:

```bash
UV_CACHE_DIR=.cache/uv uv run python \
  -m tools.curation.distance_resolution_v1.build_overrides_cli \
  --tracker ../catalogs/publications/20260730.2/evidence/distance-resolution-v1.csv \
  --preflight-dir ../catalogs/publications/20260730.2/evidence \
  --output ../catalogs/publications/20260730.2/catalog/distance_resolution_v1_resolved.yaml \
  --check
```

Results:

- tracker rows: `81`;
- resolved rows / output rows: `48`;
- provisional rows: `33`;
- payload rows cross-checked: `48`;
- maximum apparent-magnitude rebase delta:
  `3.552713678800501e-15`;
- identity, distance, uncertainty, reference, notes, and candidate-review
  matches: all `true`; and
- deterministic rebuild match: `true`.

## Cumulative Assembly and Per-Row Quality

The cumulative release was assembled with:

```bash
UV_CACHE_DIR=.cache/uv uv run fis-catalogs audit \
  assemble-overrides-publication \
  --release-dir publications/20260730.2
```

The assembler loaded both YAML components through the pinned public pipeline
dependency and checked every row. `evidence/override_quality_report.json`
contains 19 named checks and complete reference pointers for each override.

Results:

- runtime rows: `51`;
- unique override IDs: `51`;
- unique target keys: `51`;
- rows quality-checked: `51`;
- rows passing all 19 checks: `51`;
- failed rows: `0`;
- retired binary rows present: `0`;
- Sun rows present: `0`; and
- supplemental-pairing rows applied: `0`.

## Validation Environment and Final Checks

The catalogs environment resolved `found-in-space-pipeline` from:

```json
{
  "url": "https://github.com/Found-in-Space/pipeline.git",
  "vcs_info": {
    "vcs": "git",
    "commit_id": "ffd569dd1e733c5bd39bb2dd6050763d98e06a43",
    "requested_revision": "ffd569dd1e733c5bd39bb2dd6050763d98e06a43"
  }
}
```

The imported module path was inside the catalogs virtual environment, not a
local pipeline checkout.

Final validation results:

- deterministic rebuild from published evidence: passed;
- complete catalogs test suite: `16 passed`;
- Python byte-compilation of `src` and `tests`: passed;
- release checksum verification: every file passed;
- repository diff whitespace/error check: passed; and
- per-row quality gate: `51/51 passed`.

`checksums.sha256` was regenerated after all other release files were final and
does not include itself.
