# Run Log

Release: `20260515.1`

This log records the local steps executed so far for the Gaia/HIP source-data
evidence package.

## Environment

- Repository: `found-in-space-catalogs`
- Working directory: `/data/work/fis/catalogs`
- Pipeline dependency: pinned by `pyproject.toml`
- Local scratch root: `local/runs/source-20260515.1/`
- Execution date: `2026-05-16`

## Steps Executed

1. Created a local scratch pipeline project.

   ```bash
   mkdir -p local/runs/source-20260515.1
   uv run fis-pipeline project init --profile small \
     local/runs/source-20260515.1/project.toml
   ```

   Output:

   - `local/runs/source-20260515.1/project.toml`

2. Downloaded the Hipparcos-2 source catalog through the pinned pipeline.

   ```bash
   uv run fis-pipeline hip download \
     --project local/runs/source-20260515.1/project.toml
   ```

   Output:

   - `local/runs/source-20260515.1/data/catalogs/hipparcos2.ecsv`

3. Built the processed Hipparcos Parquet through the pinned pipeline.

   ```bash
   uv run fis-pipeline hip build \
     --project local/runs/source-20260515.1/project.toml \
     --force
   ```

   Output:

   - `local/runs/source-20260515.1/data/processed/hip_stars.parquet`

   Result:

   - Raw Hipparcos rows: `117,955`
   - Dropped rows without finite `distance_use_pc`: `4,013`
   - Processed finite-distance rows: `113,942`

4. Queried Gaia Archive for official Gaia-HIP matches joined to Gaia
   photometry.

   Query shape:

   ```sql
   SELECT
     h.original_ext_source_id AS hip_source_id,
     h.source_id AS gaia_source_id,
     h.angular_distance,
     h.number_of_neighbours,
     g.phot_g_mean_mag,
     g.phot_bp_mean_mag,
     g.phot_rp_mean_mag
   FROM gaiadr3.hipparcos2_best_neighbour AS h
   JOIN gaiadr3.gaia_source AS g
     ON h.source_id = g.source_id
   ```

   Output:

   - `local/runs/source-20260515.1/data/catalogs/gaia_hip_official_gmag.ecsv`

   Result:

   - Official Gaia-HIP photometry join rows: `99,525`
   - Rows with finite Gaia `G`: `99,463`
   - Rows with non-finite Gaia `G`: `62`

5. Generated magnitude-relationship release evidence.

   Outputs:

   - `evidence/hip_gaia_magnitude_relationship.parquet`
   - `evidence/hip_gaia_magnitude_relationship.png`
   - `evidence/hip_gaia_magnitude_outliers.csv`
   - `evidence/hip_gaia_magnitude_summary.json`

   Result:

   - Faintest raw Hipparcos `Hpmag`: `14.5622`
   - Faintest processed Hipparcos `Hpmag`: `14.5622`
   - Official matches with Gaia `G > 14.5622`: `30`
   - Official matches with Gaia `G > 15.0`: `27`

6. Ran pipeline-shaped Gaia Archive HEALPix row-count checks to size candidate
   full-sky Gaia download limits.

   Query shape:

   ```sql
   SELECT
     (g.source_id / 9007199254740992) AS hp3,
     COUNT(*) AS n
   FROM gaiadr3.gaia_source AS g
   JOIN external.gaiaedr3_distance AS d
     ON d.source_id = g.source_id
   WHERE
     g.astrometric_params_solved IN (31, 95)
     AND (d.r_med_photogeo IS NOT NULL OR d.r_med_geo IS NOT NULL)
     AND g.phot_g_mean_mag <= {limit}
   GROUP BY 1
   ORDER BY n DESC
   ```

   This is the same grouped-HP3 count query shape used by the pipeline Gaia
   downloader planning step.

   Result:

   - Gaia `G <= 11`: `1,236,322` rows across `768` HP3 rows
     - Query hash:
       `439f889a4e0f63181059c823863a4ca7a1f6592ab05ad8e979e2f95c03f0aad2`
   - Gaia `G <= 12`: `3,062,324` rows across `768` HP3 rows
     - Query hash:
       `1920421db344ba233767dbf6826dc546674bb201a294ca6c10e2bd651a32cc2b`
   - Gaia `G <= 15`: `36,635,159` rows across `768` HP3 rows
     - Query hash:
       `eecad6c9c47ae25247869d4a1473d27d7f2e11054e1e6cb7aa4d6337f6015192`

   Derived sizing:

   - Additional rows for `11 < G <= 12`: `1,826,002`
   - Additional rows for `12 < G <= 15`: `33,572,835`
   - Additional rows for `11 < G <= 15`: `35,398,837`

