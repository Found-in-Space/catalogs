# References for Publication 20260515.1

Publication: Gaia-HIP supplemental display de-duplication map

Release: `20260515.1`

This publication depends on the source catalogues, archive tables, and
scientific publications listed below. See `NOTICE.md` for credit and license
notes.

## Source Catalogues And Archive Tables

- ESA Gaia Archive, Gaia Data Release 3, `gaiadr3.gaia_source`.
  Used for Gaia source identifiers, sky positions, photometry, parallax, and
  parallax uncertainty in the raw display-matching scan.
  Documentation: https://gea.esac.esa.int/archive/documentation/GDR3/

- ESA Gaia Archive, Gaia Data Release 3,
  `gaiadr3.hipparcos2_best_neighbour`.
  Used as the official Gaia-Hipparcos2 best-neighbour baseline crossmatch.
  Documentation: https://gea.esac.esa.int/archive/documentation/GDR3/

- ESA Gaia Archive, Gaia Data Release 3,
  `gaiadr3.hipparcos2_neighbourhood`.
  Used as an official good-neighbour/conflict check for local supplemental
  display matches.
  Documentation: https://gea.esac.esa.int/archive/documentation/GDR3/

- Hipparcos-2 / "Hipparcos, the New Reduction", VizieR catalogue `I/311`.
  Used for Hipparcos source identifiers, epoch J1991.25 positions, proper
  motions, Hipparcos magnitudes, and parallaxes.
  Catalogue page: https://cdsarc.cds.unistra.fr/viz-bin/cat/I/311
  ReadMe: https://cdsarc.u-strasbg.fr/viz-bin/ReadMe/I/311

- VizieR catalogue access service, CDS, Strasbourg, France.
  Used to access the Hipparcos-2 catalogue.
  Service DOI: https://doi.org/10.26093/cds/vizier

## Required Gaia Citations

- Gaia Collaboration, Prusti, T., de Bruijne, J. H. J., et al. (2016).
  "The Gaia mission." Astronomy & Astrophysics, 595, A1.
  DOI: https://doi.org/10.1051/0004-6361/201629272

- Gaia Collaboration, Vallenari, A., Brown, A. G. A., et al. (2023).
  "Gaia Data Release 3. Summary of the content and survey properties."
  Astronomy & Astrophysics, 674, A1.
  DOI: https://doi.org/10.1051/0004-6361/202243940

Gaia credit and citation instructions:
https://gea.esac.esa.int/archive/documentation/GDR3/Miscellaneous/sec_credit_and_citation_instructions/

## Gaia Crossmatch Methodology

- Marrese, P. M., Marinoni, S., Fabrizio, M., & Altavilla, G. (2017).
  "Gaia Data Release 1. Cross-match with external catalogues: algorithms and
  results." Astronomy & Astrophysics, 605, A105.
  DOI: https://doi.org/10.1051/0004-6361/201629920

- Marrese, P. M., Marinoni, S., Fabrizio, M., Giuffrida, G., et al. (2019).
  "Gaia Data Release 2. Cross-match with external catalogues: algorithms and
  results." Astronomy & Astrophysics, 621, A144.
  DOI: https://doi.org/10.1051/0004-6361/201834142

These papers describe the positional/covariance/local-density matching approach
used for Gaia crossmatches with external catalogues, including sparse
catalogues such as Hipparcos2.

## Hipparcos And Tycho

- ESA (1997). "The Hipparcos and Tycho Catalogues." ESA SP-1200.
  ESA gives this as the correct catalogue reference for the Hipparcos and
  Tycho catalogues.
  ESA catalogue page: https://www.cosmos.esa.int/web/hipparcos/catalogues

- van Leeuwen, F. (2007). "Validation of the new Hipparcos reduction."
  Astronomy & Astrophysics, 474, 653-664.
  DOI: https://doi.org/10.1051/0004-6361:20078357

- van Leeuwen, F. (2007). "Hipparcos, the New Reduction of the Raw Data."
  Astrophysics and Space Science Library, volume 350. Springer.
  DOI: https://doi.org/10.1007/978-1-4020-6342-8

## VizieR/CDS

- Ochsenbein, F., Bauer, P., & Marcout, J. (2000).
  "The VizieR database of astronomical catalogues."
  Astronomy and Astrophysics Supplement Series, 143, 23-32.
  DOI: https://doi.org/10.1051/aas:2000169

## Found-In-Space Release Context

This Found-In-Space publication is a supplemental display de-duplication
catalogue. It should be used alongside, not instead of, the official Gaia
Hipparcos2 best-neighbour table. The published catalog artifact contains only
the Found-In-Space supplemental mapping delta.
