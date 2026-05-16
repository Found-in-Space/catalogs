# Gaia-HIP Supplemental Display Map

Release: `20260515.1`

This publication contains the Found-In-Space supplemental Gaia-Hipparcos2
display de-duplication map and the evidence used to derive it.

It does not republish the official Gaia `hipparcos2_best_neighbour` table. Use
the supplemental map alongside the official Gaia table when building a complete
Gaia-HIP display mapping.

Large source downloads remain in local scratch and are recorded by checksum and
query metadata rather than committed as release payloads.

## License And Notice

Found in Space original material in this publication is released under CC BY
4.0, as described in `LICENSE.txt`.

Source catalogue data and source-derived evidence remain subject to upstream
terms and credit requirements. See `NOTICE.md` for Gaia, Hipparcos/Tycho,
VizieR/CDS acknowledgements and publication references.

## Catalog

- `catalog/fis_gaia_hip_supplemental_display_map.parquet` - the published
  Found-In-Space supplemental mapping delta.

The catalog schema is:

```text
gaia_source_id
hip_source_id
mapping_source
number_of_neighbours
angular_distance
```

Rows: `15,916`

All rows have `mapping_source = fis_raw_sky_render_v1`.

## Current Evidence

- `evidence/gaia_hip_display_match_evidence.parquet` - full local
  sky/proximity/distance evidence table for the display matching scan.
- `evidence/gaia_hip_display_match_report.json` - row counts, thresholds, and
  paths from the matching scan.
- `evidence/gaia_g15_parallax_download.adql` - exact Gaia query used for the
  raw `G <= 15` parallax matching download.
- `evidence/gaia_g15_parallax_download_state.json` - Gaia async job metadata
  for that download.
- `evidence/gaia_g15_parallax_conversion_summary.json` - VOTable-to-Parquet
  conversion summary for the local working table.
- `evidence/hip_gaia_magnitude_relationship.png` - plot of Hipparcos `Hpmag`
  against Gaia DR3 `phot_g_mean_mag` for official Gaia-HIP matches.
- `evidence/hip_gaia_magnitude_relationship.parquet` - backing rows for the
  plot.
- `evidence/hip_gaia_magnitude_outliers.csv` - official matches with missing
  Gaia `G` or `G` fainter than the processed Hipparcos faint limit.
- `evidence/hip_gaia_magnitude_summary.json` - summary statistics and row
  counts.
- `evidence/hip_healpix_cone_footprint_summary.csv` - footprint estimates for
  targeted Gaia cone fetches around faint Hipparcos stars.
- `evidence/hip_healpix_neighbor_footprint_summary.csv` - footprint estimates
  for containing-HEALPix-cell plus neighbour expansion.
- `evidence/hip_healpix_footprint_summary.json` - summary of the targeted
  HEALPix/cone-fetch alternative.

## Key Observations So Far

- Raw Hipparcos rows downloaded: `117,955`.
- Processed finite-distance Hipparcos rows: `113,942`.
- Faintest processed Hipparcos `Hpmag`: `14.5622`.
- Official Gaia-HIP rows joined to Gaia photometry: `99,525`.
- Official matches with finite Gaia `G`: `99,463`.
- Official matches with Gaia `G > 14.5622`: `30`.
- Pipeline-shaped Gaia `G <= 15` sizing count: `36,635,159` rows.
- Raw Gaia `G <= 15` parallax matching download: `36,909,365` rows with
  `source_id`, sky position, Gaia photometry, `parallax`, and
  `parallax_error`.
- Parallax display-matching scan: `126,220` Gaia-HIP evidence pairs within
  `5 arcsec`, producing `15,916` one-to-one supplemental display matches.

The `G > 14.5622` rows are retained as evidence because some official matches
have extreme Gaia/HIP magnitude disagreement. They should inform the mapping
review, but they should not by themselves define the Gaia download cutoff.

## Current Decision

This release publishes only Found-In-Space supplemental display matches not
covered by the official Gaia best-neighbour map. A local combined map was
created to validate one-to-one composition, but it is intentionally not part of
the publication.

The supplemental display policy uses one-to-one local sky proximity,
official-table conflict checks, and parallax-derived rendered separation.
Magnitude and colour remain evidence-only diagnostics rather than hard default
gates.

The targeted HEALPix/cone-fetch approach remains recorded as a fallback if the
full-sky skinny download proves awkward operationally.
