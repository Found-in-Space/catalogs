# Attribution and interpretation notice

Release: `20261011.1`

The upstream imagery is the LROC WAC global morphology mosaic distributed by
USGS Astrogeology. Credit the LROC Team at Arizona State University, NASA's
Lunar Reconnaissance Orbiter mission, and USGS Astrogeology Science Center.
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

Upstream product-specific reuse terms are not established by this candidate.
Before image distribution, record the applicable terms and their primary-source
evidence. General USGS copyright guidance explicitly distinguishes USGS works
from third-party images hosted on its site:
https://www.usgs.gov/faqs/are-usgs-reportspublications-copyrighted

Found in Space original publication metadata is CC BY 4.0; copied producer
definitions remain MIT. Neither licence silently relicenses source imagery.
