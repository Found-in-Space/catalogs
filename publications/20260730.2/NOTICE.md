# Notice for Publication 20260730.2

Publication: Found in Space stellar overrides
Release: `20260730.2`

## Scope and Interpretation

This publication contains three retained Alpha Centauri overrides and 48
reviewed additions selected from an 81-row review cohort. The retained entries
preserve their original executable identities and values; their provenance has
been expanded and an obsolete best-neighbour statement corrected.

A `resolved` tracker status means the cited distance evidence was judged
suitable for the current controlled rendering use case. It does not supersede
Gaia, Hipparcos, SIMBAD, VizieR, or the cited specialist work for general
scientific use. The 33 provisional tracker rows are evidence only and must not
be applied.

The 48 additions change distance-dependent placement and rebase absolute
magnitude to preserve staged apparent brightness. The three retained entries
also carry established astrometric, photometric, and temperature corrections.
The publication asserts no new astronomical measurements.

## Explicit Exclusions

Sirius B and Procyon B were retired from the pipeline before this publication
and are not executable here. Their earlier appearance in development history
does not make them part of the original published base.

The Sun is a separate opt-in reference and is not included. The release contains
51 `replace` actions and no `add` action.

## Pairing Boundary

This release:

- uses Gaia DR3 `hipparcos2_best_neighbour` as the only automatic
  Gaia-Hipparcos pairing authority;
- does not use the supplemental Gaia-HIP map for merging;
- does not change pairing policy;
- is not applied automatically by the pipeline; and
- does not promote provisional review rows.

The current controlled best-neighbour artifact maps Alpha Cen B and Proxima to
their HIP rows and has no row for Alpha Cen A. The exact three-target review and
source checksums are in `evidence/alpha_cen_pairing_review.json`.

Consumers must select both YAML files explicitly and preserve the publication
release and checksums in run provenance.

## Versioning Boundary

`fis.overrides` is an evolving catalog distributed as a single Zenodo version
chain. Every published release is an immutable snapshot. Changes to catalog
rows, evidence, checksums, selection rules, or methodology require a new
release and Zenodo's **New version** workflow in the same lineage. A
metadata-only correction may edit the published record only when it leaves the
payload and its scientific interpretation unchanged.

Each release has a Version DOI and the series has one stable Concept DOI.
Reproducible work must cite the exact release and Version DOI; references to
the evolving series or its latest version may cite the Concept DOI. Zenodo
reserved Version DOI
[`10.5281/zenodo.21703732`](https://doi.org/10.5281/zenodo.21703732) for
release `20260730.2` before packaging. It will be registered, and the stable
Concept DOI assigned, when the initial deposit is published.

## Upstream Sources

The compact evidence and row-level references draw on Gaia, Hipparcos, SIMBAD,
VizieR catalogs including StarHorse, and the specialist publications listed in
`REFERENCES.md` and in each catalog entry. Upstream catalog terms, mission
acknowledgements, and publication rights continue to apply.

No full Gaia or Hipparcos catalog is redistributed. Included Parquet files are
compact, purpose-specific review inputs.

## No Endorsement

Use of author, archive, mission, catalog, or journal names does not imply
endorsement of Found in Space or downstream applications.
