# Run Log

Release: `20260630.2`

This log records the controlled policy-neutral remake. Commands are run from
the local Found in Space meta-repository. Exact code and input hashes are
generated in `evidence/support_input_provenance.json`.

## Preconditions

- `catalogs` tooling and authored publication metadata are committed and pushed.
- The `catalogs` worktree is clean.
- Pipeline commit:
  `3e64bfe97038b4f62395601a2ccc6bca7ad44556`.
- The existing compact Gaia `G <= 15` Parquet table is reused.
- The 137 GB Gaia VOTable conversion is not repeated.

## Validation before regeneration

```bash
cd catalogs
uv run pytest
```

## Pairing-evidence generation

```bash
cd catalogs
uv run --group audit fis-catalogs audit raw-match \
  --hip-ecsv ../pipeline/data/catalogs/hipparcos2.ecsv \
  --gaia-parquet ../pipeline/data/processed/gaia_raw_match_g15.parquet \
  --h2bn-crossmatch ../pipeline/data/processed/gaia_hip_map.parquet \
  --hipparcos2-neighbourhood ../pipeline/data/catalogs/gaia_hipparcos2_neighbourhood.ecsv \
  --output-dir ../pipeline/data/processed/raw-gaia-hip-match \
  --max-sep-arcsec 5 \
  --batch-size 500000 \
  --workers -1 \
  --force
```

This command writes only:

- `raw_pairing_evidence.parquet`; and
- `raw_pairing_report.json`.

It does not write a supplemental map, combined map, decision, recommendation,
severity, or action field.

## Publication assembly

```bash
cd catalogs
uv run --group audit fis-catalogs audit assemble-pairing-publication \
  --release-dir publications/20260630.2 \
  --raw-output-dir ../pipeline/data/processed/raw-gaia-hip-match \
  --gaia-compact-parquet ../pipeline/data/processed/gaia_raw_match_g15.parquet \
  --gaia-summary ../pipeline/data/processed/gaia_raw_match_g15_summary.json \
  --gaia-package-dir ../pipeline/data/packages/fis-gaia-dr3-full-20260627-b4db1f05-3e64bfe97038 \
  --hip-ecsv ../pipeline/data/catalogs/hipparcos2.ecsv \
  --h2bn-ecsv ../pipeline/data/catalogs/gaia_hipparcos2_best_neighbour.ecsv \
  --h2bn-crossmatch ../pipeline/data/processed/gaia_hip_map.parquet \
  --hipparcos2-neighbourhood ../pipeline/data/catalogs/gaia_hipparcos2_neighbourhood.ecsv
```

The assembler requires the clean HEAD to be present on the configured upstream.
It validates `124,207` unique pairs, `99,525` H2BN pairs, `122,678`
local-scan pairs, and `97,996` overlaps; copies acquisition evidence; records
all support hashes; removes the obsolete supplemental product; and regenerates
`checksums.sha256`.

## Validation after regeneration

```bash
cd catalogs
uv run pytest
sha256sum --check publications/20260630.2/checksums.sha256
```

## Generated result

The observed result, exact catalogs commit, and artifact hashes are recorded in
the generated pairing report and support provenance. No Zenodo draft is
published and no DOI is reserved in this sequence.
