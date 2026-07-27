# Zenodo Draft Metadata

This is preparation material only. Do not reserve a DOI or publish a Zenodo
record as part of the pairing-evidence implementation.

## Title

Policy-neutral Gaia DR3–Hipparcos pairing evidence for Found in Space

## Upload type

Dataset

## Publication date

To be set when an upload is intentionally published.

## Creators

Found in Space contributors

## Description

This dataset records possible Gaia DR3–Hipparcos pairings for later pipeline
policy. Its single Parquet product is the deduplicated union of all Gaia DR3
`hipparcos2_best_neighbour` mappings and every pair found by a `5 arcsec` local
scan of a controlled compact Gaia `G <= 15` table.

The evidence preserves independent H2BN and local-scan membership, explicit
Gaia G and Hipparcos Hp apparent magnitudes, signed and absolute magnitude
differences, catalog distances, radial gap, combined distance uncertainty,
uncertainty-normalized radial gap, parallax-derived 3D separation, local
topology, and H2BN/neighbourhood context.

H2BN is treated as authoritative published pairing context. The dataset does
not decide duplicate identity, select a source winner, recommend removal, or
construct a merged row. It contains no supplemental or combined crossmatch
map. Pair acceptance, rendering-scale thresholds, magnitude safeguards, source
selection, field fusion, and overrides remain downstream pipeline policy.

Controlled expected counts are `124,207` unique pairs, comprising `99,525`
H2BN pairs and `122,678` local-scan pairs with `97,996` overlaps.

## Keywords

- Gaia DR3
- Hipparcos
- crossmatch
- pairing evidence
- stellar catalogues
- 3D visualization
- reproducible data

## Licence

Creative Commons Attribution 4.0 for Found in Space original publication
material. Upstream Gaia, ESA, Hipparcos/Tycho, CDS/VizieR, and cited-source
terms continue to apply.

## Related identifiers

- Is supplemented by: `10.5281/zenodo.21066981` — controlled Gaia DR3
  acquisition provenance.
- References the Gaia and Hipparcos sources listed in `REFERENCES.md`.

## Upload contents

Upload a path-preserving archive of `publications/20260630.2/` after final
checksum validation. Do not include the raw 137 GB Gaia VOTables or the 2 GB
compact Gaia support table.

## Notes for a future publisher

- Confirm the publication is no longer marked draft.
- Confirm the observed counts match the controlled expected counts.
- Confirm `sha256sum --check checksums.sha256` succeeds.
- Confirm the archive contains no local absolute paths or credentials.
- Reserve or publish a DOI only under a separate explicit instruction.
