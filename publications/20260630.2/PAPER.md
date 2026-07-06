# Gaia-Hipparcos2 Visual Deduplication Pairing Evidence Catalog

Release: `20260630.2`

## Abstract

This release provides reproducible Gaia-Hipparcos2 pairing evidence for Found
in Space visual deduplication work. The immediate use case is reducing visually
aligned Gaia/Hipparcos pairs that appear as suspicious duplicate or multiple
stars in VR and 3D rendering workflows.

The release includes a clean one-to-one supplemental Gaia-Hipparcos2 crossmatch
map, but it is not a final merge-decision table. Downstream pipeline policy must
join this evidence with staged Gaia rows, staged Hipparcos rows, the final
crossmatch map, and manual overrides before deciding row retention, row
replacement, or review status.

The controlled Gaia DR3 acquisition used here is published as DOI
`10.5281/zenodo.21066981`. The source table
`gaiadr3.hipparcos2_best_neighbour` is abbreviated as `h2bn`.

## Method

The controlled Gaia VOTable payload was streamed into a compact local Parquet
table containing only rows with `phot_g_mean_mag <= 15` and the fields needed
for raw pairing:

```text
source_id, ra, dec, phot_g_mean_mag, phot_bp_mean_mag, phot_rp_mean_mag,
parallax, parallax_error
```

Hipparcos-2 positions were propagated from epoch J1991.25 to Gaia epoch J2016.0
using proper motion. Gaia sources were scanned against the propagated HIP sky
positions within `5 arcsec`.

The evidence table records:

- Gaia and Hipparcos source identifiers;
- sky separation;
- apparent-magnitude difference;
- Gaia/Hipparcos parallax distances;
- Gaia/Hipparcos parallax fractional errors;
- parallax-derived 3D separation;
- local candidate counts and ambiguity indicators;
- `h2bn` context;
- `gaiadr3.hipparcos2_neighbourhood` context;
- a publication-facing `evidence_category`.

Clean supplemental crossmatch rows require one-to-one local evidence and
agreement with the `h2bn` and `hipparcos2_neighbourhood` context. Tight sky
pairs are accepted at `<= 0.25 arcsec`. Wider pairs are accepted when the
parallax-derived 3D separation is `<= 1 pc`.

Photometric and astrometric columns are recorded as diagnostics for downstream
sidecar building, especially in crowded-field and multiple-star contexts. This
publication does not classify binary systems and does not decide which physical
row should survive the final core merge.

## Evidence Categories

- `h2bn_recovered` - the local scan recovers the same one-to-one Gaia-HIP pair
  as `gaiadr3.hipparcos2_best_neighbour`.
- `supplemental_match` - the local scan finds a clean one-to-one pair not
  already present as an `h2bn` pair.
- `local_ambiguity` - the local scan finds more than one plausible Gaia or HIP
  candidate in the neighbourhood.
- `h2bn_disagreement` - the local pair conflicts with the Gaia DR3
  `hipparcos2_best_neighbour` mapping for either source.
- `hipparcos2_neighbourhood_disagreement` - the local pair conflicts with the
  Gaia DR3 `hipparcos2_neighbourhood` context for either source.
- `nearby_nonmatch` - the local scan found a nearby candidate within the broad
  scan radius, but it did not satisfy the clean one-to-one tight-sky or
  parallax-3D acceptance criteria.

## Sidecar Use

The evidence table is intended to support downstream visual-deduplication
sidecars. It supplies enough distance and uncertainty information to compute:

```text
delta_d_pc = abs(gaia_r_pc - hip_r_pc)

combined_distance_sigma_pc =
  sqrt((gaia_r_pc * gaia_parallax_frac_error)^2
     + (hip_r_pc  * hip_parallax_frac_error)^2)

delta_d_sigma = delta_d_pc / combined_distance_sigma_pc
```

The final sidecar policy must also use staged pipeline fields outside this
publication, including Gaia and Hipparcos astrometry quality, Gaia RUWE where
available, Hipparcos solution type, final crossmatch presence, and manual
override coverage.

Bright and naked-eye candidates require an explicit completeness gate. They
should not be silently removed by this evidence publication alone.

## Results

- Gaia rows scanned for compact match table: `1,467,744,818`.
- Gaia `G <= 15` rows used for raw pairing: `36,635,159`.
- HIP rows prepared: `117,955`.
- Evidence pairs within `5 arcsec`: `122,678`.
- `h2bn` pairs recovered in the local evidence field: `92,436`.
- Clean supplemental crossmatch rows published: `15,679`.
- Non-accepted evidence rows retained for diagnostics: `14,563`.

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

The final raw Gaia-Hipparcos2 pairing scan over the 36.6M-row compact Gaia
table completed in `12m4s` wall time on the local small-machine run.
