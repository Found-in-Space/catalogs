# Gaia/HIP Source Download Evidence

Release: `20260515.1`

This draft publication is the source-data evidence package for the Gaia/HIP
mapping work. So far it records the Hipparcos download/build and the first
Hipparcos `Hp` versus Gaia `G` magnitude relationship evidence used to choose
a Gaia download cutoff.

The source catalog downloads themselves remain in local scratch for now. The
preserved release evidence is under `evidence/`.

## Current Evidence

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
- The next matching attempt should use a full-sky Gaia `G <= 15` download with
  a limited matching field set rather than the full visual-build field set.

The `G > 14.5622` rows are retained as evidence because some official matches
have extreme Gaia/HIP magnitude disagreement. They should inform the mapping
review, but they should not by themselves define the Gaia download cutoff.

## Current Decision

For Gaia-HIP candidate matching, the crossmatch publication only needs to
identify likely same-source ID pairs. Final winner selection remains a pipeline
merge decision using the full processed Gaia and Hipparcos rows.

The first full-sky candidate pass should therefore try Gaia `G <= 15` with
`source_id`, `ra`, `dec`, and `phot_g_mean_mag` as required selected fields.
Gaia BP/RP may be included as evidence-only diagnostics.

The targeted HEALPix/cone-fetch approach remains recorded as a fallback if the
full-sky skinny download proves awkward operationally.
