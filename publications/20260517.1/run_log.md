# Run Log

Release: `20260517.1`

This log records the retained local steps for the systematic Gaia/Hipparcos
candidate-review evidence publication.

## Environment

- Repository: `found-in-space-catalogs`
- Working directory: `/data/work/fis/catalogs`
- Publication directory: `publications/20260517.1/`
- Pipeline source repository: `https://github.com/Found-in-Space/pipeline`
- Pipeline commit:
  `b2833cc04ca04bf02ef1831c3726acecb402b717`
- Catalog dependency pin:
  `found-in-space-pipeline` at
  `b2833cc04ca04bf02ef1831c3726acecb402b717`
- Execution date: `2026-05-17`

No local dirty pipeline checkout, `PYTHONPATH`, editable install, or path
dependency was used to generate the retained candidate-review evidence
artifacts.

## Steps Executed

1. Defined the publication scope.

   Decision:

   - This release currently retains systematic Gaia/Hipparcos review candidate
     evidence only.
   - Candidate selection comes only from objective bright, nearby, and
     high-proper-motion cohorts.
   - Scores and quality flags prioritize review effort only; they are not
     source-row replacement decisions.
   - Override YAML should be generated later only from explicit per-target
     secondary-source review decisions.
   - `sun.yaml` remains in the pipeline as `builtin:sun.yaml`.

2. Created the publication directory.

   ```bash
   mkdir -p publications/20260517.1
   ```

3. Added publication housekeeping files.

   Files:

   - `README.md`
   - `LICENSE.txt`
   - `NOTICE.md`
   - `REFERENCES.md`
   - `manifest.toml`

   Decision:

   - Treat the publication as an academic public-interest data work.
   - Release Found-In-Space original curation and documentation under
     CC BY 4.0.
   - Preserve upstream terms, citation expectations, and credit requirements
     for Gaia, Hipparcos/Tycho, VizieR/CDS, and related catalog data.

4. Built objective candidate-discovery cohorts.

   This release starts from objective candidate cohorts. The evidence pass
   identifies Gaia/Hipparcos rows that deserve inspection against source
   catalogs and literature.

   Initial review cohorts:

   - `500` brightest Gaia DR3 sources by `phot_g_mean_mag`;
   - `500` nearest Gaia DR3 sources by positive `parallax`;
   - `500` highest proper-motion Gaia DR3 sources by total proper motion;
   - `500` brightest Hipparcos-2 sources by `Hpmag`;
   - `500` nearest Hipparcos-2 sources by positive `Plx`;
   - `500` highest proper-motion Hipparcos-2 sources by total proper motion.

5. Fetched Gaia DR3 review cohorts.

   Gaia source-row fields include sky position, parallax, proper motion,
   photometry, RUWE, astrometric solution fields, non-single-star flag,
   duplicate flag, visibility periods, excess-noise/IPD diagnostics, and
   variable-star flag.

   Outputs:

   - `evidence/gaia_review_brightest_500.csv`
   - `evidence/gaia_review_brightest_500.parquet`
   - `evidence/gaia_review_nearest_500.csv`
   - `evidence/gaia_review_nearest_500.parquet`
   - `evidence/gaia_review_high_pm_500.csv`
   - `evidence/gaia_review_high_pm_500.parquet`
   - exact ADQL files under `evidence/adql/`

   Result:

   - Gaia brightest rows: `500`
   - Gaia nearest rows: `500`
   - Gaia high-proper-motion rows: `500`
   - Unique Gaia review candidates after cohort union: `1,315`

6. Fetched Hipparcos-2 review cohorts.

   The full VizieR `I/311/hip2` table is used as a local working input to
   select the three cohorts. The full source copy is not a publication
   artifact.

   Local working outputs:

   - `local/runs/20260517.1/review-candidates/working/hipparcos2_review_source_rows.csv`
   - `local/runs/20260517.1/review-candidates/working/hipparcos2_review_source_rows.parquet`

   Published outputs:

   - `evidence/hipparcos2_review_brightest_500.csv`
   - `evidence/hipparcos2_review_brightest_500.parquet`
   - `evidence/hipparcos2_review_nearest_500.csv`
   - `evidence/hipparcos2_review_nearest_500.parquet`
   - `evidence/hipparcos2_review_high_pm_500.csv`
   - `evidence/hipparcos2_review_high_pm_500.parquet`

   Result:

   - Hipparcos-2 source rows fetched locally: `117,955`
   - Hipparcos-2 brightest rows: `500`
   - Hipparcos-2 nearest rows: `500`
   - Hipparcos-2 high-proper-motion rows: `500`
   - Unique Hipparcos-2 review candidates after cohort union: `1,237`

7. Added Gaia-Hipparcos crossmatch context for review candidates.

   Purpose:

   - determine whether candidate Gaia/HIP IDs already have official
     `hipparcos2_best_neighbour` links;
   - keep `hipparcos2_neighbourhood` rows as additional ambiguity context;
   - include the Found-In-Space `20260515.1` supplemental Gaia-HIP display map
     to see how much additional candidate overlap it contributes.

   Tables queried:

   - `gaiadr3.hipparcos2_best_neighbour`
   - `gaiadr3.hipparcos2_neighbourhood`

   Local publication input:

   - `publications/20260515.1/catalog/fis_gaia_hip_supplemental_display_map.parquet`

   Outputs:

   - `evidence/gaia_hip_review_best_neighbour_lookup.csv`
   - `evidence/gaia_hip_review_best_neighbour_lookup.parquet`
   - `evidence/fis_20260515_1_review_supplemental_lookup.csv`
   - `evidence/fis_20260515_1_review_supplemental_lookup.parquet`
   - `evidence/gaia_hip_review_neighbourhood_lookup.csv`
   - `evidence/gaia_hip_review_neighbourhood_lookup.parquet`
   - exact chunked ADQL files under `evidence/adql/`

   Result:

   - Best-neighbour rows fetched for candidate IDs: `964`
   - FiS supplemental rows for candidate IDs: `213`
   - Official best-neighbour candidate-candidate pairs: `474`
   - FiS supplemental candidate-candidate pairs: `131`
   - Combined candidate-candidate pairs: `605`
   - Neighbourhood rows fetched for candidate IDs: `967`

