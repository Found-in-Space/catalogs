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

11. Ran the exact skinny Gaia `G <= 15` count and downloaded the full matching
    table as a single authenticated Gaia Archive job.

    Exact skinny count query:

    ```sql
    SELECT
      (source_id / 9007199254740992) AS hp3,
      COUNT(*) AS n
    FROM gaiadr3.gaia_source
    WHERE
      phot_g_mean_mag <= 15
    GROUP BY 1
    ORDER BY n DESC
    ```

    Count result:

    - Total rows: `36,909,365`
    - HP3 rows: `768`
    - Maximum rows in one HP3 cell: `519,591`
    - Query hash:
      `48d43a314d949054579a5b2a55df8bb3081fe241d3021d4b3d57eed20b8bf465`
    - Local count table:
      `local/runs/source-20260515.1/data/catalogs/gaia-g15-match/gaia_g15_skinny_hp3_counts.csv`

    Download query:

    ```sql
    SELECT
      source_id,
      ra,
      dec,
      phot_g_mean_mag,
      phot_bp_mean_mag,
      phot_rp_mean_mag
    FROM gaiadr3.gaia_source
    WHERE
      phot_g_mean_mag <= 15
    ```

    Download result:

    - Gaia job name: `fis-gaia-g15-skinny-full-0af47fb1`
    - Gaia job ID: `bdf01b39-5109-11f1-8c53-bc97e148b76b-O`
    - Query hash:
      `0af47fb17b8ef017d638cc17f58a5a775997b4e8dc9257e546b800c7a0afef37`
    - Local output:
      `local/runs/source-20260515.1/data/catalogs/gaia-g15-match/gaia_g15_skinny_full.vot.gz`
    - Downloaded bytes: `1,309,708,009`
    - SHA-256:
      `8a34f9f7d8b392575b6fcfc993efef1f26c64ba5bbec30c97340bae27fbb9a99`
    - Gzip integrity check: passed.
    - Remote Gaia job was deleted after download.

12. Converted the skinny Gaia `G <= 15` VOTable into a local Parquet working
    table for matching.

    Conversion used `votpipe.parse_votable` to stream the gzipped VOTable into
    Arrow batches, then wrote a Zstandard-compressed Parquet file.

    Working input:

    - `local/runs/source-20260515.1/data/catalogs/gaia-g15-match/gaia_g15_skinny_full.vot.gz`

    Working outputs:

    - `local/runs/source-20260515.1/data/processed/gaia-g15-match/gaia_g15_skinny.parquet`
    - `local/runs/source-20260515.1/data/processed/gaia-g15-match/gaia_g15_skinny.summary.json`

    Conversion result:

    - Rows: `36,909,365`
    - Row groups / streamed batches: `74`
    - Elapsed time: `132.158` seconds
    - Parquet bytes: `1,303,169,438`
    - Parquet SHA-256:
      `04386c5ac024799ab18a41556c2ce96ceaf27787f3f525caec05d98280c66944`
    - Summary SHA-256:
      `a7d1a4226a9946c1c525863d688a95d2cb88bae547cc070f1ec0949ff0104d0d`
    - Verified Parquet metadata rows: `36,909,365`
    - Verified Parquet metadata row groups: `74`

    Schema:

    ```text
    source_id           uint64
    ra                  double
    dec                 double
    phot_g_mean_mag     double
    phot_bp_mean_mag    double
    phot_rp_mean_mag    double
    ```

13. Added and ran a raw Gaia-HIP sky/magnitude matching scan.

    Matching policy:

    - Use Gaia DR3 skinny rows directly:
      `source_id`, `ra`, `dec`, `phot_g_mean_mag`, `phot_bp_mean_mag`,
      `phot_rp_mean_mag`.
    - Use raw Hipparcos rows with no parallax, distance, or quality gate.
    - Propagate Hipparcos sky positions from J1991.25 to Gaia's J2016.0 epoch
      using raw `pmRA` and `pmDE`.
    - Match only on close sky position and close apparent magnitude:
      `separation <= 5.0 arcsec` and `abs(G - Hp) <= 0.5 mag`.
    - Classify clean one-to-one non-official candidates as supplemental
      mappings.
    - Keep official Gaia-HIP pairs in evidence for recall checks, but do not
      duplicate them in the supplemental mapping.
    - Send official conflicts and many-to-one / one-to-many local candidates to
      manual review.

    Implementation note:

    - The first full scan correctly failed validation with duplicate Gaia IDs in
      the supplemental map.
    - Inspection showed this was not astrophysical duplication, but a pandas
      row-coercion precision bug for 64-bit Gaia source IDs above `2^53`.
    - The matcher was fixed to materialize Gaia and HIP IDs as strings before
      mixed numeric row iteration, and the scan was regenerated.

    Command:

    ```bash
    uv run --group audit fis-catalogs audit raw-match \
      --hip-ecsv local/runs/source-20260515.1/data/catalogs/hipparcos2.ecsv \
      --gaia-parquet local/runs/source-20260515.1/data/processed/gaia-g15-match/gaia_g15_skinny.parquet \
      --official-crossmatch local/runs/source-20260515.1/data/catalogs/gaia_hip_official_gmag.ecsv \
      --output-dir local/runs/source-20260515.1/data/processed/gaia-hip-raw-match \
      --max-sep-arcsec 5.0 \
      --max-mag-delta 0.5 \
      --force
    ```

    Working outputs:

    - `local/runs/source-20260515.1/data/processed/gaia-hip-raw-match/raw_hip_match_sources.parquet`
    - `local/runs/source-20260515.1/data/processed/gaia-hip-raw-match/raw_match_evidence.parquet`
    - `local/runs/source-20260515.1/data/processed/gaia-hip-raw-match/raw_supplemental_gaia_hip_map.parquet`
    - `local/runs/source-20260515.1/data/processed/gaia-hip-raw-match/raw_combined_gaia_hip_map.parquet`
    - `local/runs/source-20260515.1/data/processed/gaia-hip-raw-match/raw_match_report.json`

    Scan result:

    - Gaia rows scanned: `36,909,365`
    - Gaia rows skipped for non-finite match fields: `0`
    - Raw HIP rows: `117,955`
    - Prepared HIP match rows: `117,955`
    - Evidence rows: `94,172`
    - Official Gaia-HIP rows: `99,525`
    - Official pairs in raw evidence: `77,571`
    - Official pairs confirmed cleanly: `77,398`
    - Supplemental one-to-one mappings: `15,984`
    - Combined map rows: `115,509`
    - Manual review evidence rows: `790`

    Decision counts:

    ```text
    official_confirmed    77,398
    supplemental_match    15,984
    manual_review            790
    ```

    Manual review split:

    ```text
    inspect_official_conflict          407
    inspect_ambiguous_raw_match        210
    inspect_ambiguous_official_pair    173
    ```

    Official recall note:

    - `21,954` official rows were not found in the broad raw evidence.
    - Of those, `21,865` had finite Gaia `G <= 15`.
    - For the finite `G <= 15` official misses, nearly all were excluded by the
      conservative `abs(G - Hp) <= 0.5` threshold:

    ```text
    abs(G - Hp) <= 0.5       3
    0.5 < abs(G - Hp) <= 1.0 19,197
    1.0 < abs(G - Hp) <= 2.0 2,487
    2.0 < abs(G - Hp) <= 5.0 155
    5.0 < abs(G - Hp) <= 10  22
    abs(G - Hp) > 10         1
    ```

    Working output checksums:

    ```text
    64ac2fd8fd87d53d3be78ac93d2c8d729e274398b5579f0433e7c979177f74d8  raw_hip_match_sources.parquet
    573ddc131a32f28f42ed5f0f77c6f9e79b6b9caf0c1df71bbbb60fe6e61bdff4  raw_match_evidence.parquet
    619ae6b01c89226f3022a9dc1cce4c396c3d0aa467d39cb36f35893f9125db2b  raw_supplemental_gaia_hip_map.parquet
    c97d44095828a8dd265d0fcb398fcf8108fdb554f5ecf9ab7280761fae130198  raw_combined_gaia_hip_map.parquet
    0bdafbc838e2df5534bb8bbbaf20774d193c4e4d93f7f95456d6bace3a637225  raw_match_report.json
    ```

