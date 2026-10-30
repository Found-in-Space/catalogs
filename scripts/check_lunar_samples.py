"""Representative checks using public historical CRS resources and recorded GDAL operations."""

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import time

import argparse
import sys

parser = argparse.ArgumentParser(
    description="Check representative lunar source windows without rebuilding the pyramid."
)
parser.add_argument("--run-root", type=Path, required=True)
parser.add_argument("--producer-root", type=Path, required=True)
parser.add_argument("--scratch-root", type=Path, required=True)
parser.add_argument("--report", type=Path, required=True)
args = parser.parse_args()
run = args.run_root.resolve()
repo = args.producer_root.resolve()
scratch = args.scratch_root.resolve()
assert not args.report.exists(), "Never overwrite a report"
repository = Path(__file__).resolve().parents[1]


def git(root, *arguments):
    return subprocess.check_output(
        ["git", "-C", str(root), *arguments], text=True
    ).strip()


assert not git(repository, "status", "--porcelain", "--untracked-files=all"), (
    "Use a clean checkout"
)
sampler_commit = git(repository, "rev-parse", "HEAD")
assert git(repository, "branch", "-r", "--contains", sampler_commit), (
    "Push check code before recording evidence"
)
assert not git(repo, "status", "--porcelain", "--untracked-files=all"), (
    "Use clean producer resources"
)
product = json.loads((run / "output/product.json").read_text())
producer_commit = product["producer"]["git_sha"]
scratch.mkdir(exist_ok=False)
resources = scratch / "resources"
resources.mkdir()
for name in ("moon-simple-cylindrical-1737400.wkt", "moon-geographic-1737400.wkt"):
    (resources / name).write_bytes(
        subprocess.check_output(
            ["git", "-C", str(repo), "show", f"{producer_commit}:resources/crs/{name}"]
        )
    )
env = {"GDAL_PAM_ENABLED": "NO"}
import os

environment = dict(os.environ, **env)
commands = []


def execute(argv):
    start = time.monotonic()
    process = subprocess.run(
        [str(a) for a in argv],
        env=environment,
        text=True,
        capture_output=True,
        check=True,
    )
    commands.append(
        {
            "argv": [str(a) for a in argv],
            "seconds": time.monotonic() - start,
            "stderr": process.stderr,
        }
    )


def pixels(source, destination, window=None):
    args = ["gdal_translate", "-q", "-of", "PNM", "-ot", "Byte", "-a_nodata", "none"]
    if window:
        args += ["-srcwin", *window]
    execute([*args, source, destination])
    # GDAL's PNM output has a fixed three-line header for these Byte rasters.
    with destination.open("rb") as stream:
        assert stream.readline().strip() == b"P5"
        dimensions = tuple(int(v) for v in stream.readline().split())
        assert stream.readline().strip() == b"255"
        data = stream.read()
    assert len(data) == dimensions[0] * dimensions[1]
    return data


results = {
    "started_at": datetime.now(timezone.utc).isoformat(),
    "scope": "Representative same-host process checks. Exact matches are observations, not regeneration requirements. No full independent rebuild is claimed.",
    "base_reprojection": [],
    "pyramid_averaging": [],
    "png_emission": [],
}
source = run / "source/Lunar_LRO_LROC-WAC_Mosaic_global_100m_June2013.tif"
source_crs = resources / "moon-simple-cylindrical-1737400.wkt"
target_crs = resources / "moon-geographic-1737400.wkt"
base = run / "work/levels/8.tif"

for x, y in [(0, 0), (255, 255), (128, 128), (127, 42)]:
    directory = scratch / f"base-8-{x}-{y}"
    directory.mkdir()
    west = -180 + 360 * x / 256
    east = -180 + 360 * (x + 1) / 256
    north = 90 - 180 * y / 256
    south = 90 - 180 * (y + 1) / 256
    rebuilt = directory / "reprojected.tif"
    execute(
        [
            "gdalwarp",
            "-q",
            "-of",
            "GTiff",
            "-ot",
            "Byte",
            "-s_srs",
            source_crs,
            "-t_srs",
            target_crs,
            "-te_srs",
            target_crs,
            "-te",
            west,
            south,
            east,
            north,
            "-ts",
            512,
            512,
            "-r",
            "bilinear",
            "-srcnodata",
            "0.0",
            "-dstnodata",
            "0",
            "-wm",
            1024,
            "-wo",
            "NUM_THREADS=4",
            source,
            rebuilt,
        ]
    )
    actual = pixels(rebuilt, directory / "actual.pgm")
    expected = pixels(base, directory / "expected.pgm", [x * 512, y * 512, 512, 512])
    differences = sum(a != b for a, b in zip(actual, expected))
    results["base_reprojection"].append(
        {
            "tile": [8, x, y],
            "pixels_compared": len(actual),
            "pixels_different": differences,
            "actual_pixels_sha256": sha256(actual).hexdigest(),
            "expected_pixels_sha256": sha256(expected).hexdigest(),
        }
    )

