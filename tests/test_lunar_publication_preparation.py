"""Exercise authentication and portability of publication preparation."""

import hashlib
import json
import runpy
from pathlib import Path

import pytest

TOOL = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "scripts/prepare_lunar_publication.py")
)


def fixture_product(tmp_path):
    output = tmp_path / "output"
    tile = output / "imagery/0/0/0.png"
    tile.parent.mkdir(parents=True)
    tile.write_bytes(b"test payload")
    checksum = TOOL["sha256"](tile)
    manifest = output / "manifests/tiles-z0.sha256"
    manifest.parent.mkdir()
    manifest.write_text(f"{checksum}  imagery/0/0/0.png\n")
    digest = TOOL["sha256"](manifest)
    manifest_set = [{"zoom": 0, "manifest_sha256": digest}]
    product = {
        "product_identity_sha256": "a" * 64,
        "manifest_set_sha256": hashlib.sha256(
            json.dumps(manifest_set, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "levels": [
            {
                "zoom": 0,
                "tile_count": 1,
                "tile_bytes": tile.stat().st_size,
                "manifest": "manifests/tiles-z0.sha256",
                "manifest_sha256": digest,
            }
        ],
        "tiles": {
            "minimum_zoom": 0,
            "maximum_zoom": 0,
            "total_count": 1,
            "total_bytes": tile.stat().st_size,
        },
    }
    (output / "product.json").write_text(json.dumps(product))
    validation = {
        "valid": True,
        "checks": {"exact_reconstruction": True},
        "product_json_sha256": TOOL["sha256"](output / "product.json"),
        "product_identity_sha256": product["product_identity_sha256"],
        "tile_count": 1,
        "tile_bytes": tile.stat().st_size,
    }
    return output, tile, product, validation


def test_authenticate_payload_and_detect_same_size_corruption(tmp_path):
    output, tile, product, validation = fixture_product(tmp_path)
    rows = TOOL["verify_tiles"](output, product, validation)
    assert rows[0]["count"] == 1
    assert rows[0]["bytes"] == len(b"test payload")
    tile.write_bytes(b"fake payload")
    with pytest.raises(ValueError, match="Tile checksum mismatch"):
        TOOL["verify_tiles"](output, product, validation)


def test_manifest_traversal_and_unlisted_files_are_rejected(tmp_path):
    output, tile, product, validation = fixture_product(tmp_path)
    extra = tile.with_name("extra.png")
    extra.write_bytes(b"unlisted")
    with pytest.raises(ValueError, match="Unexpected imagery files"):
        TOOL["verify_tiles"](output, product, validation)
    extra.unlink()
    manifest = output / product["levels"][0]["manifest"]
    manifest.write_text(f"{'a' * 64}  ../../private.png\n")
    product["levels"][0]["manifest_sha256"] = TOOL["sha256"](manifest)
    with pytest.raises(ValueError, match="Invalid tile manifest entry"):
        TOOL["verify_tiles"](output, product, validation)


def test_failed_or_changed_pixel_validation_is_rejected(tmp_path):
    output, _, product, validation = fixture_product(tmp_path)
    validation["checks"]["exact_reconstruction"] = False
    with pytest.raises(ValueError, match="Incomplete tile checks"):
        TOOL["verify_tiles"](output, product, validation)
    validation["checks"]["exact_reconstruction"] = True
    validation["product_json_sha256"] = "b" * 64
    with pytest.raises(ValueError, match="differs from validated"):
        TOOL["verify_tiles"](output, product, validation)


def test_portable_paths_keep_distinct_roles_and_embedded_stdout():
    run = Path("/data/runs/moon")
    producer = Path("/data/work/producer")
    evidence = {
        "commands": [
            "gdalwarp",
            "/data/runs/moon/source/input.tif",
            "/data/runs/moon/work/input.tif",
        ],
        "stdout": "Processing /data/runs/moon/source/input.tif [1/1] : complete\n",
        "crs": "/data/work/producer/resources/crs/moon.wkt",
        "url": "https://planetarymaps.usgs.gov/mosaic/input.tif",
    }
    result = TOOL["portable"](evidence, run, producer)
    assert result["commands"][1:] == [
        "${RUN_ROOT}/source/input.tif",
        "${RUN_ROOT}/work/input.tif",
    ]
    assert (
        result["stdout"] == "Processing ${RUN_ROOT}/source/input.tif [1/1] : complete\n"
    )
    assert result["crs"] == "${PRODUCER_ROOT}/resources/crs/moon.wkt"
    assert result["url"] == evidence["url"]
    assert evidence["commands"][1] == "/data/runs/moon/source/input.tif"


def test_complete_log_text_keeps_failed_attempt_and_public_url():
    text = (
        "Error: could not download https://planetarymaps.usgs.gov/mosaic/input.tif: timed out\n"
        '{"path": "/data/runs/moon/source/input.tif", "resumed": true}\n'
    )
    result = TOOL["portable"](
        text, Path("/data/runs/moon"), Path("/data/work/producer")
    )
    assert result.startswith(
        "Error: could not download https://planetarymaps.usgs.gov/"
    )
    assert '"path": "${RUN_ROOT}/source/input.tif"' in result
    assert result.endswith('"resumed": true}\n')


@pytest.mark.parametrize(
    "value",
    [
        "/home/person/private",
        "https://secret.example/data",
        "https://user:password@planetarymaps.usgs.gov/mosaic/file.tif",
        "https://planetarymaps.usgs.gov/mosaic/file.tif?token=secret",
    ],
)
def test_unmapped_paths_and_unreviewed_urls_are_rejected(value):
    with pytest.raises(ValueError):
        TOOL["portable"](value, Path("/data/runs/moon"), Path("/data/work/producer"))


def test_checksums_exclude_post_publication_tracking(tmp_path):
    (tmp_path / "README.md").write_text("public metadata")
    (tmp_path / "zenodo").mkdir()
    (tmp_path / "zenodo/published-record.toml").write_text("later DOI bookkeeping")
    TOOL["regenerate_checksums"](tmp_path)
    checksums = (tmp_path / "checksums.sha256").read_text()
    assert checksums == f"{TOOL['sha256'](tmp_path / 'README.md')}  README.md\n"