14. Analysed Gaia `G` vs Hipparcos `Hp` differences in the official
    Gaia-HIP crossmatch to calibrate the magnitude gate.

    Working outputs:

    - `local/runs/source-20260515.1/data/processed/gaia-hip-raw-match/magnitude-calibration/official_g_hp_calibration.parquet`
    - `local/runs/source-20260515.1/data/processed/gaia-hip-raw-match/magnitude-calibration/official_g_hp_by_color_bin.csv`
    - `local/runs/source-20260515.1/data/processed/gaia-hip-raw-match/magnitude-calibration/official_g_hp_threshold_summary.csv`
    - `local/runs/source-20260515.1/data/processed/gaia-hip-raw-match/magnitude-calibration/official_g_hp_quantiles.csv`
    - `local/runs/source-20260515.1/data/processed/gaia-hip-raw-match/magnitude-calibration/official_g_hp_poly3_coefficients.json`
    - `local/runs/source-20260515.1/data/processed/gaia-hip-raw-match/magnitude-calibration/official_g_minus_hp_histogram.png`
    - `local/runs/source-20260515.1/data/processed/gaia-hip-raw-match/magnitude-calibration/official_g_minus_hp_vs_bp_rp.png`
    - `local/runs/source-20260515.1/data/processed/gaia-hip-raw-match/magnitude-calibration/official_g_minus_hp_color_residual_histogram.png`

    Key result:

    - The fixed `abs(G - Hp) <= 0.5` criterion is too strict and not physically
      well centred for the official Gaia-HIP relation.
    - For official rows with finite `G <= 15`, the median `G - Hp` is
      `-0.274220`.
    - The relation is strongly colour-dependent: redder stars have more
      negative `G - Hp`.

    Fixed-threshold recovery for official rows with finite `G <= 15`:

    ```text
    abs(G - Hp) <= 0.25    43,456 / 99,436  43.7%
    abs(G - Hp) <= 0.50    77,574 / 99,436  78.0%
    abs(G - Hp) <= 0.75    92,352 / 99,436  92.9%
    abs(G - Hp) <= 1.00    96,771 / 99,436  97.3%
    abs(G - Hp) <= 1.25    98,291 / 99,436  98.8%
    ```

    Colour trend examples from official rows:

    ```text
    BP-RP median    median(G-Hp)
    -0.072          -0.001
     0.116          -0.045
     0.383          -0.125
     0.636          -0.216
     0.831          -0.291
     1.160          -0.427
     1.344          -0.512
     1.610          -0.644
     1.860          -0.771
     2.179          -0.933
     2.687          -1.201
     3.333          -1.517
     4.430          -1.967
    ```

    Robust third-order colour correction fitted to official pairs:

    ```text
    c = BP - RP
    expected(G - Hp) =
      0.014335595891044701 * c^3
    - 0.11014332763057445  * c^2
    - 0.24593654992633962  * c
    - 0.020857069669247257
    ```

    In the colour-fit domain, a residual gate
    `abs((G - Hp) - expected(G - Hp)) <= 0.5` recovers `97,558` official pairs
    (`98.3%` of rows with a valid colour residual).

    Decision:

    - Do not simply keep `abs(G - Hp) <= 0.5` for the release matching scan.
    - Prefer a colour-corrected magnitude residual when Gaia `BP-RP` is finite.
    - Treat missing-colour candidates conservatively, likely as review-only
      unless also passing a broader fixed fallback gate.
    - If a simple fixed fallback is needed, `abs(G - Hp) <= 1.0` is a much more
      realistic broad gate than `0.5`, but the colour-corrected gate is better
      justified.

    Working output checksums:

    ```text
    1dca16be9d1a7f04d461807e03eb1eec9ffff2908850f259fc83ff1de14bb781  official_g_hp_calibration.parquet
    e9adff80646c5c0102d54a8097a06fa48461c301cdb9cdd67fc3e174f00a486c  official_g_hp_by_color_bin.csv
    dabe8ffffcfd06e9fd082d246f084f11b21cb7d1ce53649c3902604784cd69ac  official_g_hp_threshold_summary.csv
    9c5cac6c02ea6f3f854f79d000691479e4e8ecb30ece7290eeb20b0cfec6eeee  official_g_hp_quantiles.csv
    9140264f1bb6d93538292427aa3a4db921f86ef2bbf6230bbf1f589b3abc918a  official_g_hp_poly3_coefficients.json
    88f4d970cad04eab7ed33a37b764d74da5e7385b9d9e769dce3d24729d089496  official_g_minus_hp_histogram.png
    e87a6136e8ae54326b2fba488ec07a9c03a86f084eaf0ac8724b306c81c2477e  official_g_minus_hp_vs_bp_rp.png
    402ba4d7d10e7b194bbb2d70972178496752905a32114e9685968ff084342102  official_g_minus_hp_color_residual_histogram.png
    ```

