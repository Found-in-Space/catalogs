# Gaia-HIP Supplemental Crossmatch Catalog For Controlled Core Dataset

Release: `20260630.2`

This publication contains Found in Space supplemental Gaia-Hipparcos2
crossmatch rows regenerated from the controlled Gaia DR3 acquisition published
as DOI `10.5281/zenodo.21066981`.

The raw Gaia VOTable payload is not included here. It is represented by the
published Gaia acquisition record, per-file manifests, checksums, and the local
`G <= 15` conversion summary.

## Catalog

- `catalog/fis_gaia_hip_supplemental_crossmatch_map.parquet` - the published
  Found in Space supplemental Gaia-Hipparcos2 crossmatch rows.

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

## Evidence

- `evidence/gaia_hip_crossmatch_evidence.parquet` - local crossmatch
  evidence table.
- `evidence/gaia_hip_crossmatch_report.json` - thresholds, row counts, and
  decision counts from the raw matching scan.
- `evidence/gaia_raw_match_g15_summary.json` - controlled Gaia VOTable to
  compact `G <= 15` Parquet conversion summary.
- `evidence/support_input_provenance.json` - row counts and checksums for
  local source inputs and publication outputs.
- `evidence/gaia-votables-manifest.tsv` and `evidence/gaia-votables.sha256` -
  copied source-file manifest/checksum evidence from the controlled Gaia
  acquisition package.

## Key Counts

- Controlled Gaia rows scanned: `1,467,744,818`.
- Compact Gaia `G <= 15` rows written: `36,635,159`.
- Raw Hipparcos rows prepared: `117,955`.
- `h2bn` rows: `99,525`.
- `hipparcos2_neighbourhood` rows: `100,010`.
- Gaia-HIP evidence pairs within `5 arcsec`: `122,678`.
- Supplemental crossmatch rows: `15,679`.
- `h2bn` pairs recovered in the local evidence field: `92,436`.
- Ambiguous local evidence rows: `13,721`.
- Separate-object evidence rows: `842`.

## Crossmatch Criteria

This catalog is concerned with crossmatching Gaia and Hipparcos2 source
identities. The source table `gaiadr3.hipparcos2_best_neighbour` is abbreviated
as `h2bn`.

- `h2bn` is used as the published Gaia DR3 Hipparcos2 best-neighbour catalog;
- supplemental crossmatch rows must be one-to-one in the local evidence field;
- local candidates that conflict with `h2bn` are retained as evidence;
- local candidates that conflict with `gaiadr3.hipparcos2_neighbourhood` are
  retained as evidence;
- sky separation `<= 0.25 arcsec` is accepted for clean one-to-one pairs;
- wider pairs up to `5 arcsec` are accepted when parallax-derived 3D separation
  is `<= 1 pc`;
- photometric and astrometric columns are crossmatch diagnostics, especially in
  multiple-star and crowded-field cases.

## License And Notice

Found in Space original material in this publication is released under CC BY
4.0, as described in `LICENSE.txt`.

Source catalogue data and source-derived evidence remain subject to upstream
terms and credit requirements. See `NOTICE.md` and `REFERENCES.md`.
