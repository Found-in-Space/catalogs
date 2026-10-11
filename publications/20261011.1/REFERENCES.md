# Source and method references

Release: `20261011.1`

## Exact source product

LROC Team, Arizona State University; distributed by USGS Astrogeology Science
Center, *Moon LRO LROC WAC Global Morphology Mosaic 100m*, June 2013 GeoTIFF.

- Product page: https://astrogeology.usgs.gov/search/map/moon_lro_lroc_wac_global_morphology_mosaic_100m
- Requested payload: https://planetarymaps.usgs.gov/mosaic/Lunar_LRO_LROC-WAC_Mosaic_global_100m_June2013.tif
- Exact byte identity and complete raster inspection: `manifest.toml`, the
  acquisition receipt, and `evidence/sources/`.
- Public-source attribution and bibliographic references were reviewed on 2026-10-11.

## Upstream scientific references

Speyerer, E. J., Robinson, M. S., Denevi, B. W., and the LROC Science Team
(2011), *Lunar Reconnaissance Orbiter Camera global morphological map of the
Moon*, 42nd Lunar and Planetary Science Conference, abstract 2387.
https://www.lpi.usra.edu/meetings/lpsc2011/pdf/2387.pdf

Robinson, M. S., et al. (2010), *Lunar Reconnaissance Orbiter Camera (LROC)
instrument overview*, Space Science Reviews 150, 81–124.
https://doi.org/10.1007/s11214-010-9634-2

Wagner, R. V., Speyerer, E. J., Robinson, M. S., and the LROC Team (2015),
*New Mosaicked Data Products from the LROC Team*, 46th Lunar and Planetary
Science Conference, abstract 1473.
https://www.hou.usra.edu/meetings/lpsc2015/pdf/1473.pdf

The producer performs display conversion of an existing mosaic; it does not
repeat the upstream camera calibration, photometric modelling, or mosaicking.

## Software and publication policies

- Intended producer repository (public availability is pending verification):
  https://github.com/Found-in-Space/pas-de-geant-texture-pipeline
- Publication assembler: https://github.com/Found-in-Space/catalogs/tree/0cebfd1ffaf914298a1b0aa2eeae98bd22cb8c21
- GDAL: https://gdal.org/
- PROJ: https://proj.org/
- USGS copyright guidance: https://www.usgs.gov/faqs/are-usgs-reportspublications-copyrighted
- Zenodo version management: https://help.zenodo.org/docs/deposit/manage-versions/

Recorded producer SHAs, source hashes, CRS definitions, and tool versions are
included in this release. General software homepages are explanatory links,
not substitutes for an exact environment pin.
