import hashlib
import json
import tomllib
from pathlib import Path

RELEASE = Path(__file__).parents[1] / "publications/20261017.1"


def test_sky_publication_authenticates_hosted_payload_and_its_recipe():
    manifest = tomllib.loads((RELEASE / "manifest.toml").read_text())
    product = json.loads((RELEASE / "product.json").read_text())
    receipt = json.loads((RELEASE / "evidence/hosting.json").read_text())
    assert manifest["publication_kind"] == "evolving-series"
    assert manifest["series_id"] == "fis.sky.deep-star-maps-2020-celestial"
    assert manifest["scope"]["consumer_opt_in_required"] is True
    assert manifest["scope"]["star_catalog_included"] is False
    assert manifest["scope"]["scientific_photometry"] is False
    assert product["projection"] == {"type": "plate-carree", "frame": "ICRF/J2000",
        "centreRaDegrees": 0, "raIncreases": "left", "north": "top", "width": 4096, "height": 2048}
    for name, field in [("prepare.mjs", "scriptSha256"), ("package-lock.json", "lockfileSha256")]:
        assert hashlib.sha256((RELEASE / "recipe" / name).read_bytes()).hexdigest() == product["preparation"][field]
    assert product["preparation"]["commit"] == manifest["producer"]["commit"]
    rows = {row["path"]: row for row in receipt["objects"]}
    image = product["output"]
    assert rows[image["path"]]["url"] == manifest["payload"]["url"]
    assert rows[image["path"]]["sha256"] == image["sha256"] == manifest["payload"]["sha256"]
    assert rows[image["path"]]["bytes"] == image["bytes"] == manifest["payload"]["bytes"]
    assert "/20261017.1/" in manifest["payload"]["url"]
    for line in (RELEASE / "payload-checksums.sha256").read_text().splitlines():
        checksum, name = line.split("  ", 1)
        assert rows[name]["sha256"] == checksum
        assert rows[name]["status"] == 200
        assert rows[name]["cors"] == "*"
        assert rows[name]["cache_control"] == "public, max-age=31536000, immutable"
    assert not list(RELEASE.glob("*.webp"))


def test_sky_publication_checksums_cover_all_publication_files():
    recorded = dict((name, checksum) for checksum, name in
                    (line.split("  ", 1) for line in (RELEASE / "checksums.sha256").read_text().splitlines()))
    actual = {path.relative_to(RELEASE).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in RELEASE.rglob("*") if path.is_file() and "node_modules" not in path.parts
              and path.name != "checksums.sha256"}
    assert actual == recorded
