# Run log

Release `20261017.1`. Source, conversion code and output are authenticated by
`product.json`; hosting was verified at `2026-10-17T14:09:23.813898+00:00`.

Producer repository: https://github.com/Found-in-Space/catalogs

Producer commit: `c1616042bab867ad8d0806a082da028e524a8b7e` (clean checkout).

The admitted source was the NASA celestial 4k EXR, SHA-256
`69b841cd048c2ef35543eb1c5819b322530e78aa4b0cab97ec1de3ef56a4ddcd` (35997085 bytes).
The recipe independently installed the public `three@0.170.0` release
using its own npm lockfile. Its resolved package location and version were
checked by the recipe; no local Geant or SkyKit implementation was imported.

Commands, with replaceable external paths:

```sh
cd publications/20261017.1/recipe
npm ci --ignore-scripts
node prepare.mjs /path/to/starmap_2020_4k.exr /path/to/new-product
cd ../../..
uv run --no-project scripts/publish_sky_image.py --payload /path/to/new-product \
  --publish --profile <aws-profile> --receipt /path/to/hosting.json
uv run --no-project scripts/record_sky_image.py --payload /path/to/new-product \
  --receipt /path/to/hosting.json
```

Tools: Node `v24.16.0`, Three.js `0.170.0`;
`ffmpeg version 4.4.2-0ubuntu0.22.04.1 Copyright (c) 2000-2021 the FFmpeg developers`. The host's FFmpeg/libwebp is an external encoder rather
than a hermetic dependency. The payload hash identifies the exact result.

Output: `deep-star-map-2020-4k.webp`, 2552346 bytes, SHA-256
`ceabaafadf77dc9792cf2ad8e3d80d4c3cba069602bee035763fe9ddeefa4ab4`. Conversion: linear RGB clamped to [0,1], IEC sRGB transfer, nearest 8-bit RGB; no resizing or exposure change; reverse EXRLoader rows; WebP, quality 90, compression level 6.

The uploader checked every payload file locally, refused conflicting S3
objects, used conditional writes, and verified all 5 objects via S3
SHA-256 and complete CDN responses. Content types, immutable caching and CORS
are recorded in `evidence/hosting.json`. No bucket policy was changed.

This is an S3-hosted catalog publication. No Zenodo deposit, DOI, headset
acceptance, or scientific value preservation is claimed.
