# Notice for Publication 20260730.1

Publication: Reviewed stellar distance overrides
Release: `20260730.1`

## Scope and Interpretation

This publication contains 48 opt-in pipeline replacements selected from an
81-row review cohort. A `resolved` status means the cited evidence was judged
suitable for this controlled rendering dataset; it does not supersede Gaia,
Hipparcos, or the cited specialist work for general scientific use.

The 33 provisional tracker rows are included only as review evidence and must
not be applied as overrides.

The catalog changes distance-dependent render placement for the selected
canonical rows. Absolute magnitude is rebased to preserve the staged apparent
brightness at the reviewed distance. The publication does not assert new
photometric measurements.

## Upstream Sources

The compact evidence and row-level references draw on Gaia, Hipparcos,
SIMBAD, VizieR catalogs including StarHorse, and the specialist publications
listed in `REFERENCES.md` and in each catalog entry. Upstream catalog terms,
mission acknowledgements, and publication rights continue to apply.

No full Gaia or Hipparcos catalog is redistributed here. The included Parquet
files are compact, purpose-specific review inputs.

## Application Boundary

This release:

- is not applied automatically by the pipeline;
- does not change Gaia–Hipparcos pairing;
- does not include the Sun; and
- does not promote provisional review rows.

Consumers must select the YAML explicitly and preserve the publication release
and checksum in their run provenance.

## No Endorsement

Use of author, archive, mission, catalog, or journal names does not imply
endorsement of Found in Space or downstream applications.