15. Reviewed the published Gaia crossmatch methodology for the official
    `gaiadr3.hipparcos2_best_neighbour` table.

    Sources:

    - Gaia@AIP metadata for `gaiadr3.hipparcos2_best_neighbour`:
      <https://gaia.aip.de/metadata/gaiadr3/hipparcos2_best_neighbour/>
    - Gaia@AIP metadata for `gaiadr3.hipparcos2_neighbourhood`:
      <https://gaia.aip.de/metadata/gaiadr3/hipparcos2_neighbourhood/>
    - Marrese et al. 2019, "Gaia Data Release 2. Cross-match with external
      catalogues - Algorithms and results", A&A 621, A144:
      <https://doi.org/10.1051/0004-6361/201834142>

    Key methodology notes:

    - The official Hipparcos2 best-neighbour table is positional and
      non-symmetric: Hipparcos2 is treated as the sparse leading catalogue and
      Gaia as the searched catalogue.
    - The best neighbour is selected among "good neighbours" using a figure of
      merit based on the likelihood ratio of match-vs-chance hypotheses.
    - The method uses angular distance, position errors, epoch differences,
      Gaia astrometric covariance when available, and the local Gaia source
      density.
    - It is explicitly not a simple cone search.
    - For sparse catalogues such as Hipparcos2, the official method forces a
      one-to-one best match; additional good Gaia neighbours belong in the
      neighbourhood table.
    - Photometry is not part of the official best-neighbour decision. Marrese
      et al. used magnitude and colour distributions as validation diagnostics.
    - Marrese et al. noted no special binary-star treatment in the Gaia DR2
      external-catalogue crossmatch. They specifically identified Hipparcos2
      missing matches as plausibly caused by non-optimal astrometric solutions
      from multiplicity, variability, and/or peculiarities.
    - For DR2 Hipparcos2, Marrese et al. found that only about two-thirds of
      Hipparcos2 objects had a Gaia counterpart compatible within the official
      position-error criterion, and separately published a 1 arcsec cone-search
      association list because the team expected almost all Hipparcos2 sources
      to have Gaia counterparts.

    Decision impact:

    - Our supplemental catalogue should not try to reproduce the full DPAC
      figure-of-merit method unless we also bring in astrometric covariance,
      position errors, local-density scoring, and the official neighbourhood
      table.
    - For this release, our raw local scan remains a conservative supplemental
      catalogue: close sky position plus one-to-one field uniqueness are the
      primary criteria.
    - The magnitude relation should be treated as a sanity/ambiguity filter,
      not as a physical identity score that must be close to zero.
    - Next best evidence step is to fetch/use `gaiadr3.hipparcos2_neighbourhood`
      and compare our local candidates against official good-neighbour scores,
      not only against `best_neighbour`.

