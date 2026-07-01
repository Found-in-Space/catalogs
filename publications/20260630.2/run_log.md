# Run Log

Release: `20260630.2`

This log records the local controlled remake of the Gaia-HIP supplemental
crossmatch catalog.

## Environment

- Meta-repo working directory: `/home/kws/work/fis`
- Catalogs repository: `/home/kws/work/fis/catalogs`
- Pipeline repository: `/home/kws/work/fis/pipeline`
- Pipeline commit used for the controlled Gaia acquisition:
  `3e64bfe97038b4f62395601a2ccc6bca7ad44556`
- Gaia acquisition DOI: `10.5281/zenodo.21066981`
- Local pipeline project: `/home/kws/work/fis/pipeline/project.toml`

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
   cd /home/kws/work/fis/pipeline
   uv run fis-pipeline hip build --project project.toml --force
   ```

   Result:

   - Raw Hipparcos rows: `117,955`
   - Processed finite-distance rows: `113,942`

3. Built the Gaia DR3 `h2bn` sidecar.

   ```bash
   cd /home/kws/work/fis/pipeline
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

5. Converted the controlled Gaia acquisition into a compact raw-match table.

   ```bash
   cd /home/kws/work/fis/catalogs
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

6. Ran raw Gaia-HIP crossmatching.

   ```bash
   cd /home/kws/work/fis/catalogs
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

   - Gaia rows scanned: `36,635,159`
   - Evidence rows: `122,678`
   - Supplemental crossmatch rows: `15,679`
   - Combined validation rows: `115,204`
   - `h2bn` pairs recovered in the local evidence field: `92,436`
   - Decision counts:
     - `h2bn_recovered`: `92,436`
     - `supplemental_match`: `15,679`
     - `manual_review`: `13,721`
     - `separate_object`: `842`

7. Copied publishable artifacts into this publication directory.

   Published catalog:

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
