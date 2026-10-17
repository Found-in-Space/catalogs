"""Record a prepared, S3-verified sky product in its catalog publication."""

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    assert not subprocess.check_output(["git", "status", "--porcelain"], cwd=root).strip(), "Use a clean producer checkout"
    product = json.loads((args.payload / "product.json").read_text())
    receipt = json.loads(args.receipt.read_text())
    release = product["release"]
    assert release in {"20261017.1", "20261017.2"}
    target = root / "publications" / release
    assert not (target / "manifest.toml").exists(), "Published records are immutable; use a new release"
    image = product["output"]
    remote = {row["path"]: row for row in receipt["objects"]}
    images = [image] + [product["polarCaps"][pole] for pole in ["north", "south"] if "polarCaps" in product]
    for entry in images:
        assert remote[entry["path"]]["sha256"] == entry["sha256"]
        assert hashlib.sha256((args.payload / entry["path"]).read_bytes()).hexdigest() == entry["sha256"]
    for name in ["product.json", "checksums.sha256", "LICENSE.txt", "NOTICE.md"]:
        assert hashlib.sha256((args.payload / name).read_bytes()).hexdigest() == remote[name]["sha256"]
    shutil.copyfile(args.payload / "product.json", target / "product.json")
    shutil.copyfile(args.payload / "checksums.sha256", target / "payload-checksums.sha256")
    (target / "evidence").mkdir(exist_ok=True)
    shutil.copyfile(args.receipt, target / "evidence" / "hosting.json")
    prep = product["preparation"]
    q = json.dumps
    manifest = f'''format_version = 1
release = {q(release)}
title = "Deep Star Maps 2020 celestial display texture"
status = "s3-hosted"
publication_kind = "evolving-series"
series_id = "fis.sky.deep-star-maps-2020-celestial"
zenodo_status = "not-deposited"

[scope]
consumer_opt_in_required = true
scientific_photometry = false
runtime_code_included = false
star_catalog_included = false

[source]
page = {q(product['source']['page'])}
url = {q(product['source']['url'])}
sha256 = {q(product['source']['sha256'])}
bytes = {product['source']['bytes']}

[producer]
repository = {q(prep['repository'])}
commit = {q(prep['commit'])}
recipe = {q(prep['recipe'])}
script_sha256 = {q(prep['scriptSha256'])}
lockfile_sha256 = {q(prep['lockfileSha256'])}
three = {q(prep['three'])}
node = {q(prep['node'])}
ffmpeg = {q(prep['ffmpeg'])}

[payload]
url = {q(remote[image['path']]['url'])}
sha256 = {q(image['sha256'])}
bytes = {image['bytes']}
width = {product['projection']['width']}
height = {product['projection']['height']}
content_type = {q(image['contentType'])}
product = "product.json"
checksums = "payload-checksums.sha256"
hosting_evidence = "evidence/hosting.json"

[license]
image = "NASA SVS public-domain usage policy; retain NASA/ESA credits and upstream terms"
original_recipe_and_documentation = "MIT"
notice = "NOTICE.md"
terms = "LICENSE.txt"
'''
    if "polarCaps" in product:
        caps = product["polarCaps"]
        manifest += f'''
[polar_caps]
projection = {q(caps['projection'])}
half_angle_degrees = {caps['halfAngleDegrees']}
blend_start_declination_degrees = {caps['blendStartDeclinationDegrees']}
blend_end_declination_degrees = {caps['blendEndDeclinationDegrees']}
projection_sha256 = {q(prep['projectionSha256'])}
'''
        for pole in ["north", "south"]:
            cap = caps[pole]
            manifest += f'''
[polar_caps.{pole}]
url = {q(remote[cap['path']]['url'])}
sha256 = {q(cap['sha256'])}
bytes = {cap['bytes']}
width = {cap['width']}
height = {cap['height']}
'''
    (target / "manifest.toml").write_text(manifest)
    (target / "run_log.md").write_text(f'''# Run log

Release `{release}`. Source, conversion code and output are authenticated by
`product.json`; hosting was verified at `{receipt['verified_at']}`.

Producer repository: {prep['repository']}

Producer commit: `{prep['commit']}` (clean checkout).

The admitted source was the NASA celestial 4k EXR, SHA-256
`{product['source']['sha256']}` ({product['source']['bytes']} bytes).
The recipe independently installed the public `three@{prep['three']}` release
using its own npm lockfile. Its resolved package location and version were
checked by the recipe; no local Geant or SkyKit implementation was imported.

Commands, with replaceable external paths:

```sh
cd publications/{release}/recipe
npm ci --ignore-scripts
node prepare.mjs /path/to/starmap_2020_4k.exr /path/to/new-product
cd ../../..
uv run --no-project scripts/publish_sky_image.py --payload /path/to/new-product \\
  --publish --profile <aws-profile> --receipt /path/to/hosting.json
uv run --no-project scripts/record_sky_image.py --payload /path/to/new-product \\
  --receipt /path/to/hosting.json
```

Tools: Node `{prep['node']}`, Three.js `{prep['three']}`;
`{prep['ffmpeg']}`. The host's FFmpeg/libwebp is an external encoder rather
than a hermetic dependency. The payload hash identifies the exact result.

Output: `{image['path']}`, {image['bytes']} bytes, SHA-256
`{image['sha256']}`. Conversion: {prep['transform']}; {prep['encoding']}.

Additional images: {json.dumps(images[1:], sort_keys=True)}.

The uploader checked every payload file locally, refused conflicting S3
objects, used conditional writes, and verified all {len(receipt['objects'])} objects via S3
SHA-256 and complete CDN responses. Content types, immutable caching and CORS
are recorded in `evidence/hosting.json`. No bucket policy was changed.

This is an S3-hosted catalog publication. No Zenodo deposit, DOI, headset
acceptance, or scientific value preservation is claimed.
''')
    files = sorted(path for path in target.rglob("*") if path.is_file()
                   and "node_modules" not in path.parts and path.name != "checksums.sha256")
    (target / "checksums.sha256").write_text("".join(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(target).as_posix()}\n"
        for path in files))
    print(json.dumps({"release": release, "publication_files": len(files), "payload_bytes": sum(row["bytes"] for row in images)}))


if __name__ == "__main__":
    main()
