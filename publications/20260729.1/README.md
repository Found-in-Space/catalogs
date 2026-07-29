# Optional Solar Reference

Release: `20260729.1`
Status: release candidate

This publication contains one opt-in reference entry for the Sun. It supplies
published solar values and an optional synthetic session-origin placement for
applications that want to render, label, select, or navigate relative to a Sun
object.

The entry is deliberately not:

- a member of the core external-star catalog;
- a correction for a missing or uncertain Gaia/Hipparcos result;
- a merge-ready Found in Space pipeline override; or
- automatically included in `stars.octree`.

The core octree uses a solar-origin coordinate frame without requiring a Sun
row. Applications may load this reference through a static star provider,
replace it with their own Sun, or omit it.

## Catalog

- `catalog/fis_solar_reference.yaml` — the single optional solar reference
  entry, its physical-value provenance, and its optional session placement.

The entry records:

| Field | Value | Meaning |
|---|---:|---|
| Johnson V absolute magnitude | `4.81` | Vegamag value from Willmer (2018) |
| Nominal effective temperature | `5772 K` | Exact conversion constant adopted by IAU 2015 Resolution B3 |
| Default session position | `(0, 0, 0) pc` | Optional synthetic solar-origin placement, not an astrometric measurement |

The nominal effective temperature is a standard conversion constant, not an
uncertainty-free claim about the instantaneous physical Sun. Likewise, the
origin coordinates are a scene/reference-frame convention rather than observed
astrometry.

## Provider Use

The intended consumer is a small static or reference-object provider composed
with an external-catalog octree provider. Provider identity must remain visible
to picking, metadata, and replacement logic.

Consumers must opt in. They may:

- use the published values and default placement;
- use the values with a different visual representation;
- replace any or all values under an application-owned identity; or
- omit the Sun entirely.

No cross-provider deduplication or replacement is implied by this publication.

## Files

- `manifest.toml` — scope, inputs, outputs, counts, and provenance.
- `catalog/fis_solar_reference.yaml` — published data product.
- `REFERENCES.md` — primary scientific and standards references.
- `NOTICE.md` — scope, interpretation, and attribution notice.
- `LICENSE.txt` — publication licence and upstream-rights boundary.
- `run_log.md` — authoring and validation record.
- `checksums.sha256` — SHA-256 checksums generated from the final files.

## Licence

Found in Space original prose, organization, and schema are released under
CC BY 4.0. Scientific facts and standards remain attributable to their cited
sources, whose publication rights are unaffected. See `LICENSE.txt`,
`NOTICE.md`, and `REFERENCES.md`.
