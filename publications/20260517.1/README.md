# Gaia-HIP Review Candidate Evidence

Release: `20260517.1`

This publication currently contains the systematic candidate-discovery and
priority-ranking evidence for a Gaia DR3 / Hipparcos-2 quality review. It does
not publish override YAML.

The retained artifacts identify bright, nearby, and high-proper-motion stars
whose Gaia/Hipparcos source rows deserve review against secondary catalogs or
published literature. Replacement values should be generated later only from
explicit per-target review decisions in the pipeline YAML override format.

The Sun is intentionally not included here. `builtin:sun.yaml` remains part of
the Found-In-Space pipeline because it is a synthetic origin object needed by
the pipeline itself rather than an externally curated stellar catalog record.

## License And Notice

Found in Space original material in this publication is released under CC BY
4.0, as described in `LICENSE.txt`.

Source catalog data, identifiers, and measurements remain subject to upstream
terms and credit requirements. See `NOTICE.md` and `REFERENCES.md`.

## Current Scope

Initial objective cohorts:

- 500 brightest Gaia DR3 sources.
- 500 nearest Gaia DR3 sources.
- 500 highest-proper-motion Gaia DR3 sources.
- 500 brightest Hipparcos-2 sources.
- 500 nearest Hipparcos-2 sources.
- 500 highest-proper-motion Hipparcos-2 sources.

Primary retained tables:

- `evidence/review_candidates.parquet`
- `evidence/review_candidates.csv`
- `evidence/review_candidate_report.json`
- `evidence/review_priority_candidates.parquet`
- `evidence/review_priority_candidates.csv`
- `evidence/review_priority_report.json`

Supporting retained cohort and crossmatch evidence:

- `evidence/gaia_review_candidates.parquet`
- `evidence/gaia_review_candidates.csv`
- `evidence/hipparcos2_review_candidates.parquet`
- `evidence/hipparcos2_review_candidates.csv`
- `evidence/gaia_hip_review_best_neighbour_lookup.parquet`
- `evidence/gaia_hip_review_best_neighbour_lookup.csv`
- `evidence/gaia_hip_review_neighbourhood_lookup.parquet`
- `evidence/gaia_hip_review_neighbourhood_lookup.csv`
- `evidence/fis_20260515_1_review_supplemental_lookup.parquet`
- `evidence/fis_20260515_1_review_supplemental_lookup.csv`

Crossmatch context is included from both the official Gaia DR3 Hipparcos-2
best-neighbour/neighbourhood tables and the Found-In-Space `20260515.1`
supplemental Gaia-HIP display map. Within these review cohorts, the official
best-neighbour table links `474` Gaia/HIP candidate pairs; the FiS supplemental
map adds `131` candidate pairs, for `605` linked pairs total.

The scored priority list uses only objective cohort membership and catalog
quality/context signals. It combines:

- cohort rank and multi-cohort membership;
- practical display impact from apparent magnitude, parallax distance, and
  proper motion;
- weighted Gaia/Hipparcos quality flags;
- missing or partial Gaia-HIP crossmatch context.

Scored rows by priority tier:

| Tier | Rows |
| --- | ---: |
| P1 | 34 |
| P2 | 351 |
| P3 | 271 |
| P4 | 1,896 |

No source-row replacement should be inferred from these priority scores. They
are a worklist for later review, not curation decisions.

Full source working copies used to select cohorts remain under `local/` and are
not publication artifacts.

## Checksums

`checksums.sha256` records SHA-256 checksums for the current publication files.