16. Downloaded `gaiadr3.hipparcos2_neighbourhood` and compared it with the raw
    local Gaia-HIP evidence.

    Query:

    ```sql
    SELECT
      source_id,
      original_ext_source_id,
      angular_distance,
      score,
      xm_flag
    FROM gaiadr3.hipparcos2_neighbourhood
    ```

    Working inputs:

    - Raw local evidence:
      `local/runs/source-20260515.1/data/processed/gaia-hip-raw-match/raw_match_evidence.parquet`
    - Official best-neighbour join:
      `local/runs/source-20260515.1/data/catalogs/gaia_hip_official_gmag.ecsv`

    Working outputs:

    - `local/runs/source-20260515.1/data/catalogs/gaia-hip-neighbourhood/hipparcos2_neighbourhood.adql`
    - `local/runs/source-20260515.1/data/catalogs/gaia-hip-neighbourhood/hipparcos2_neighbourhood.vot.gz`
    - `local/runs/source-20260515.1/data/catalogs/gaia-hip-neighbourhood/hipparcos2_neighbourhood_state.json`
    - `local/runs/source-20260515.1/data/processed/gaia-hip-neighbourhood/hipparcos2_neighbourhood.parquet`
    - `local/runs/source-20260515.1/data/processed/gaia-hip-neighbourhood/hipparcos2_neighbourhood.summary.json`
    - `local/runs/source-20260515.1/data/processed/gaia-hip-neighbourhood-comparison/neighbourhood_comparison_summary.json`
    - `local/runs/source-20260515.1/data/processed/gaia-hip-neighbourhood-comparison/raw_evidence_with_neighbourhood.parquet`
    - `local/runs/source-20260515.1/data/processed/gaia-hip-neighbourhood-comparison/raw_evidence_neighbourhood_by_decision.csv`
    - `local/runs/source-20260515.1/data/processed/gaia-hip-neighbourhood-comparison/manual_review_neighbourhood_by_action.csv`
    - `local/runs/source-20260515.1/data/processed/gaia-hip-neighbourhood-comparison/neighbourhood_nonbest_rows.parquet`
    - `local/runs/source-20260515.1/data/processed/gaia-hip-neighbourhood-comparison/neighbourhood_nonbest_raw_overlap.parquet`
    - `local/runs/source-20260515.1/data/processed/gaia-hip-neighbourhood-comparison/neighbourhood_nonbest_raw_overlap.csv`
    - `local/runs/source-20260515.1/data/processed/gaia-hip-neighbourhood-comparison/raw_supplemental_in_neighbourhood.csv`
    - `local/runs/source-20260515.1/data/processed/gaia-hip-neighbourhood-comparison/raw_manual_review_in_neighbourhood.csv`
    - `local/runs/source-20260515.1/data/processed/gaia-hip-neighbourhood-comparison/best_not_in_neighbourhood.parquet`

    Neighbourhood table summary:

    - Rows: `100,010`
    - Unique Gaia source IDs: `100,010`
    - Unique HIP source IDs: `99,525`
    - Duplicate Gaia-HIP pair rows: `0`
    - HIP sources with multiple official good neighbours: `483`
    - Maximum official good neighbours for one HIP source: `3`
    - Gaia source IDs linked to multiple HIP sources: `0`
    - `xm_flag` counts:

    ```text
    8     82,593
    16     1,999
    72    15,418
    ```

    Comparison with official best-neighbour rows:

    - Official best-neighbour rows in local input: `99,525`
    - Best-neighbour pairs found in neighbourhood: `99,525`
    - Best-neighbour pairs missing from neighbourhood: `0`
    - Non-best neighbourhood rows: `485`
    - Non-best neighbourhood rows also present in raw local evidence: `45`

    Comparison with raw local evidence:

    ```text
    decision             rows    in neighbourhood    best pair
    manual_review          790                 218          173
    official_confirmed  77,398              77,398       77,398
    supplemental_match  15,984                   0            0
    ```

    Manual-review split:

    ```text
    recommended_action              rows    in neighbourhood    best pair
    inspect_ambiguous_official_pair  173                 173          173
    inspect_ambiguous_raw_match      210                   0            0
    inspect_official_conflict        407                  45            0
    ```

    Separation distribution for raw supplemental candidates:

    ```text
    <= 0.10 arcsec    11,644
    <= 0.25 arcsec    14,973 cumulative
    <= 0.50 arcsec    15,752 cumulative
    <= 1.00 arcsec    15,915 cumulative
    <= 5.00 arcsec    15,984 cumulative
    ```

    Decision impact:

    - The neighbourhood table is useful for identifying a small set of official
      ambiguity/conflict cases, but it does not explain the main display
      duplicate problem.
    - None of the `15,984` clean raw supplemental candidates are official
      Hipparcos2 neighbourhood rows.
    - This means the display artefact correction is necessarily a local
      Found-In-Space policy decision rather than simply "use all official good
      neighbours".
    - Absence from neighbourhood should be recorded as a lower-confidence flag,
      not an automatic veto, because most supplemental candidates are extremely
      close on the sky at the display epoch.

    Working output checksums:

    ```text
    138b669e613e799ec9e4d10fa99b9c922a1462328e20eaff3cafdeb11b8a264a  hipparcos2_neighbourhood.adql
    c4c2d3eb353278ebf53f98e1f6a0dc3ddedf42bdb54d70565bc68da4317f51f5  hipparcos2_neighbourhood_state.json
    f69efb2e069d08929ea416e7d9a6467055ba107f1820e4c4a53511785dc5e8cf  hipparcos2_neighbourhood.vot.gz
    94db42c15c951adafdeedbdc5597de297335ac742d47201b3765e27d06dc4681  hipparcos2_neighbourhood.parquet
    6fc97c06ad8266180cacadf0b7f7f831a9101e1d5118e1c199777768d1003e83  hipparcos2_neighbourhood.summary.json
    4599c0b2f9ba8ec1e14acca3ed691bdfcae926453402e3a9210e603b90dbef9b  neighbourhood_comparison_summary.json
    7ea474fe240f323b8ef176f9e4b19e818b431a36e0422d183300f3e943c58f25  raw_evidence_neighbourhood_by_decision.csv
    5956f5434c29b6a97f1f56ef8b093421cce042f4173f947ecb60a706030ecb39  manual_review_neighbourhood_by_action.csv
    d05c16cba44c97a01a33fc74f93286a7ea1d12eeabb7345d0cf11416e58fa6b5  neighbourhood_nonbest_raw_overlap.csv
    ```

