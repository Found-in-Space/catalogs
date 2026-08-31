# Zenodo Draft Metadata

## Record

- Title: **Gaia-HIP supplemental display de-duplication map**
- Upload type: **Dataset**
- Version: **20260515.1**
- Publication model: **Standalone historical publication**
- Publication date: set to the actual Zenodo publication date
- Community: **Found in Space**
- Licence: **Creative Commons Attribution 4.0** for Found in Space original
  material; upstream terms continue to apply

## Creator

- Name: **Siebert, Kaj Wik**
- Affiliation: **University College London**
- ORCID: **0009-0009-4500-4316**

## Description

This dataset publishes `15,916` supplemental Gaia DR3-Hipparcos2 identifier
pairs used by Found in Space to reduce visually duplicated points and radial
"finger of god" artefacts in rendered 3D and VR views.

The map is a visual de-duplication aid, not a scientific crossmatch. Inclusion
of a pair does not claim that the two records represent the same physical
star, that either catalogue is wrong, or that either record should be removed
from scientific use. Establishing physical identity would require more
detailed analysis than this display policy performs. The official Gaia
`hipparcos2_best_neighbour` table remains the scientific baseline and is not
republished here.

The publication includes the compact Parquet map, the full candidate and
decision evidence, acquisition metadata, diagnostics, VR context captures,
references, upstream notices, and SHA-256 checksums.

## Keywords

- Gaia DR3
- Hipparcos
- stellar catalogues
- visual de-duplication
- 3D visualization
- virtual reality
- reproducible data

## Related resources

- Repository: <https://github.com/Found-in-Space/catalogs>
- Project website: <https://foundin.space/>
- Scientific and catalogue references: `REFERENCES.md`

## Upload contents

Upload three files:

1. `README.md`, for direct preview;
2. `fis_gaia_hip_supplemental_display_map.parquet`, for direct data access;
3. `fis-gaia-hip-supplemental-display-map-20260515.1.zip`, a
   path-preserving archive of the complete publication directory.

Build the ZIP outside `publications/20260515.1/` from the final clean public
commit. Do not include the ZIP inside itself or in `checksums.sha256`.

## Final checks

- Confirm the release checksum manifest passes.
- Confirm the deposited Parquet checksum matches the catalog file.
- Confirm the ZIP preserves publication-relative paths.
- Confirm no credentials, private URLs, or machine-specific absolute paths are
  present.
- After publication, record the Zenodo record/Concept DOI, exact catalogs
  commit, and deposited-file checksums in `zenodo/published-record.toml`.
