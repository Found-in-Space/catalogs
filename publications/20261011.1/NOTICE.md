# Attribution and interpretation notice

Release: `20261011.1`

The upstream imagery is the LROC WAC global morphology mosaic distributed by
USGS Astrogeology. Credit NASA/GSFC/Arizona State University, the LROC Team,
and USGS Astrogeology Science Center.
Scientific attribution does not imply endorsement of Found in Space.

Found in Space contributes reprojection, geographic display tiling, the
resolution pyramid, reproducibility records, and publication packaging.
The source imagery remains attributable to its originators.

The source is single-channel morphology imagery. Surface brightness depends
on image acquisition and upstream mosaicking as well as the terrain itself;
these display samples should not be interpreted as elevation or calibrated
reflectance. Source metadata records a byte scale and offset; this producer
does not apply an explicit conversion into physical reflectance values.

Missing source coverage is mapped to opaque black. Reprojection is bilinear,
lower levels are area averages of the maximum-resolution base, and output
values are unsigned 8-bit samples. Consumers should preserve the addressing,
coordinate, resampling, and missing-coverage conventions when describing reuse.

The exact June 2013 USGS product metadata identifies the imagery as public
domain and asks users to cite the authors. The retrieved page identity,
observation date, and relevant fields are in evidence/upstream_reuse_terms.json:
https://astrogeology.usgs.gov/search/map/moon_lro_lroc_wac_global_morphology_mosaic_100m

Found in Space original publication metadata is CC BY 4.0; copied producer
definitions remain MIT. Neither licence silently relicenses source imagery.
