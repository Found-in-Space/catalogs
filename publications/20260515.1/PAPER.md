# Gaia-HIP Supplemental Display De-Duplication Map

Publication: `20260515.1`

## Purpose and scope

When Gaia DR3 and Hipparcos-2 are rendered together, some catalogue entries
appear as duplicate points or long radial "fingers" in the 3D view. This
publication provides `15,916` supplemental Gaia-HIP pairs that Found in Space
can collapse for display.

This is a visual de-duplication aid, not a scientific crossmatch. Inclusion of
a pair does not claim that the two catalogue records represent the same
physical star, that either catalogue is wrong, or that either record should be
removed from scientific use. Gaia and Hipparcos can differ or fail to align for
many reasons, including observing epoch, astrometric uncertainty, source
multiplicity, variability, catalogue selection, and problematic solutions.
Establishing physical identity would require more detailed analysis than this
display policy performs.

The official Gaia `hipparcos2_best_neighbour` table remains the scientific
baseline. This publication contains only a Found-in-Space display delta and
does not republish or replace the official table.

## Method summary

The scan used:

- Hipparcos-2 / VizieR `I/311` positions, proper motions, magnitudes, and
  parallaxes;
- Gaia DR3 `gaia_source` rows with `G <= 15`;
- Gaia DR3 `hipparcos2_best_neighbour`; and
- Gaia DR3 `hipparcos2_neighbourhood`.

Hipparcos positions were propagated from J1991.25 to J2016.0 and compared with
Gaia positions within `5 arcsec`. A non-official pair was added to the display
map only when it was locally one-to-one, had no official-table conflict, and
met one of these visual rules:

| Rule | Display action |
| --- | --- |
| Sky separation `<= 0.25 arcsec` | Collapse for display |
| Separation `0.25-5 arcsec` and rendered 3D separation `<= 1 pc` | Collapse for display |
| Otherwise | Leave separate |

Magnitude and colour are retained as diagnostics but are not hard selection
gates. The full decision evidence is published with the map.

## Results

The scan produced `126,220` candidate pairs:

| Decision | Rows |
| --- | ---: |
| Official pair recovered | `92,620` |
| Manual or conflicting evidence | `16,753` |
| Supplemental display match | `15,916` |
| Keep visually separate | `931` |

Of the supplemental rows, `15,725` pass the tight-sky rule and `191` pass the
rendered-distance rule.

## VR context

These project-supplied captures show the VR context in which the map was
assessed. They are qualitative evidence and do not alter the selection policy.

![VR finger-of-god view](evidence/vr_finger_of_god.jpg)

![VR view from the Sun](evidence/vr_from_sun.jpg)

## Published data

- `catalog/fis_gaia_hip_supplemental_display_map.parquet` - the `15,916`-row
  display delta.
- `evidence/gaia_hip_display_match_evidence.parquet` - the `126,220`-row
  decision evidence table.
- `evidence/gaia_hip_display_match_report.json` - thresholds and summary
  counts.
- Remaining files in `evidence/` record the Gaia query, download state,
  magnitude diagnostics, footprint analysis, and VR captures.

The local combined official-plus-supplemental map is intentionally not
published. Consumers should apply this delta only where visual de-duplication
is desired and should not treat it as evidence of physical identity.

See `README.md` for the schema, `run_log.md` for detailed provenance,
`REFERENCES.md` for scientific sources, and `NOTICE.md` for upstream terms and
credits.
