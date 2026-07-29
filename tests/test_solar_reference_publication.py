import hashlib
from pathlib import Path

import tomllib
import yaml

RELEASE_DIR = Path(__file__).parents[1] / "publications" / "20260729.1"


def test_solar_reference_publication_is_opt_in_and_self_consistent():
    with (RELEASE_DIR / "manifest.toml").open("rb") as stream:
        manifest = tomllib.load(stream)
    catalog = yaml.safe_load(
        (RELEASE_DIR / "catalog" / "fis_solar_reference.yaml").read_text(
            encoding="utf-8"
        )
    )

    assert manifest["release"] == "20260729.1"
    assert manifest["scope"]["catalog_entries"] == 1
    assert manifest["scope"]["core_catalog_member"] is False
    assert manifest["scope"]["core_octree_member"] is False
    assert manifest["scope"]["pipeline_override"] is False
    assert manifest["scope"]["automatic_merge"] is False
    assert manifest["scope"]["consumer_opt_in_required"] is True

    assert catalog["catalog"]["catalog_id"] == "fis.solar-reference"
    assert catalog["catalog"]["release"] == manifest["release"]
    assert catalog["catalog"]["provider_id"] == "fis.solar-reference"
    assert catalog["catalog"]["core_catalog_member"] is False
    assert catalog["catalog"]["core_octree_member"] is False
    assert catalog["catalog"]["automatic_merge"] is False
    assert catalog["catalog"]["consumer_opt_in_required"] is True

    assert len(catalog["stars"]) == 1
    sun = catalog["stars"][0]
    assert sun["object_id"] == "sun"
    assert sun["provenance_kind"] == "published_reference"
    assert sun["identifiers"]["proper_name"] == "Sun"

    magnitude = sun["physical_values"]["absolute_magnitude"]
    assert magnitude["value"] == 4.81
    assert magnitude["bandpass"] == "Johnson_V"
    assert magnitude["magnitude_system"] == "vegamag"
    assert magnitude["source"]["doi"] == "10.3847/1538-4365/aabfdf"

    temperature = sun["physical_values"]["effective_temperature"]
    assert temperature["value"] == 5772
    assert temperature["unit"] == "K"
    assert temperature["value_kind"] == "nominal_exact_conversion_constant"
    assert temperature["exact_by_definition"] is True
    assert temperature["source"]["doi"] == "10.3847/0004-6256/152/2/41"

    placement = sun["default_session_placement"]
    assert placement["optional"] is True
    assert placement["placement_kind"] == "synthetic_coordinate_origin"
    assert (
        placement["x_icrs_pc"],
        placement["y_icrs_pc"],
        placement["z_icrs_pc"],
    ) == (0.0, 0.0, 0.0)

    policy = sun["consumer_policy"]
    assert policy["include_automatically"] is False
    assert policy["may_omit"] is True
    assert policy["may_replace"] is True


def test_solar_reference_publication_checksums_cover_every_release_file():
    checksum_path = RELEASE_DIR / "checksums.sha256"
    recorded = {}
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        digest, relative_path = line.split(maxsplit=1)
        recorded[relative_path] = digest

    expected_files = {
        path.relative_to(RELEASE_DIR).as_posix()
        for path in RELEASE_DIR.rglob("*")
        if path.is_file() and path != checksum_path
    }
    assert set(recorded) == expected_files

    for relative_path, expected_digest in recorded.items():
        actual_digest = hashlib.sha256(
            (RELEASE_DIR / relative_path).read_bytes()
        ).hexdigest()
        assert actual_digest == expected_digest
