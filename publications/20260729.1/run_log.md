# Run Log

Release: `20260729.1`

This is a small authored reference publication rather than a generated
survey-catalog product.

## Source Review

The selected values were checked against the public primary references:

- Willmer (2018), DOI `10.3847/1538-4365/aabfdf`, for Johnson V vegamag
  absolute magnitude `4.81`;
- IAU 2015 Resolution B3 and Prsa et al. (2016), DOI
  `10.3847/0004-6256/152/2/41`, for nominal effective temperature `5772 K`.

The previously public pipeline record at commit
`9c014848a7a99f6d93583ae7dfa51a740733fa9c` was reviewed as migration context.
The publication does not import or execute code from a local pipeline checkout.

## Authored Product

`catalog/fis_solar_reference.yaml` was authored to separate:

- published solar physical/reference values;
- optional synthetic placement at the solar coordinate origin; and
- core external-star catalog membership, which is explicitly false.

No Gaia, Hipparcos, VizieR, or other survey-catalog payload is included.

## Validation

From the `catalogs` repository:

```bash
uv run pytest
sha256sum --check publications/20260729.1/checksums.sha256
```

The publication-specific tests validate the manifest, one-entry count, opt-in
scope, cited values, nominal-value interpretation, and synthetic-placement
label.

`checksums.sha256` is generated from the final publication files and does not
include itself.
