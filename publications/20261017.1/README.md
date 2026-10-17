# Deep Star Maps 2020: optional celestial display texture

Release `20261017.1` is the first snapshot of the evolving
`fis.sky.deep-star-maps-2020-celestial` series. It supplies one 4096 × 2048
sRGB WebP for an optional, infinitely distant sky background. It contains no
runtime plugin, star catalog, or selectable star objects. Consumers opt in.

The payload is hosted separately from source code at the immutable prefix
<https://data.foundin.space/textures/sky/deep-star-maps-2020/20261017.1/>.
Use [`product.json`](https://data.foundin.space/textures/sky/deep-star-maps-2020/20261017.1/product.json)
for provenance and the authenticated filename, or the
[WebP](https://data.foundin.space/textures/sky/deep-star-maps-2020/20261017.1/deep-star-map-2020-4k.webp)
directly. Hosting is verified in `evidence/hosting.json` once publication
completes. The raw EXR and the generated WebP are excluded from Git.

The projection is celestial plate carree, ICRF/J2000: RA 0 at the centre,
RA increases left, north is at the top. Use camera orientation and the host's
celestial frame rotation, without observer translation or positional parallax.
The image derives from Gaia DR2, rather than the newer Found in Space star
catalog. Clamping, 8-bit conversion and lossy compression make it display
imagery; do not use it as scientific photometry.

## Reproduction

Use a clean checkout of the exact public producer commit recorded in
`product.json`. The recipe uses public Three.js 0.170.0, authenticated by
`recipe/package-lock.json`; it does not import a local SkyKit or Geant checkout.
Install Node.js and FFmpeg with libwebp, then:

```sh
cd publications/20261017.1/recipe
npm ci --ignore-scripts
curl --fail --location --output /path/to/starmap_2020_4k.exr \
  https://svs.gsfc.nasa.gov/vis/a000000/a004800/a004851/starmap_2020_4k.exr
node prepare.mjs /path/to/starmap_2020_4k.exr /path/to/new-product-directory
```

The recipe verifies the admitted input SHA-256 and dimensions, reverses
EXRLoader's rows, clamps linear RGB to [0,1], applies the IEC sRGB transfer,
rounds to 8-bit RGB, and encodes WebP at quality 90 and compression level 6.
It changes neither dimensions nor exposure. `product.json` records exact
source and output hashes, code commit, lockfile, script, and tool versions.
Identical compressed bytes require the recorded FFmpeg/libwebp environment;
a changed product requires a new immutable release.

From the repository root, the publication uploader defaults to a local check:

```sh
uv run --no-project scripts/publish_sky_image.py --payload /path/to/product
# Add --publish --profile <aws-profile> --receipt /path/to/hosting.json
# to upload and verify S3 and CDN checksums, content types, caching, and CORS.
```

`payload-checksums.sha256` authenticates the externally hosted files;
`checksums.sha256` authenticates the publication files kept in Git. The image
plugin remains in Pas de Géant and can use this URL or a caller-hosted copy.
Neither the payload nor its preparation dependencies belong in default app
bundles. Earth-to-stars transitions are outside this publication.

## Citation and rights

Credit NASA/Goddard Space Flight Center Scientific Visualization Studio;
Gaia DR2: ESA/Gaia/DPAC. See `NOTICE.md`, `LICENSE.txt`, and `REFERENCES.md`.
S3 hosting does not alter the image's rights. Cite this exact release and
its public repository commit when reproducibility matters. No Zenodo DOI is
assigned by an S3 upload; a later initial deposit can establish this series'
lineage, with subsequent revisions using Zenodo's New version workflow.
