# References for Publication 20260729.1

Publication: Optional solar reference
Release: `20260729.1`

## Johnson V Absolute Magnitude

Willmer, C. N. A. (2018), "The Absolute Magnitude of the Sun in Several
Filters," *The Astrophysical Journal Supplement Series*, 236, 47.

- DOI: https://doi.org/10.3847/1538-4365/aabfdf
- arXiv: https://arxiv.org/abs/1804.07788

Willmer reports `M_V = 4.81` for the Sun in Johnson V using the vegamag system.
The publication uses that passband-specific value and does not treat it as a
bolometric or Gaia G magnitude.

## Nominal Effective Temperature

Prsa, A., Harmanec, P., Torres, G., et al. (2016), "Nominal Values for Selected
Solar and Planetary Quantities: IAU 2015 Resolution B3," *The Astronomical
Journal*, 152, 41.

- DOI: https://doi.org/10.3847/0004-6256/152/2/41
- arXiv: https://arxiv.org/abs/1605.09788

IAU 2015 Resolution B3:

- Resolution text: https://www.iau.org/static/resolutions/IAU2015_English.pdf
- Resolution preprint: https://arxiv.org/abs/1510.07674

The resolution adopts the nominal solar effective temperature `5772 K` as an
exact SI conversion constant. It is not a claim that an instantaneous physical
estimate of the Sun has zero uncertainty.

## Found in Space Migration Context

The same value selection was previously carried by the public Found in Space
pipeline at commit:

`9c014848a7a99f6d93583ae7dfa51a740733fa9c`

in:

`src/foundinspace/pipeline/overrides/data/sun.yaml`

This publication separates those reference values from pipeline behavior and
from membership in the core external-star catalog.
