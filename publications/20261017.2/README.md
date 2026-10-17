# Deep Star Maps 2020: celestial display texture with polar caps

Release `20261017.2` is the second snapshot of the evolving
`fis.sky.deep-star-maps-2020-celestial` series. It adds two 1024 × 1024 polar
images to the 4096 × 2048 map from `20261017.1`. The preceding release and its
S3 objects remain immutable. This release contains no runtime plugin, star
catalog or selectable objects; all consumers opt in.

The payload uses the immutable prefix
<https://data.foundin.space/textures/sky/deep-star-maps-2020/20261017.2/>.
[`product.json`](https://data.foundin.space/textures/sky/deep-star-maps-2020/20261017.2/product.json)
records every image's filename, SHA-256, size, projection and source. Generated
images and the raw EXR stay outside Git. `evidence/hosting.json` records S3/CDN
verification after upload. `payload-checksums.sha256` authenticates those
external files; `checksums.sha256` covers the publication files in Git.

## Projection and display

The main image is ICRF/J2000 plate carree: RA 0 at centre, RA increases left,
north at the top. Each cap uses a gnomonic projection centred on J2000 +Z
(north) or -Z (south). Both images have +X to the right and +Y at the top.
For a normalized direction `d`, cap UV is
`0.5 + 0.5 * d.xy / (abs(d.z) * tan(35 degrees))`, with image top at v=1.
The square has a 35-degree half-angle along each axis; its corners extend
farther from the pole. Image sample coordinates refer to pixel centres.

Blend the main map into the appropriate cap using
`smoothstep(sin(60 degrees), sin(65 degrees), abs(d.z))`. At declinations
above ±65 degrees, use only the cap. This removes the longitude singularity
and its stretched mip footprint from the visible pole. Both caps overlap the
transition with a sampling margin. Match celestial rotation and camera
orientation without positional parallax.

Caps are reprojected from the **original linear EXR**, with longitude wrapping,
latitude clamping and bilinear interpolation before display conversion. They
are not resampled from the lossy WebP. Cap WebP encoding is lossless to avoid
adding compression blocks to the new projection. The main image retains the
same quality-90 conversion and pixel identity as `20261017.1`.

These are clamped, 8-bit display images derived from Gaia DR2 and the other
catalogs credited by NASA, not scientific photometry or the current Found in
Space star catalog. The two RGBA caps occupy 8 MiB before mipmaps, in addition
to the 32 MiB main map. Physical headset visual acceptance is separate.

## Reproduction and publication

Use a clean checkout of the public producer commit in `product.json`:

```sh
cd publications/20261017.2/recipe
npm ci --ignore-scripts
node --test projection.test.mjs
node prepare.mjs /path/to/starmap_2020_4k.exr /path/to/new-product
cd ../../..
uv run --no-project scripts/publish_sky_image.py --payload /path/to/new-product
# Add --publish --profile <aws-profile> --receipt /path/to/hosting.json
uv run --no-project scripts/record_sky_image.py --payload /path/to/new-product \
  --receipt /path/to/hosting.json
```

The admitted input is the same NASA celestial 4k EXR as in `20261017.1`:
<https://svs.gsfc.nasa.gov/vis/a000000/a004800/a004851/starmap_2020_4k.exr>.
The recipe verifies its hash and dimensions, the locked public Three.js
package location/version, and a clean code checkout. No Geant or SkyKit source
is imported. Encoder/tool versions and script, projection, lockfile and image
hashes are generated. Identical encoded bytes require the recorded FFmpeg/
libwebp environment; changed artifacts require another immutable release.

Credit NASA/Goddard Space Flight Center Scientific Visualization Studio;
Gaia DR2: ESA/Gaia/DPAC. See `LICENSE.txt`, `NOTICE.md` and `REFERENCES.md`.
S3 hosting changes neither rights nor attribution. No Zenodo deposit or DOI
has been created; any future deposit continues the same series lineage.
