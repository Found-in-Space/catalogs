import hashlib
import json
import math
import tomllib
from pathlib import Path

import pytest


@pytest.fixture(params=["20261017.1", "20261017.2"])
def release(request):
    return Path(__file__).parents[1] / "publications" / request.param


def test_sky_publication_authenticates_hosted_payload_and_its_recipe(release):
    manifest = tomllib.loads((release / "manifest.toml").read_text())
    product = json.loads((release / "product.json").read_text())
    receipt = json.loads((release / "evidence/hosting.json").read_text())
    assert manifest["publication_kind"] == "evolving-series"
    assert manifest["series_id"] == "fis.sky.deep-star-maps-2020-celestial"
    assert manifest["scope"]["consumer_opt_in_required"] is True
    assert manifest["scope"]["star_catalog_included"] is False
    assert manifest["scope"]["scientific_photometry"] is False
    assert product["projection"] == {"type": "plate-carree", "frame": "ICRF/J2000",
        "centreRaDegrees": 0, "raIncreases": "left", "north": "top", "width": 4096, "height": 2048}
    for name, field in [("prepare.mjs", "scriptSha256"), ("package-lock.json", "lockfileSha256")]:
        assert hashlib.sha256((release / "recipe" / name).read_bytes()).hexdigest() == product["preparation"][field]
    assert product["preparation"]["commit"] == manifest["producer"]["commit"]
    rows = {row["path"]: row for row in receipt["objects"]}
    image = product["output"]
    assert rows[image["path"]]["url"] == manifest["payload"]["url"]
    assert rows[image["path"]]["sha256"] == image["sha256"] == manifest["payload"]["sha256"]
    assert rows[image["path"]]["bytes"] == image["bytes"] == manifest["payload"]["bytes"]
    assert f"/{release.name}/" in manifest["payload"]["url"]
    for line in (release / "payload-checksums.sha256").read_text().splitlines():
        checksum, name = line.split("  ", 1)
        assert rows[name]["sha256"] == checksum
        assert rows[name]["status"] == 200
        assert rows[name]["cors"] == "*"
        assert rows[name]["cache_control"] == "public, max-age=31536000, immutable"
    assert not list(release.glob("*.webp"))
    if "polarCaps" in product:
        caps = product["polarCaps"]
        assert hashlib.sha256((release / "recipe/projection.mjs").read_bytes()).hexdigest() == product["preparation"]["projectionSha256"]
        assert product["preparation"]["projectionSha256"] == manifest["polar_caps"]["projection_sha256"]
        assert caps["rightAxis"] == "+X" and caps["topAxis"] == "+Y"
        assert caps["northAxis"] == "+Z" and caps["southAxis"] == "-Z"
        # The entire blend band must lie inside the cap images, including a margin.
        start = math.radians(caps["blendStartDeclinationDegrees"])
        extent = math.tan(math.radians(caps["halfAngleDegrees"]))
        assert math.tan(math.pi / 2 - start) / extent < 1
        for pole in ["north", "south"]:
            cap = caps[pole]
            assert manifest["polar_caps"][pole]["url"] == rows[cap["path"]]["url"]
            assert cap["sha256"] == rows[cap["path"]]["sha256"] == manifest["polar_caps"][pole]["sha256"]
            assert cap["bytes"] == rows[cap["path"]]["bytes"]
        previous = json.loads((release.parent / "20261017.1/product.json").read_text())
        assert image["sha256"] == previous["output"]["sha256"]


def test_sky_publication_checksums_cover_all_publication_files(release):
    recorded = dict((name, checksum) for checksum, name in
                    (line.split("  ", 1) for line in (release / "checksums.sha256").read_text().splitlines()))
    actual = {path.relative_to(release).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in release.rglob("*") if path.is_file() and "node_modules" not in path.parts
              and path.name != "checksums.sha256"}
    assert actual == recorded