17. Consolidated methodology and assumption audit for using the official Gaia
    Hipparcos2 crossmatch tables.

    Purpose:

    - Document what the official Gaia/Hipparcos2 crossmatch tables claim to
      represent.
    - State the assumptions this publication makes about those tables.
    - Record the local data checks used to validate those assumptions before
      deriving a Found-In-Space supplemental display de-duplication catalogue.

    Literature and table documentation reviewed:

    - Marrese et al. 2017, Gaia DR1 crossmatch paper, for the original
      definitions of `BestNeighbour` and `Neighbourhood`.
    - Marrese et al. 2019, Gaia DR2 crossmatch paper, for the updated Gaia
      external-catalogue crossmatch algorithm and the specific Hipparcos2
      discussion.
    - Gaia DR3 table metadata for:
      - `gaiadr3.hipparcos2_best_neighbour`
      - `gaiadr3.hipparcos2_neighbourhood`

    Summary of the official method:

    - Hipparcos2 is treated as a sparse external catalogue.
    - For sparse catalogues, the external catalogue is the leading catalogue
      and Gaia is searched for counterparts.
    - The official match is not symmetric.
    - The algorithm is positional/astrometric, not photometric.
    - A "good neighbour" is a nearby Gaia source whose position is compatible
      with the Hipparcos2 target within the relevant position-error model.
    - The method uses angular distance, position errors, epoch differences,
      Gaia astrometric covariance where available, external-catalogue position
      errors, and local Gaia source density.
    - The best neighbour is chosen from the good neighbours using a score /
      figure of merit based on match-vs-chance hypotheses.
    - The method is explicitly not equivalent to a simple cone search.
    - For sparse catalogues, a one-to-one best match is forced.
    - Additional good Gaia neighbours, when present, are represented in the
      neighbourhood table rather than the best-neighbour table.
    - The Gaia crossmatch papers use magnitudes and colours for validation and
      diagnostics, not as the primary best-neighbour decision rule.
    - Marrese et al. explicitly identify Hipparcos2 as difficult: missing
      official matches are plausibly linked to non-optimal astrometric
      solutions caused by multiplicity, variability, and/or peculiar sources.
    - Marrese et al. also published a separate 1 arcsec Hipparcos2 cone-search
      association list for DR2 because they expected almost all Hipparcos2
      sources to have Gaia counterparts, even when the official
      position-error compatibility criterion did not accept them.

    Assumptions made for this Found-In-Space publication:

    - `source_id` in the official tables is the Gaia source identifier.
    - `original_ext_source_id` in the official tables is the Hipparcos2/HIP
      identifier.
    - `angular_distance` is in arcsec.
    - `hipparcos2_best_neighbour` is the official winning one-to-one mapping
      table for matched Hipparcos2 sources.
    - `hipparcos2_neighbourhood` contains all official good-neighbour candidates
      for matched Hipparcos2 sources, including the best-neighbour row.
    - For any given HIP source, `score` is useful for official-neighbour
      ranking, but we do not assume that scores are globally comparable across
      unrelated HIP sources.
    - A local Gaia-HIP pair absent from `hipparcos2_neighbourhood` was not
      accepted as an official DPAC good neighbour under the published
      positional/covariance/local-density method.
    - Absence from `hipparcos2_neighbourhood` is therefore a confidence caveat,
      but not a display-policy veto: our target problem is visible duplicate
      artefacts after rendering, not a claim to supersede DPAC astrometry.
    - Gaia/Hipparcos magnitude agreement should be a sanity or ambiguity
      feature. It should not be treated as the core identity rule because the
      official method is not photometric and because `G - Hp` is strongly
      colour-dependent.

    Local assertions performed against the downloaded official data:

    - Downloaded an official best-neighbour plus Gaia photometry join from
      Gaia Archive:
      - rows: `99,525`
      - finite Gaia `G`: `99,463`
    - Downloaded `gaiadr3.hipparcos2_neighbourhood`:
      - rows: `100,010`
      - unique Gaia source IDs: `100,010`
      - unique HIP source IDs: `99,525`
      - duplicate Gaia-HIP pair rows: `0`
      - HIP sources with multiple official good neighbours: `483`
      - maximum official good neighbours for one HIP source: `3`
      - Gaia source IDs linked to multiple HIP sources: `0`
    - Confirmed every downloaded best-neighbour pair is present in
      `hipparcos2_neighbourhood`:
      - best rows checked: `99,525`
      - best rows found in neighbourhood: `99,525`
      - best rows missing from neighbourhood: `0`
    - Confirmed the neighbourhood table adds only a small number of non-best
      official good-neighbour rows:
      - non-best neighbourhood rows: `485`
      - non-best neighbourhood rows also found by our raw local evidence scan:
        `45`
    - Confirmed our raw local evidence correctly recovers official winners when
      they pass our sky/magnitude scan:

    ```text
    decision             rows    in neighbourhood    best pair
    official_confirmed  77,398              77,398       77,398
    manual_review          790                 218          173
    supplemental_match  15,984                   0            0
    ```

    - Confirmed no clean raw supplemental candidate is an official
      neighbourhood row:
      - supplemental candidates: `15,984`
      - supplemental candidates in neighbourhood: `0`
    - Confirmed the conservative raw supplemental candidates are mostly far
      below visual separability:

    ```text
    <= 0.10 arcsec    11,644
    <= 0.25 arcsec    14,973 cumulative
    <= 0.50 arcsec    15,752 cumulative
    <= 1.00 arcsec    15,915 cumulative
    <= 5.00 arcsec    15,984 cumulative
    ```

    - Calibrated Gaia `G` against Hipparcos `Hp` using the official
      best-neighbour pairs and confirmed that a naive `abs(G - Hp) <= 0.5`
      threshold is not an appropriate reproduction of official matching:
      - median `G - Hp` for official finite `G <= 15` rows: `-0.274220`
      - `abs(G - Hp) <= 0.5` recovers only `78.0%` of official finite
        `G <= 15` rows
      - `abs(G - Hp) <= 1.0` recovers `97.3%`
      - a colour-corrected residual gate better represents the official
        passband relationship

    Conclusion:

    - The official Gaia Hipparcos2 crossmatch tables are internally consistent
      with the assumptions above.
    - The official neighbourhood table is useful as an ambiguity/conflict flag,
      but it cannot solve the main Found-In-Space visible duplicate problem:
      none of the clean local supplemental candidates are official
      neighbourhood rows.
    - The Found-In-Space supplemental mapping should therefore be documented as
      a display de-duplication policy catalogue derived from local sky
      proximity, one-to-one candidate uniqueness, and magnitude sanity checks.
    - It should not be described as a replacement for, or correction to, the
      DPAC scientific crossmatch.

