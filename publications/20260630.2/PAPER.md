# A Policy-Neutral Gaia DR3–Hipparcos Pairing-Evidence Catalogue

## Abstract

This release publishes a reproducible evidence table of possible Gaia DR3 and
Hipparcos pairings for later 3D star-field processing. The table is the
deduplicated union of all Gaia DR3 `hipparcos2_best_neighbour` mappings and a
local `5 arcsec` scan over a controlled `G <= 15` Gaia table. It records
crossmatch membership, local topology, apparent magnitudes, distances,
uncertainties, and derived radial and three-dimensional separations. It makes
no duplicate-identity, preferred-source, removal, or merged-record decision.

## Motivation

Two catalog rows that are nearly coincident on the sky can be placed several
parsecs apart in a three-dimensional rendering when their inferred distances
disagree. At roughly one rendered metre per parsec, this may create an obvious
radial “finger” rather than a single rendered object. Whether such a pairing
should be accepted and how its output fields should be chosen are pipeline
policy questions. A citable catalog should first preserve the candidate
population and its measurements without embedding that policy.

## Pair acquisition

The evidence population is the set union of:

1. all `99,525` Gaia DR3 H2BN mappings; and
2. all `122,678` pairs found within `5 arcsec` while scanning the existing
   `36,635,159`-row compact Gaia `G <= 15` table against Hipparcos.

Pairs are deduplicated by `(gaia_source_id, hip_source_id)`. Independent
`h2bn_pair` and `local_scan_pair` flags preserve provenance. H2BN-only rows are
retained even when their Gaia source lies outside the compact-table scope; in
that case Gaia measurements are null.

The controlled inputs are expected to yield `97,996` overlapping pairs and a
`124,207`-row union. Publication assembly rejects any other result.

## Measurements

The table records Gaia G and Hipparcos Hp as explicit apparent magnitudes. The
signed comparison is:

```text
gaia_g_minus_hip_hp_mag = gaia_g_mag - hip_hp_mag
```

Its absolute value is also recorded for descriptive summaries. Because G and
Hp are not identical passbands, neither value is used as an automatic pairing
gate. Absolute magnitudes are excluded because their derivation already
depends on distance.

For finite positive parallaxes, reciprocal-parallax distances are recorded in
parsecs. The radial comparison is:

```text
radial_gap_pc = abs(gaia_r_pc - hip_r_pc)
combined_distance_sigma_pc =
    sqrt((gaia_r_pc * gaia_parallax_frac_error)^2
       + (hip_r_pc * hip_parallax_frac_error)^2)
radial_gap_sigma = radial_gap_pc / combined_distance_sigma_pc
```

The parallax-derived 3D separation combines the two radial distances with the
measured angular separation using the law of cosines. Invalid or unavailable
measurements remain null.

Local candidate counts, sky-neighbour counts, one-to-one topology, H2BN
membership/conflicts, Hipparcos2 neighbourhood context, BP/RP values,
parallaxes, uncertainties, Hipparcos proper motion, and Hipparcos solution type
are retained where available.

## Descriptive summaries

The generated report provides source, union, overlap, missing-measurement,
ambiguity, and context counts. It also reports fixed descriptive bins:

- radial gap: `<=1`, `1–3`, `3–5`, `5–10`, `>10 pc`;
- absolute G–Hp difference: `<=0.5`, `0.5–1`, `1–2`, `>2 mag`.

These bins do not imply acceptance, rejection, visual significance, or source
preference.

## Policy boundary

H2BN is authoritative evidence that Gaia publishes a best-neighbour mapping;
it is not asserted here to prove duplicate identity. The local scan similarly
records proximity rather than identity. Downstream pipeline work must decide:

- whether a pairing is accepted;
- whether one row is retained or both are retained;
- whether one source wins or fields are fused;
- how apparent-magnitude differences protect important bright stars;
- how radial gaps interact with rendering scale and uncertainty;
- how named objects, pathological distances, and overrides are handled.

No supplemental map is published, and there are no decision, action,
recommendation, or severity columns.

## Reproducibility

The release reuses the existing 2 GB compact Gaia table produced from the
controlled Gaia acquisition. It does not repeat conversion of the 137 GB raw
VOTable payload. The publication assembler requires a clean committed catalogs
worktree whose HEAD is present on its configured upstream, validates the exact
pair counts and schema, hashes every support input including the raw H2BN ECSV,
copies selected Gaia acquisition evidence, and regenerates the complete
publication checksum manifest.

## Data product

The only pairing data product is:

`evidence/gaia_hip_pairing_evidence.parquet`

The accompanying JSON report and provenance describe its generation and
validation. No DOI is reserved or published by this change.
