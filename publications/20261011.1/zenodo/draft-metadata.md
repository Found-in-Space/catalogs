# Initial Zenodo deposit metadata

This is preparation material for the first publication of `fis.textures.moon.lroc-wac-global-morphology-100m`.
No draft has been created and no DOI has been reserved by this preparation.

## Record fields

- Title: **Found in Space lunar display textures: LROC WAC global morphology 100 m**
- Resource type: **Dataset**
- Version: **20261011.1**
- Publication date: the actual publication date, to be set when publishing.
- Creator: **Siebert, Kaj Wik**
- Affiliation: **University College London**
- ORCID: **0009-0009-4500-4316**
- Community: **Found in Space**
- Metadata-deposit licence: **CC BY 4.0** for Found in Space original material.
  Copied producer definitions remain MIT. The exact USGS source product
  metadata identifies the upstream imagery as public domain; cite its authors.
- Version DOI and Concept DOI: pending initial deposit/publication.

Creator details follow earlier Found in Space catalog releases and should be
confirmed in the final deposit preview. The tile payload is external; explain
that distinction prominently in the description and supply verified links.

Keywords: Moon; lunar imagery; LROC; LRO; WAC; planetary cartography;
display textures; geographic XYZ tiles; reproducible data; provenance.

## Proposed description

Found in Space lunar display textures derived from the LROC WAC global
morphology mosaic distributed by USGS Astrogeology. Release 20261011.1
authenticates 87,381 opaque 512-pixel grayscale PNG tiles at zooms 0–8,
totalling 8,160,721,984 bytes, in a geographic square XYZ matrix covering the
Moon. The lunar reference sphere has radius 1,737,400 metres; x increases
eastward and y increases southward.

This metadata deposit includes the source identity and acquisition receipt,
complete source inspection, project and CRS definitions, exact producer code
history and dependency files, processing states and commands, complete producer
pixel validation, and per-tile SHA-256 manifests. The image files are hosted
externally and are not included in the metadata archive. Insert verified
immutable payload and producer-code links after publication prerequisites pass.

Planned; no hosting receipt has been supplied.
Verified download links will be supplied after hosting checks pass.
Representative source reprojection, direct-from-base averaging, and tile emission checks are recorded in evidence/representative_checks.json. The recorded process and representative display checks support
reuse without requiring byte-identical regeneration or a full pyramid rebuild.

The imagery is intended for display and interactive exploration. Reprojection
and pyramid construction do not create new observed detail. The payload is not
an elevation or calibrated reflectance dataset. Missing coverage is opaque
black. Credit NASA, the LROC Team at Arizona State University, and USGS.

## Related identifiers and attribution

- Source dataset (`IsDerivedFrom`):
  https://astrogeology.usgs.gov/search/map/moon_lro_lroc_wac_global_morphology_mosaic_100m
- Instrument reference (`References`): https://doi.org/10.1007/s11214-010-9634-2
- Mosaic reference (`References`): https://www.lpi.usra.edu/meetings/lpsc2011/pdf/2387.pdf
- Production reference (`References`): https://www.hou.usra.edu/meetings/lpsc2015/pdf/1473.pdf
- Exact catalogs release commit (`IsSupplementTo`): add its public commit URL
  after final metadata, evidence, and checksums are committed.
- Verified producer-code URLs and immutable tile/product URLs: pending.

Use one Zenodo version lineage for this series. Cite each release's Version
DOI for exact reproduction and the Concept DOI for the series. Keep later
DOI-tracking metadata outside the already-deposited payload.