18. Ran a proximity-only diagnostic to decide whether the supplemental display
    de-duplication policy needs a magnitude gate.

    Purpose:

    - Determine how many Gaia-HIP candidate pairs appear when the raw local
      scan uses sky proximity only.
    - Separate official best-neighbour recovery from non-official supplemental
      display candidates.
    - Decide whether magnitude should be a hard gate, a sanity flag, or omitted
      from automatic policy.

    Working outputs:

    - `local/runs/source-20260515.1/data/processed/gaia-hip-proximity-diagnostic/proximity_pairs_5arcsec.parquet`
    - `local/runs/source-20260515.1/data/processed/gaia-hip-proximity-diagnostic/proximity_threshold_summary.csv`
    - `local/runs/source-20260515.1/data/processed/gaia-hip-proximity-diagnostic/proximity_official_adjusted_summary.csv`
    - `local/runs/source-20260515.1/data/processed/gaia-hip-proximity-diagnostic/proximity_diagnostic_summary.json`
    - `local/runs/source-20260515.1/data/processed/gaia-hip-proximity-diagnostic/proximity_one_to_one_5arcsec.csv`

    Full proximity-only scan result:

    - Gaia rows scanned: `36,909,365`
    - HIP rows scanned: `117,955`
    - Gaia-HIP pairs within `5 arcsec`: `126,220`
    - Unique Gaia IDs in proximity pairs: `126,220`
    - Unique HIP IDs in proximity pairs: `117,837`
    - One-to-one sky pairs within `5 arcsec`: `109,549`
    - Isolated sky pairs within `5 arcsec`: `109,549`

    One-to-one sky pairs after removing official best-neighbour pairs:

    ```text
    sep <= 0.05 arcsec     7,634 non-official pairs
    sep <= 0.10 arcsec    12,428 non-official pairs
    sep <= 0.25 arcsec    15,803 non-official pairs
    sep <= 0.50 arcsec    16,639 non-official pairs
    sep <= 1.00 arcsec    16,829 non-official pairs
    sep <= 2.00 arcsec    16,879 non-official pairs
    sep <= 5.00 arcsec    16,929 non-official pairs
    ```

    For these non-official one-to-one sky pairs, none are official
    neighbourhood rows at any tested threshold.

    Effect of simple `abs(G - Hp)` gates on non-official one-to-one sky pairs:

    ```text
    sep <= 0.25 arcsec:
      total non-official one-to-one      15,803
      abs(G-Hp) <= 0.5                  13,918
      abs(G-Hp) <= 0.75                 15,331
      abs(G-Hp) <= 1.0                  15,637

    sep <= 5.00 arcsec:
      total non-official one-to-one      16,929
      abs(G-Hp) <= 0.5                  14,829
      abs(G-Hp) <= 0.75                 16,364
      abs(G-Hp) <= 1.0                  16,729
    ```

    Effect of colour-corrected residual gates on non-official one-to-one sky
    pairs:

    ```text
    sep <= 0.25 arcsec:
      rows with finite colour residual   15,783
      abs(residual) <= 0.25              15,366
      abs(residual) <= 0.5               15,658
      abs(residual) <= 0.75              15,775

    sep <= 5.00 arcsec:
      rows with finite colour residual   16,909
      abs(residual) <= 0.25              16,358
      abs(residual) <= 0.5               16,710
      abs(residual) <= 0.75              16,882
    ```

    Decision:

    - A strict raw `abs(G - Hp) <= 0.5` gate is too aggressive for display
      de-duplication. It removes about `1,885` otherwise clean non-official
      one-to-one pairs at `0.25 arcsec`, and about `2,100` at `5 arcsec`.
    - Proximity and one-to-one sky uniqueness are the primary display
      de-duplication evidence.
    - Magnitude should remain in the evidence table and should be used as a
      review/sanity signal, preferably as a colour-corrected residual.
    - For automatic supplemental mapping, the likely policy is:
      - allow very tight one-to-one sky pairs without a hard raw magnitude gate;
      - flag large raw `G-Hp` differences, missing colour, and large
        colour-corrected residuals for review or lower confidence;
      - use a broader raw fallback such as `abs(G-Hp) <= 1.0` only when colour
        is unavailable and the pair is not extremely tight.

    Working output checksums:

    ```text
    2d1dbce90e8bef080627d876d5b25a0a5885c8805b6caa645c522793cc6db689  proximity_pairs_5arcsec.parquet
    cbceadddf0bc21c8d65d1b59771c56a40af73d59ec8d74f7e0dd16d130627c6f  proximity_threshold_summary.csv
    222fc79f321e1695f4ad39ce7c501d5b04fdf83c4b65a7fcb0613fda8f481e8b  proximity_official_adjusted_summary.csv
    7b9dc7b97a340d0790b71605572e82408d5e3bd721cb743d748bc12760b20477  proximity_diagnostic_summary.json
    ```

19. Finalised the current display de-duplication decision lines from the
    gathered evidence.

    Problem restatement:

    - The target problem is visible Gaia/Hipparcos duplicate artefacts in
      rendered sky views.
    - The target output is a deterministic display de-duplication mapping.
    - This is not a claim that the supplemental mapping is a scientifically
      superior replacement for the DPAC Gaia/Hipparcos2 crossmatch.
    - The policy should avoid subjective visual judgement and should be
      explainable entirely from measured catalogue fields and rendering-risk
      thresholds.

    Evidence used:

    - Official `hipparcos2_best_neighbour` is internally consistent and should
      remain the baseline mapping.
    - Official `hipparcos2_neighbourhood` does not explain the local display
      duplicates:
      - clean raw supplemental candidates in neighbourhood: `0 / 15,984`
    - Most non-official one-to-one proximity candidates are extremely close:
      - `15,803` non-official one-to-one pairs within `0.25 arcsec`
      - `16,929` non-official one-to-one pairs within `5 arcsec`
    - Raw `abs(G-Hp)` is not a suitable hard decision gate:
      - it is not part of the official matching method;
      - it is colour-dependent;
      - `abs(G-Hp) <= 0.5` removes about `1,885` otherwise clean
        non-official one-to-one pairs at `0.25 arcsec`.
    - A colour-corrected magnitude residual is useful as evidence, but does not
      materially change the candidate set:
      - at `0.25 arcsec`, `abs(residual) <= 0.5` keeps
        `15,658 / 15,783` rows with finite colour residual;
      - at `5 arcsec`, `abs(residual) <= 0.5` keeps
        `16,710 / 16,909` rows with finite colour residual.

    Current deterministic policy:

    1. Official best-neighbour pairs:
       - include as the baseline Gaia-HIP mapping.

    2. Non-official local Gaia-HIP pairs:
       - require one-to-one sky uniqueness;
       - require no official best-neighbour conflict;
       - require no official neighbourhood conflict.

    3. Automatic supplemental display merge:
       - if sky separation `<= 0.25 arcsec`, merge for display;
       - otherwise, if `0.25 < sky separation <= 5 arcsec`, merge for display
         only when rendered 3D separation is `<= 1 pc`.

    4. Leave both stars visible:
       - if `0.25 < sky separation <= 5 arcsec` and rendered 3D separation is
         `> 1 pc`;
       - if the local field is ambiguous;
       - if the pair conflicts with an official best-neighbour or official
         neighbourhood candidate.

    5. Magnitude and colour:
       - do not use raw `abs(G-Hp)` as a hard gate;
       - do not use colour-corrected residual as a hard gate in the current
         policy;
       - retain raw magnitude delta, `BP-RP`, expected `G-Hp`, and
         colour-corrected residual in evidence/report outputs for audit and
         future diagnostics.

    6. Diagnostic outputs:
       - emit rows that are close on sky but not merged, with explicit reason
         codes such as:
         - `ambiguous_local_field`
         - `official_best_conflict`
         - `official_neighbourhood_conflict`
         - `rendered_3d_separation_gt_1pc`
         - `missing_rendered_distance`
       - these diagnostics are not a subjective manual merge queue; they are a
         trace of deterministic non-merge decisions and potential future
         external-evidence work.

    Remaining implementation requirement at this point:

    - The final supplemental catalogue generation needs to compute
      `rendered_3d_separation_pc` for proximity candidates.
    - The source evidence currently available for this release already contains
      the sky-proximity, official-table, and magnitude/colour diagnostics needed
      for the rest of the policy.
    - Steps 20-22 below resolve the distance-evidence gap with a narrow
      Gaia root-table parallax download rather than a full Gaia pipeline field
      download.

