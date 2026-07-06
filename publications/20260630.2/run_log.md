# Run Log

Release: `20260630.2`

This log records the local controlled remake of the Gaia-Hipparcos2 visual
deduplication pairing evidence catalog.

## Environment

- Commands are shown relative to the local Found in Space meta-repo root.
- Catalogs repository: `catalogs/`
- Catalogs commit used for the raw pairing rerun:
  `18ca668756c0cec3b52bcd123fdb762988349399`
- Pipeline repository: `pipeline/`
- Pipeline commit used for the controlled Gaia acquisition:
  `3e64bfe97038b4f62395601a2ccc6bca7ad44556`
- Gaia acquisition DOI: `10.5281/zenodo.21066981`
- Local pipeline project: `pipeline/project.toml`

## Steps Executed

1. Added a reproducible Gaia raw-match table builder.

   Command shape:

   ```bash
   uv run --group audit fis-catalogs audit gaia-match-table --help
   ```

   The builder streams Gaia Archive BINARY2 VOTables, filters
   `phot_g_mean_mag <= 15`, and writes the compact columns needed by
   `audit raw-match`.

2. Built the Hipparcos-2 support input.

   ```bash
   cd pipeline
   uv run fis-pipeline hip build --project project.toml --force
   ```

   Result:

   - Raw Hipparcos rows: `117,955`
   - Processed finite-distance rows: `113,942`

3. Built the Gaia DR3 `h2bn` mapping sidecar.

   ```bash
   cd pipeline
   uv run fis-pipeline gaia-to-hip build --project project.toml --force
   ```

   Result:

   - `h2bn` rows: `99,525`
   - Output: `data/processed/gaia_hip_map.parquet`

4. Downloaded the Gaia DR3 `hipparcos2_neighbourhood` table.

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

   Result:

   - `hipparcos2_neighbourhood` rows: `100,010`
   - Output: `data/catalogs/gaia_hipparcos2_neighbourhood.ecsv`

5. Converted the controlled Gaia acquisition into a compact pairing table.

   ```bash
   cd catalogs
   uv run --group audit fis-catalogs audit gaia-match-table \
     --gaia-dir ../pipeline/data/catalogs/gaia \
     --pattern 'gaia_full_*.vot.gz' \
     --output-parquet ../pipeline/data/processed/gaia_raw_match_g15.parquet \
     --summary-json ../pipeline/data/processed/gaia_raw_match_g15_summary.json \
     --source-manifest ../pipeline/data/packages/fis-gaia-dr3-full-20260627-b4db1f05-3e64bfe97038/manifests/gaia-votables-manifest.tsv \
     --source-checksums ../pipeline/data/packages/fis-gaia-dr3-full-20260627-b4db1f05-3e64bfe97038/manifests/gaia-votables.sha256 \
     --g-mag-limit 15 \
     --batch-rows 500000 \
     --force
   ```

   Result:

   - Input files: `60`
   - Gaia rows scanned: `1,467,744,818`
   - Gaia `G <= 15` rows written: `36,635,159`
   - Output bytes: `2,038,921,186`
   - Output SHA256:
     `cb8dbc1e5db4e65584e36126b4423ed55d1c3df9f3b334f50711122411221b69`

6. Ran the raw Gaia-Hipparcos2 pairing scan.

   ```bash
   cd catalogs
   uv run --group audit fis-catalogs audit raw-match \
     --hip-ecsv ../pipeline/data/catalogs/hipparcos2.ecsv \
     --gaia-parquet ../pipeline/data/processed/gaia_raw_match_g15.parquet \
     --h2bn-crossmatch ../pipeline/data/processed/gaia_hip_map.parquet \
     --hipparcos2-neighbourhood ../pipeline/data/catalogs/gaia_hipparcos2_neighbourhood.ecsv \
     --output-dir ../pipeline/data/processed/raw-gaia-hip-match \
     --max-sep-arcsec 5 \
     --auto-sep-arcsec 0.25 \
     --max-parallax-3d-separation-pc 1 \
     --batch-size 500000 \
     --workers -1 \
     --force
   ```

   Result:

   - Runtime on the local small-machine run: `12m4s` wall, `11m49s` user,
     `0m7s` system.
   - Gaia rows scanned: `36,635,159`
   - Evidence rows: `122,678`
   - Clean supplemental crossmatch rows: `15,679`
   - Combined validation rows: `115,204`
   - `h2bn` pairs recovered in the local evidence field: `92,436`
   - Evidence category interpretation:
     - `h2bn_recovered`: `92,436`
     - `supplemental_match`: `15,679`
     - `local_ambiguity`: `7,803`
     - `h2bn_disagreement`: `5,918`
     - `hipparcos2_neighbourhood_disagreement`: `0`
     - `nearby_nonmatch`: `842`

7. Copied publishable artifacts into this publication directory.

   Clean supplemental map:

   - `catalog/fis_gaia_hip_supplemental_crossmatch_map.parquet`

   Published evidence:

   - `evidence/gaia_hip_crossmatch_evidence.parquet`
   - `evidence/gaia_hip_crossmatch_report.json`
   - `evidence/gaia_raw_match_g15_summary.json`
   - `evidence/support_input_provenance.json`
   - `evidence/gaia-votables-manifest.tsv`
   - `evidence/gaia-votables.sha256`

The local combined map was generated only for one-to-one validation and is not
included in the publication payload.