8. Built review-candidate tables and broad quality flags.

   Outputs:

   - `evidence/gaia_review_candidates.csv`
   - `evidence/gaia_review_candidates.parquet`
   - `evidence/hipparcos2_review_candidates.csv`
   - `evidence/hipparcos2_review_candidates.parquet`
   - `evidence/review_candidates.csv`
   - `evidence/review_candidates.parquet`
   - `evidence/review_candidate_report.json`

   Result:

   - Combined candidate rows: `2,552`
   - Unique Gaia candidates: `1,315`
   - Unique Hipparcos-2 candidates: `1,237`
   - Gaia/HIP candidate pairs linked by official best-neighbour only: `474`
   - Gaia/HIP candidate pairs linked after adding FiS `20260515.1`: `605`

   Quality flag counts:

   ```text
   astrometric_excess_noise_gt_1       514
   astrometric_params_not_31_or_95      80
   duplicated_source                    16
   hip_component_flag                  175
   hip_solution_type_not_5             353
   ipd_frac_multi_peak_gt_10           103
   missing_bp_or_rp                     12
   non_positive_parallax                 1
   non_single_star                      25
   parallax_frac_error_gt_0p1          168
   phot_variable                        84
   ruwe_gt_1p4                         570
   visibility_periods_lt_8              31
   ```

   Interpretation:

   - These flags are review signals only.
   - A flagged row is not an override decision.
   - Review-derived overrides should only be created after later inspection
     against appropriate catalogs or published literature.

9. Built the scored review priority list.

   Purpose:

   - provide a single ranked table for systematic follow-up;
   - make the ranking reproducible and auditable;
   - avoid any score bonus from non-cohort review signals.

   Scoring model:

   - `cohort_score`: rank-weighted membership in the brightest, nearest, and
     high-proper-motion cohorts, plus a multi-cohort bonus;
   - `visibility_score`: practical display impact from apparent magnitude,
     parallax distance, and total proper motion;
   - `quality_score`: weighted Gaia/Hipparcos quality flags, capped at `30`;
   - `crossmatch_gap_score`: missing official/FIS Gaia-HIP overlap, or partial
     neighbourhood/local-supplemental-only context.

   Outputs:

   - `evidence/score_review_candidates.py`
   - `evidence/review_priority_candidates.csv`
   - `evidence/review_priority_candidates.parquet`
   - `evidence/review_priority_report.json`

   Result:

   - Scored candidate rows: `2,552`
   - P1 rows: `34`
   - P2 rows: `351`
   - P3 rows: `271`
   - P4 rows: `1,896`

   Interpretation:

   - Scores use only the systematic candidate cohorts and catalog
     quality/context signals.
   - The ranking prioritizes review effort only; it is not an override
     decision.

10. Removed the heuristic follow-up and override artifacts.

   The previous generated follow-up tables, scripts, lookup queries, and YAML
   were removed from this publication because the artifacts did not record
   sufficient per-target secondary-source review to justify source-row
   replacement values.

   Current publication status:

   - YAML files: `0`
   - Override rows: `0`
   - Retained evidence: objective candidate cohorts, crossmatch context,
     quality flags, and review-priority scores.

## Release Artifacts Created So Far

```text
publications/20260517.1/
  LICENSE.txt
  NOTICE.md
  README.md
  REFERENCES.md
  checksums.sha256
  manifest.toml
  run_log.md
  evidence/
    fetch_review_candidate_cohorts.py
    score_review_candidates.py
    review_candidate_report.json
    review_priority_report.json
    review_candidates.csv
    review_candidates.parquet
    review_priority_candidates.csv
    review_priority_candidates.parquet
    gaia_review_candidates.csv
    gaia_review_candidates.parquet
    gaia_review_brightest_500.csv
    gaia_review_brightest_500.parquet
    gaia_review_nearest_500.csv
    gaia_review_nearest_500.parquet
    gaia_review_high_pm_500.csv
    gaia_review_high_pm_500.parquet
    hipparcos2_review_candidates.csv
    hipparcos2_review_candidates.parquet
    hipparcos2_review_brightest_500.csv
    hipparcos2_review_brightest_500.parquet
    hipparcos2_review_nearest_500.csv
    hipparcos2_review_nearest_500.parquet
    hipparcos2_review_high_pm_500.csv
    hipparcos2_review_high_pm_500.parquet
    gaia_hip_review_best_neighbour_lookup.csv
    gaia_hip_review_best_neighbour_lookup.parquet
    fis_20260515_1_review_supplemental_lookup.csv
    fis_20260515_1_review_supplemental_lookup.parquet
    gaia_hip_review_neighbourhood_lookup.csv
    gaia_hip_review_neighbourhood_lookup.parquet
    adql/
      *.adql
```

## Artifact Checksums

The complete generated checksum record for the current publication is
`checksums.sha256`.
