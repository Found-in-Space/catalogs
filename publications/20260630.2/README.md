# Gaia–Hipparcos Pairing Evidence

Release: `20260630.2`
Status: draft; no DOI has been reserved

This publication records possible Gaia DR3–Hipparcos pairings for later
Found in Space pipeline policy. It does not decide that two rows are the same
star, choose a preferred source, remove a row, or construct a merged record.

The evidence is intended to support investigation of visually distracting
radial pairings in 3D star fields. A close angular pairing can still place its
Gaia and Hipparcos rows several parsecs apart when the catalogued distances
disagree. The publication measures that situation but deliberately does not
define a visual-gap threshold or prescribe what the pipeline should do.

## Pair population

The single Parquet product is the deduplicated union of:

- every row in Gaia DR3 `hipparcos2_best_neighbour` (H2BN); and
- every Gaia–Hipparcos pair in the existing local scan, using the controlled
  compact Gaia `G <= 15` table and a `5 arcsec` angular search radius.

`h2bn_pair` and `local_scan_pair` are independent flags. H2BN is retained as
authoritative crossmatch context, including rows outside the compact Gaia
scope, but H2BN membership is not treated here as a duplicate-identity or
merge decision.

With the controlled inputs, the required counts are:

- unique union: `124,207`;
- H2BN pairs: `99,525`;
- local-scan pairs: `122,678`;
- pairs present in both: `97,996`;
- H2BN-only pairs: `1,529`;
- local-only pairs: `24,682`.

The generated report and support provenance are the authoritative records of
the observed counts.

## Measurements

The evidence records factual catalog values and derived comparisons:

- Gaia G and Hipparcos Hp apparent magnitudes;
- signed `gaia_g_minus_hip_hp_mag` and its absolute value;
- Gaia and Hipparcos distances, `radial_gap_pc`, combined distance
  uncertainty, `radial_gap_sigma`, and parallax-derived 3D separation;
- local candidate and sky-neighbour counts plus one-to-one topology;
- H2BN membership, H2BN conflicts, and Hipparcos2 neighbourhood context;
- available parallax, uncertainty, BP/RP, proper-motion, and solution-type
  fields.

The sign convention is Gaia G minus Hipparcos Hp. These are different passbands,
so the difference is context rather than a same-band photometric residual.
Absolute magnitude is intentionally absent: it already incorporates the
distance estimate whose disagreement is being examined.

The report bins radial gaps as `<=1`, `1–3`, `3–5`, `5–10`, and `>10 pc`, and
absolute apparent-magnitude differences as `<=0.5`, `0.5–1`, `1–2`, and
`>2 mag`. The bins are descriptive only.

## Files

- `evidence/gaia_hip_pairing_evidence.parquet` — the single pairing-evidence
  data product.
- `evidence/gaia_hip_pairing_report.json` — source, union, missing-value,
  topology, context, and descriptive-bin counts.
- `evidence/support_input_provenance.json` — exact code SHA, support-input
  hashes, acquisition parameters, observed counts, and artifact hashes.
- `evidence/gaia_raw_match_g15_summary.json` — compact Gaia-table build
  summary.
- `evidence/gaia-*` — selected controlled Gaia acquisition evidence.
- `manifest.toml`, `run_log.md`, `checksums.sha256`, `PAPER.md`,
  `LICENSE.txt`, `NOTICE.md`, and `REFERENCES.md` — publication metadata.

There is no supplemental or combined Gaia–Hipparcos map in this release.
The 137 GB Gaia VOTable payload and the 2 GB compact Gaia table are support
inputs, not publication payloads.

## Downstream boundary

Pipeline policy must separately decide whether a possible pair is accepted,
whether either source wins, whether fields are fused, and whether an override
is needed. That later policy can use radial separation, uncertainty, apparent
magnitude, visibility scale, astrometric quality, and named-star safeguards.
No such recommendation is encoded in this publication.

## Reproduction

The controlled rerun reuses the existing compact Gaia table; it does not repeat
the full VOTable conversion:

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

After the tooling and authored metadata commit is public and the catalogs
worktree is clean, `audit assemble-pairing-publication` validates and copies
the results. The exact command is recorded in `run_log.md`.

## Licence and credit

Found in Space original prose, organization, and added evidence-table
selection/arrangement are released under CC BY 4.0. Gaia, ESA,
Hipparcos/Tycho, CDS/VizieR, and cited-source terms and attribution requirements
continue to apply to upstream data. See `LICENSE.txt`, `NOTICE.md`, and
`REFERENCES.md`.
