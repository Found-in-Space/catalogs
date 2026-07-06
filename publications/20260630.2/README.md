# Gaia-Hipparcos2 Visual Deduplication Pairing Evidence Catalog

Release: `20260630.2`

This publication contains reproducible Gaia-Hipparcos2 pairing evidence for
Found in Space visual deduplication work. Its immediate purpose is to reduce
visually aligned Gaia/Hipparcos pairs that look like duplicate or suspicious
multiple stars in VR and 3D rendering workflows.

The publication also includes a clean one-to-one supplemental crossmatch map.
That map is a merge input, but the broader publication is not a final
merge-decision policy.

The controlled Gaia DR3 acquisition used here is published as DOI
`10.5281/zenodo.21066981`. The raw Gaia VOTable payload is not included here.
It is represented by the published Gaia acquisition record, per-file manifests,
checksums, and the local `G <= 15` conversion summary.

## Scope

This catalog identifies Gaia-Hipparcos2 aligned-pair evidence and ambiguity
contexts. It is intended to support downstream sidecar building for visual
deduplication.

It does not:

- decide which physical row should survive the final core merge;
- broadly prefer Gaia over Hipparcos;
- classify real binaries or multiple-star systems;
- claim that every nearby pair is a duplicate identity;
- replace the pipeline's Gaia/Hipparcos winner policy or manual overrides.

Without an external binary/component catalog or manual review, this evidence
cannot always distinguish duplicate identities from real visual binaries,
component mismatches, or crowded-field alignments.

## Outputs

Catalog:

- `catalog/fis_gaia_hip_supplemental_crossmatch_map.parquet` - clean
  one-to-one Gaia-Hipparcos2 pairs suitable for direct use as supplemental
  merge-input mappings.

Schema:

```text
gaia_source_id
hip_source_id
mapping_source
number_of_neighbours
angular_distance
```

Rows: `15,679`.

All rows have `mapping_source = fis_raw_crossmatch_v1`.

Evidence:

- `evidence/gaia_hip_crossmatch_evidence.parquet` - local pairing evidence
  table.
- `evidence/gaia_hip_crossmatch_report.json` - thresholds, row counts, and
  decision and evidence-category counts from the raw pairing scan.
- `evidence/gaia_raw_match_g15_summary.json` - controlled Gaia VOTable to
  compact `G <= 15` Parquet conversion summary.
- `evidence/support_input_provenance.json` - row counts and checksums for
  source inputs and generated run outputs.
- `evidence/gaia-votables-manifest.tsv` and `evidence/gaia-votables.sha256` -
  copied source-file manifest/checksum evidence from the controlled Gaia
  acquisition package.

## Key Counts

- Controlled Gaia rows scanned: `1,467,744,818`.
- Compact Gaia `G <= 15` rows written: `36,635,159`.
- Raw Hipparcos rows prepared: `117,955`.
- `h2bn` rows: `99,525`.
- `hipparcos2_neighbourhood` rows: `100,010`.
- Gaia-Hipparcos2 evidence pairs within `5 arcsec`: `122,678`.
- Clean supplemental crossmatch rows: `15,679`.
- `h2bn` pairs recovered in the local evidence field: `92,436`.
- Non-accepted evidence rows retained for diagnostics: `14,563`.

## Pairing Criteria

The source table `gaiadr3.hipparcos2_best_neighbour` is abbreviated as `h2bn`.

- `h2bn` is used as the Gaia DR3 Hipparcos2 best-neighbour reference catalog;
- clean supplemental crossmatch rows must be one-to-one in the local evidence
  field;
- local candidates that conflict with `h2bn` are retained as evidence;
- local candidates that conflict with `gaiadr3.hipparcos2_neighbourhood` are
  retained as evidence;
- sky separation `<= 0.25 arcsec` is accepted for clean one-to-one pairs;
- wider pairs up to `5 arcsec` are accepted when parallax-derived 3D separation
  is `<= 1 pc`;
- photometric and astrometric columns are recorded as diagnostics for sidecar
  building, especially in crowded-field and multiple-star contexts.

## Evidence Categories

The evidence table records `decision` for compatibility with the raw matching
tool and `evidence_category` for publication-facing interpretation.

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

## Consumer Contract

This publication provides pairing evidence. A downstream Found in Space pipeline
sidecar builder must join it with staged Gaia rows, staged Hipparcos rows, the
final `h2bn` plus supplemental crossmatch map, and manual overrides before
deciding row retention, row replacement, or review status.

The evidence should be sufficient for sidecar code to compute:

```text
delta_d_pc = abs(gaia_r_pc - hip_r_pc)

combined_distance_sigma_pc =
  sqrt((gaia_r_pc * gaia_parallax_frac_error)^2
     + (hip_r_pc  * hip_parallax_frac_error)^2)

delta_d_sigma = delta_d_pc / combined_distance_sigma_pc
```

Downstream sidecar decisions also require staged pipeline fields that are not
finalized by this publication, including Gaia and Hipparcos astrometry quality,
Gaia RUWE where available, Hipparcos solution type, final crossmatch presence,
and manual override coverage.

Bright and naked-eye candidates should be handled by an explicit completeness
gate. They should not be silently removed by this publication's evidence alone.

## License And Notice

Found in Space original material in this publication is released under CC BY
4.0, as described in `LICENSE.txt`.

Source catalogue data and source-derived evidence remain subject to upstream
terms and credit requirements. See `NOTICE.md` and `REFERENCES.md`.
