# Gaia-HIP Supplemental Crossmatch Catalog For Controlled Core Dataset

Release: `20260630.2`

## Abstract

This release regenerates the Found in Space supplemental Gaia-Hipparcos2
crossmatch catalog from the controlled Gaia DR3 acquisition published as DOI
`10.5281/zenodo.21066981`.

The source table `gaiadr3.hipparcos2_best_neighbour` is abbreviated as `h2bn`.

## Method

The controlled Gaia VOTable payload was streamed into a compact local Parquet
table containing only rows with `phot_g_mean_mag <= 15` and the fields needed
for raw crossmatching:

```text
source_id, ra, dec, phot_g_mean_mag, phot_bp_mean_mag, phot_rp_mean_mag,
parallax, parallax_error
```

Hipparcos-2 positions were propagated from epoch J1991.25 to Gaia epoch J2016.0
using proper motion. Gaia sources were scanned against the propagated HIP sky
positions within `5 arcsec`. The evidence table records sky separation,
apparent-magnitude difference, Gaia/HIP parallax distances, parallax-derived
3D separation, `h2bn` context, and `gaiadr3.hipparcos2_neighbourhood` context.

Clean supplemental crossmatch rows require one-to-one local evidence and
agreement with the `h2bn` and `hipparcos2_neighbourhood` context. Tight sky
pairs are accepted at `<= 0.25 arcsec`. Wider pairs are accepted when the
parallax-derived 3D separation is `<= 1 pc`.

Photometric and astrometric columns are recorded as crossmatch diagnostics,
especially for resolving multiple-star and crowded-field candidates.

## Results

- Gaia rows scanned for compact match table: `1,467,744,818`.
- Gaia `G <= 15` rows used for raw matching: `36,635,159`.
- HIP rows prepared: `117,955`.
- Evidence pairs within `5 arcsec`: `122,678`.
- `h2bn` pairs recovered in the local evidence field: `92,436`.
- Supplemental crossmatch rows published: `15,679`.
- Ambiguous local evidence rows retained: `13,721`.
- Separate-object evidence rows retained: `842`.

## Outputs

Catalog:

- `catalog/fis_gaia_hip_supplemental_crossmatch_map.parquet`

Primary evidence:

- `evidence/gaia_hip_crossmatch_evidence.parquet`
- `evidence/gaia_hip_crossmatch_report.json`
- `evidence/gaia_raw_match_g15_summary.json`
- `evidence/support_input_provenance.json`

## Runtime Note

The Gaia `G <= 15` preparation step streamed a 137G local Gaia VOTable payload
into a compact local intermediate. The final compact intermediate is about 2.0
GB and is recorded by checksum rather than included in this publication.