20. Reran the full-sky Gaia `G <= 15` matching download with only root-table
    parallax fields added.

    Reason:

    - The previous `gaia_g15_skinny` download had the fields needed for sky
      proximity and magnitude/colour diagnostics, but not distance evidence:
      `source_id`, `ra`, `dec`, `phot_g_mean_mag`, `phot_bp_mean_mag`,
      `phot_rp_mean_mag`.
    - For display de-duplication we only need an approximate rendered-distance
      comparison, so Gaia root-table `parallax` is sufficient evidence.
    - `parallax_error` is included to allow later quality checks and to flag
      cases where the parallax-derived distance is unreliable.
    - No external distance or astrophysical-parameter joins were used.

    Query:

    ```sql
    SELECT
      source_id,
      ra,
      dec,
      phot_g_mean_mag,
      phot_bp_mean_mag,
      phot_rp_mean_mag,
      parallax,
      parallax_error
    FROM gaiadr3.gaia_source
    WHERE
      phot_g_mean_mag <= 15
    ```

    Result:

    - Expected rows from the previous identical-`WHERE` count:
      `36,909,365`
    - Gaia job name: `fis-gaia-g15-parallax-52b3939a`
    - Gaia job ID: `e6117c1e-512c-11f1-8c53-bc97e148b76b-O`
    - Query hash:
      `52b3939a5d3f00f88f38799446d83356ab9f69bf5bdaaf654c598337ee33f25c`
    - Local query:
      `local/runs/source-20260515.1/data/catalogs/gaia-g15-parallax-match/gaia_g15_parallax_full.adql`
    - Local output:
      `local/runs/source-20260515.1/data/catalogs/gaia-g15-parallax-match/gaia_g15_parallax_full.vot.gz`
    - Downloaded bytes: `1,778,025,432`
    - Gzip integrity check: passed.
    - Remote Gaia job was deleted after download.

    Checksums:

    ```text
    b38b3a83633027546a0f8d9a4e5d1a0c674189b7d9ca1e507857def1dec7540b  gaia_g15_parallax_full.adql
    cec2c725469671d6745f0f21f335b2899092e5d560bd0c99d12a6464d232e9f7  gaia_g15_parallax_full.vot.gz
    5061c7c32e8723cc8b01b2fb5e14a317d7c847e81ef8c5a2b26735563e60c0de  gaia_g15_parallax_full_state.json
    ```

21. Converted the Gaia `G <= 15` parallax VOTable into a raw Parquet working
    table.

    Purpose:

    - Preserve the raw Gaia fields needed by the display de-duplication
      matcher:
      `source_id`, `ra`, `dec`, `phot_g_mean_mag`, `phot_bp_mean_mag`,
      `phot_rp_mean_mag`, `parallax`, `parallax_error`.
    - Avoid running the full Gaia pipeline transform for this catalogue
      evidence step; the matcher needs candidate evidence, not dense star
      output.

    Conversion result:

    - Input:
      `local/runs/source-20260515.1/data/catalogs/gaia-g15-parallax-match/gaia_g15_parallax_full.vot.gz`
    - Output:
      `local/runs/source-20260515.1/data/processed/gaia-g15-parallax-match/gaia_g15_parallax.parquet`
    - Summary:
      `local/runs/source-20260515.1/data/processed/gaia-g15-parallax-match/gaia_g15_parallax.summary.json`
    - Rows: `36,909,365`
    - Streamed batches: `74`
    - Batch size: `500,000`
    - Elapsed time: `163.615` seconds
    - Parquet bytes: `1,772,003,171`

    Checksums:

    ```text
    f0085a618b7915b1ab9f98e240db90a17c5be519cd21cafa53c630afd49063f0  gaia_g15_parallax.parquet
    aef5ed119449bd3c14cc0abaf53ef931759c4db4f8d4687b1191dcc551f5e548  gaia_g15_parallax.summary.json
    ```