7. Reviewed the Gaia-HIP mapping and merge code paths to confirm which fields
   are required for a supplemental crossmatch catalog.

   Code paths inspected:

   - Pipeline Gaia-HIP mapping stage:
     `foundinspace.pipeline.gaia_to_hip.pipeline`
   - Pipeline merge winner policy:
     `foundinspace.pipeline.merge.policy`
   - Pipeline merge orchestration and decision sidecar:
     `foundinspace.pipeline.merge.pipeline`
   - Catalog audit broad-scan matching code:
     `foundinspace.catalogs.audit.pipeline`

   Result:

   - The Gaia-HIP mapping artifact is only a cross-reference table:
     `gaia_source_id`, `hip_source_id`, `mapping_source`,
     `number_of_neighbours`, and `angular_distance`.
   - Winner selection is intentionally left to the final pipeline merge, where
     the full processed Gaia and Hipparcos rows are available.
   - For candidate crossmatch generation, Gaia parallax, Bailer-Jones distance,
     RUWE, astrometry quality, and astrophysical-parameter fields are not
     required as selected fields.
   - The first full-sky matching attempt should therefore try Gaia `G <= 15`
     with a limited matching field set:
     `source_id`, `ra`, `dec`, and `phot_g_mean_mag`.
   - Gaia `phot_bp_mean_mag` and `phot_rp_mean_mag` may be included as cheap
     evidence-only diagnostics, but they are not required for the core
     positional/magnitude match.
   - Hipparcos-side matching evidence should use the HIP source ID, J2016
     coordinates, and `Hpmag`.
   - The current `G <= 15` row count above uses the pipeline downloader
     eligibility filter, including the external distance join. If the matching
     download removes that eligibility filter entirely, rerun the row-count
     sizing check for the exact skinny query shape before treating the count as
     final.

8. Merged the broad-scan audit policy branch into the working tree as part of
   this snapshot.

   ```bash
   git merge --no-commit --no-ff audit/broad-scan-gaia-hip-policy
   ```

   Result:

   - Clean one-to-one close Gaia/HIP candidates are treated as supplemental
     mapping rows.
   - Distance disagreement is retained as diagnostic evidence, not as an
     automatic veto.
   - The audit CLI help text was updated to describe
     `--auto-distance-frac-diff` as diagnostic-only.

9. Re-ran the audit unit tests after the branch merge and CLI wording update.

   ```bash
   uv run pytest -q tests/audit/test_pipeline.py
   ```

   Result:

   - `3 passed in 3.03s`

10. Recorded the alternate targeted HEALPix/cone-fetch strategy for possible
    later use.

    This was explored as an alternative to full-sky Gaia `G <= 15`: fetch Gaia
    only in regional slices around the faint Hipparcos tail, then use those
    rows for broad candidate matching.

    Method:

    - Used the raw Hipparcos-2 table from
      `local/runs/source-20260515.1/data/catalogs/hipparcos2.ecsv`.
    - Converted raw `RArad`/`DErad` from radians to degrees.
    - Counted target footprints for raw Hipparcos selections:
      `11 < Hpmag <= 12`, `12 < Hpmag <= 15`, and `11 < Hpmag <= 15`.
    - Wrote two footprint tables:
      - containing HEALPix pixel plus all immediate neighbours;
      - HEALPix cells intersecting explicit cones around each HIP target.

    Outputs:

    - `evidence/hip_healpix_cone_footprint_summary.csv`
    - `evidence/hip_healpix_neighbor_footprint_summary.csv`
    - `evidence/hip_healpix_footprint_summary.json`

    Key examples:

    - Raw `12 < Hpmag <= 15`: `630` HIP targets.
    - Raw `11 < Hpmag <= 15`: `3,130` HIP targets.
    - At HEALPix level 10 with a `5` arcsec cone:
      - `12 < Hpmag <= 15`: `698` footprint pixels, `2.288387 deg^2`.
      - `11 < Hpmag <= 15`: `3,412` footprint pixels, `11.186211 deg^2`.
    - At HEALPix level 10 with a `60` arcsec cone:
      - `12 < Hpmag <= 15`: `1,545` footprint pixels, `5.065268 deg^2`.
      - `11 < Hpmag <= 15`: `7,618` footprint pixels, `24.975543 deg^2`.
    - At HEALPix level 10, expanding each `11 < Hpmag <= 15` containing pixel
      to all immediate neighbours produced `24,231` pixels and `79.441111 deg^2`.

    Decision:

    - The targeted cone approach remains a plausible fallback.
    - For the next attempt, prefer a full-sky Gaia `G <= 15` skinny field
      download because the pipeline-shaped count was `36,635,159` rows, lower
      than initially feared.

## Release Artifacts Created So Far

```text
publications/20260515.1/
  README.md
  manifest.toml
  run_log.md
  evidence/
    hip_gaia_magnitude_relationship.parquet
    hip_gaia_magnitude_relationship.png
    hip_gaia_magnitude_outliers.csv
    hip_gaia_magnitude_summary.json
    hip_healpix_cone_footprint_summary.csv
    hip_healpix_neighbor_footprint_summary.csv
    hip_healpix_footprint_summary.json
```

## Artifact Checksums

```text
5b13649244920aeb19071f61f9bb0502672d39f674ae224274d89b92b3a25777  evidence/hip_gaia_magnitude_outliers.csv
b1218e2be847ab7dbd838a9f25504106ae7d91252a98a9df777565082e6506b4  evidence/hip_gaia_magnitude_relationship.parquet
7d1d10020d9da6cb637230e78f8992b80f80c9df08a32527ab48136e47301f76  evidence/hip_gaia_magnitude_relationship.png
e4764a5b931821e02653151371d758ba7c5079ac93c9bcd7e5989f12d5d75532  evidence/hip_gaia_magnitude_summary.json
fb2246d7c383bbdbcd7ba1b0c4a184273f82af661b5311ebadd51af8bf08b9aa  evidence/hip_healpix_cone_footprint_summary.csv
739403c8193441909f266444a1d0ec307a4c7af00a79fa95e07f7b1cd094c9d5  evidence/hip_healpix_footprint_summary.json
c014472f97179be106bbdd8fa78748b2444d11dbc088bf8acd84c7a665814167  evidence/hip_healpix_neighbor_footprint_summary.csv
```