for z in range(8):
    directory = scratch / f"average-z{z}"
    directory.mkdir()
    dimension = 512 * (1 << z)
    xoff = dimension // 2 - 8
    yoff = dimension // 2 - 8
    factor = 1 << (8 - z)
    rebuilt = directory / "averaged.tif"
    execute(
        [
            "gdal_translate",
            "-q",
            "-of",
            "GTiff",
            "-ot",
            "Byte",
            "-srcwin",
            xoff * factor,
            yoff * factor,
            16 * factor,
            16 * factor,
            "-outsize",
            16,
            16,
            "-r",
            "average",
            base,
            rebuilt,
        ]
    )
    actual = pixels(rebuilt, directory / "actual.pgm")
    expected = pixels(
        run / f"work/levels/{z}.tif", directory / "expected.pgm", [xoff, yoff, 16, 16]
    )
    results["pyramid_averaging"].append(
        {
            "zoom": z,
            "level_window": [xoff, yoff, 16, 16],
            "base_window": [xoff * factor, yoff * factor, 16 * factor, 16 * factor],
            "pixels_compared": len(actual),
            "pixels_different": sum(a != b for a, b in zip(actual, expected)),
            "actual_pixels_sha256": sha256(actual).hexdigest(),
            "expected_pixels_sha256": sha256(expected).hexdigest(),
        }
    )

for z, x, y in [(0, 0, 0), (4, 8, 8), (8, 0, 0), (8, 128, 128)]:
    directory = scratch / f"png-{z}-{x}-{y}"
    directory.mkdir()
    tile_root = directory / "tiles"
    tile_root.mkdir()
    vrt = directory / "window.vrt"
    execute(
        [
            "gdal_translate",
            "-q",
            "-of",
            "VRT",
            "-a_nodata",
            "none",
            "-srcwin",
            x * 512,
            y * 512,
            512,
            512,
            run / f"work/levels/{z}.tif",
            vrt,
        ]
    )
    execute(
        [
            "gdal_retile.py",
            "-q",
            "-of",
            "PNG",
            "-ot",
            "Byte",
            "-ps",
            512,
            512,
            "-overlap",
            0,
            "-co",
            "ZLEVEL=6",
            "-useDirForEachRow",
            "-targetDir",
            tile_root,
            vrt,
        ]
    )
    emitted = list(tile_root.rglob("*.png"))
    assert len(emitted) == 1
    actual = emitted[0].read_bytes()
    existing = run / f"output/imagery/{z}/{x}/{y}.png"
    expected = existing.read_bytes()
    actual_pixels = pixels(emitted[0], directory / "actual.pgm")
    expected_pixels = pixels(existing, directory / "expected.pgm")
    results["png_emission"].append(
        {
            "tile": [z, x, y],
            "png_bytes_equal": actual == expected,
            "actual_png_sha256": sha256(actual).hexdigest(),
            "expected_png_sha256": sha256(expected).hexdigest(),
            "pixels_different": sum(
                a != b for a, b in zip(actual_pixels, expected_pixels)
            ),
        }
    )


def portable(value):
    if isinstance(value, dict):
        return {key: portable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [portable(item) for item in value]
    if isinstance(value, str):
        for root, token in (
            (scratch, "${SAMPLE_ROOT}"),
            (run, "${RUN_ROOT}"),
            (repo, "${PRODUCER_ROOT}"),
        ):
            value = value.replace(str(root), token)
    return value


results["format_version"] = 1
results["sampler_repository"] = "https://github.com/Found-in-Space/catalogs"
results["sampler_commit"] = sampler_commit
results["producer_commit"] = producer_commit
results["product_identity_sha256"] = product["product_identity_sha256"]
results["product_json_sha256"] = sha256(
    (run / "output/product.json").read_bytes()
).hexdigest()
results["commands"] = portable(commands)
results["runtime"] = {
    "python": sys.version.split()[0],
    "uv": subprocess.check_output(["uv", "--version"], text=True).strip(),
    "gdal": subprocess.check_output(["gdalinfo", "--version"], text=True).strip(),
    "proj": subprocess.run(
        ["proj"], text=True, capture_output=True
    ).stderr.splitlines()[0],
    "gdal_retile_runtime": "system Python from its installed wrapper; separate from sampler Python",
}
results["source_to_base_and_direct_lower_levels_checked"] = True
results["byte_identical_regeneration_required"] = False
results["full_independent_rebuild_performed"] = False
results["finished_at"] = datetime.now(timezone.utc).isoformat()
args.report.parent.mkdir(parents=True, exist_ok=True)
args.report.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
print(
    json.dumps(
        {key: value for key, value in results.items() if key != "commands"}, indent=2
    )
)