22. Updated and reran the raw Gaia-HIP display matching scan with parallax
    distance evidence.

    Implementation change:

    - The raw matcher now treats raw magnitude difference as evidence rather
      than a hard default gate.
    - The matcher records Gaia and HIP parallax-derived distances, parallax
      fractional errors, and rendered 3D separation in parsecs.
    - Automatic supplemental display matches use the deterministic policy from
      step 19:
      - one-to-one local sky candidate;
      - no official best-neighbour conflict;
      - no official neighbourhood conflict;
      - sky separation `<= 0.25 arcsec`, or rendered 3D separation `<= 1 pc`.
    - Pairs outside the display rule are retained in evidence as deterministic
      `display_separate` diagnostics rather than subjective manual overrides.

    Command:

    ```bash
    uv run --group audit fis-catalogs audit raw-match \
      --hip-ecsv local/runs/source-20260515.1/data/catalogs/hipparcos2.ecsv \
      --gaia-parquet local/runs/source-20260515.1/data/processed/gaia-g15-parallax-match/gaia_g15_parallax.parquet \
      --official-crossmatch local/runs/source-20260515.1/data/catalogs/gaia_hip_official_gmag.ecsv \
      --official-neighbourhood local/runs/source-20260515.1/data/processed/gaia-hip-neighbourhood/hipparcos2_neighbourhood.parquet \
      --output-dir local/runs/source-20260515.1/data/processed/gaia-hip-raw-match-parallax \
      --max-sep-arcsec 5.0 \
      --auto-sep-arcsec 0.25 \
      --max-rendered-separation-pc 1.0 \
      --batch-size 500000 \
      --workers -1 \
      --force
    ```

    Outputs:

    - `local/runs/source-20260515.1/data/processed/gaia-hip-raw-match-parallax/raw_hip_match_sources.parquet`
    - `local/runs/source-20260515.1/data/processed/gaia-hip-raw-match-parallax/raw_match_evidence.parquet`
    - `local/runs/source-20260515.1/data/processed/gaia-hip-raw-match-parallax/raw_supplemental_gaia_hip_map.parquet`
    - `local/runs/source-20260515.1/data/processed/gaia-hip-raw-match-parallax/raw_combined_gaia_hip_map.parquet`
    - `local/runs/source-20260515.1/data/processed/gaia-hip-raw-match-parallax/raw_match_report.json`

    Scan result:

    - Gaia rows scanned: `36,909,365`
    - Gaia rows skipped: `0`
    - HIP rows prepared: `117,955`
    - Evidence pairs within `5 arcsec`: `126,220`
    - Supplemental display matches: `15,916`
    - Combined official plus supplemental rows: `115,441`
    - Official rows: `99,525`
    - Official neighbourhood rows: `100,010`
    - Official pairs found in evidence: `99,430`
    - Official pairs confirmed without local ambiguity: `92,620`

    Decision counts:

    ```text
    official_confirmed    92,620
    manual_review         16,753
    supplemental_match    15,916
    display_separate         931
    ```

    Supplemental match split:

    ```text
    tight sky separation <= 0.25 arcsec          15,725
    non-tight rendered 3D separation <= 1 pc        191
    ```

    Non-merged display diagnostics:

    ```text
    display_separate rows                         931
    finite rendered 3D separation                 739
    missing rendered 3D separation                192
    ```

    Supplemental apparent-magnitude evidence:

    ```text
    median abs(G-Hp)       0.244000
    90th percentile        0.531337
    95th percentile        0.655862
    99th percentile        1.010475
    max                    2.586314
    abs(G-Hp) > 0.5        1,917 rows
    abs(G-Hp) > 1.0          166 rows
    ```

    One-to-one validation:

    - Supplemental map rows: `15,916`
    - Supplemental unique Gaia IDs: `15,916`
    - Supplemental unique HIP IDs: `15,916`
    - Combined map rows: `115,441`
    - Combined unique Gaia IDs: `115,441`
    - Combined unique HIP IDs: `115,441`
    - Supplemental `mapping_source`: `fis_raw_sky_render_v1`

    Checksums:

    ```text
    64ac2fd8fd87d53d3be78ac93d2c8d729e274398b5579f0433e7c979177f74d8  raw_hip_match_sources.parquet
    1a39dc68bdf9639db6a8bf240387e8aa125a632a7bf34fe7e07b6ffeb3bbef35  raw_match_evidence.parquet
    576c47cf715d6649ccf6fcbfa4f277d76d4399d7227cfb31297778bc6b82e7ad  raw_supplemental_gaia_hip_map.parquet
    dee4d88b0f5f42bb903cdf3680063daa50ba3d1d686f29d5f9472f9488caaff2  raw_combined_gaia_hip_map.parquet
    1f5b85ccfc08ee1a7e68ebfe89e9558c242fc6a7aec1a9cd2b349f9042b2cd04  raw_match_report.json
    ```

    Verification:

    ```text
    uv run --group audit pytest -q        -> 9 passed
    uv run --with ruff ruff check .       -> All checks passed
    ```

23. Prepared the publishable release artifact set.

    Decision:

    - Publish the Found-In-Space supplemental display map only.
    - Do not publish the local combined official-plus-supplemental map. That
      file is a build-convenience and validation artifact, and publishing it
      would amount to republishing the official Gaia best-neighbour table with
      our delta appended.
    - Downstream builds should compose the official Gaia
      `hipparcos2_best_neighbour` map with this supplemental map at build time.

    Published catalog artifact:

    - `catalog/fis_gaia_hip_supplemental_display_map.parquet`
      - rows: `15,916`
      - bytes: `241,298`
      - SHA-256:
        `576c47cf715d6649ccf6fcbfa4f277d76d4399d7227cfb31297778bc6b82e7ad`

    Published evidence artifacts added in this step:

    ```text
    evidence/gaia_hip_display_match_evidence.parquet
    evidence/gaia_hip_display_match_report.json
    evidence/gaia_g15_parallax_download.adql
    evidence/gaia_g15_parallax_download_state.json
    evidence/gaia_g15_parallax_conversion_summary.json
    ```

    Checksums for the added evidence artifacts:

    ```text
    1a39dc68bdf9639db6a8bf240387e8aa125a632a7bf34fe7e07b6ffeb3bbef35  evidence/gaia_hip_display_match_evidence.parquet
    1f5b85ccfc08ee1a7e68ebfe89e9558c242fc6a7aec1a9cd2b349f9042b2cd04  evidence/gaia_hip_display_match_report.json
    b38b3a83633027546a0f8d9a4e5d1a0c674189b7d9ca1e507857def1dec7540b  evidence/gaia_g15_parallax_download.adql
    5061c7c32e8723cc8b01b2fb5e14a317d7c847e81ef8c5a2b26735563e60c0de  evidence/gaia_g15_parallax_download_state.json
    aef5ed119449bd3c14cc0abaf53ef931759c4db4f8d4687b1191dcc551f5e548  evidence/gaia_g15_parallax_conversion_summary.json
    ```

24. Added explicit licensing and upstream publication notices.

    Decision:

    - Treat this publication as an academic public-interest data work.
    - Release Found-in-Space original material in the publication under
      CC BY 4.0.
    - Preserve upstream source terms and credit requirements for Gaia,
      Hipparcos/Tycho, VizieR/CDS, and source-derived evidence.
    - Add explicit references to the scientific publications that underpin the
      source catalogues and crossmatch methodology.

    Added files:

    ```text
    LICENSE.txt
    NOTICE.md
    ```

    Root repository licensing was also clarified:

    - repository software and Found-in-Space-authored maintenance docs:
      MIT License;
    - catalog publications:
      publication-specific license and notice files;
    - upstream-derived evidence:
      upstream terms apply.

## Release Artifacts Created So Far

```text
publications/20260515.1/
  LICENSE.txt
  NOTICE.md
  README.md
  checksums.sha256
  manifest.toml
  run_log.md
  catalog/
    fis_gaia_hip_supplemental_display_map.parquet
  evidence/
    gaia_g15_parallax_conversion_summary.json
    gaia_g15_parallax_download.adql
    gaia_g15_parallax_download_state.json
    gaia_hip_display_match_evidence.parquet
    gaia_hip_display_match_report.json
    hip_gaia_magnitude_relationship.parquet
    hip_gaia_magnitude_relationship.png
    hip_gaia_magnitude_outliers.csv
    hip_gaia_magnitude_summary.json
    hip_healpix_cone_footprint_summary.csv
    hip_healpix_neighbor_footprint_summary.csv
    hip_healpix_footprint_summary.json
```

## Artifact Checksums

The complete generated checksum record for the publication is
`checksums.sha256`.
