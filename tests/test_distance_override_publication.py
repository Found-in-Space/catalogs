from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import tomllib
import yaml
from foundinspace.pipeline.overrides.pipeline import build_overrides_dataframe

RELEASE_DIR = Path(__file__).parents[1] / "publications" / "20260730.1"
CATALOG_PATH = RELEASE_DIR / "catalog" / "distance_resolution_v1_resolved.yaml"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_distance_override_publication_selection_and_runtime_contract():
    with (RELEASE_DIR / "manifest.toml").open("rb") as stream:
        manifest = tomllib.load(stream)
    catalog = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8"))
    tracker = pd.read_csv(RELEASE_DIR / "evidence" / "distance-resolution-v1.csv")

    assert manifest["release"] == "20260730.1"
    assert manifest["scope"]["tracker_rows"] == 81
    assert manifest["scope"]["resolved_override_rows"] == 48
    assert manifest["scope"]["excluded_provisional_rows"] == 33
    assert manifest["scope"]["selection"] == "status == resolved"
    assert manifest["scope"]["includes_sun"] is False
    assert manifest["scope"]["changes_pairing_policy"] is False

    assert catalog["dataset"]["dataset_id"] == "fis.distance-resolution-v1.resolved"
    assert catalog["dataset"]["resolved_row_count"] == 48
    assert catalog["dataset"]["excluded_provisional_row_count"] == 33
    stars = catalog["stars"]
    assert len(stars) == 48
    assert len({star["override_id"] for star in stars}) == 48
    assert len({(star["source"], str(star["source_id"])) for star in stars}) == 48
    assert {star["action"] for star in stars} == {"replace"}
    assert {star["override_policy_version"] for star in stars} == {
        "distance_resolution_v1"
    }
    assert not any(
        star["source"] == "manual" or str(star["source_id"]).lower() == "sun"
        for star in stars
    )

    assert len(tracker) == 81
    assert tracker["status"].value_counts().to_dict() == {
        "resolved": 48,
        "provisional": 33,
    }
    tracker_resolved = {
        (str(row.official_source), str(row.official_source_id))
        for row in tracker.loc[tracker["status"] == "resolved"].itertuples()
    }
    published = {(star["source"], str(star["source_id"])) for star in stars}
    assert published == tracker_resolved

    runtime = build_overrides_dataframe(source_paths=(CATALOG_PATH,))
    assert len(runtime) == 48
    assert set(runtime["action"]) == {"replace"}
    assert set(runtime["override_policy_version"]) == {"distance_resolution_v1"}


def test_distance_override_publication_evidence_and_build_report():
    catalog = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8"))
    build_report = json.loads(
        (RELEASE_DIR / "evidence" / "build_report.json").read_text(encoding="utf-8")
    )
    provenance = json.loads(
        (RELEASE_DIR / "evidence" / "input_provenance.json").read_text(
            encoding="utf-8"
        )
    )

    input_paths = {
        "distance_resolution_tracker": RELEASE_DIR
        / "evidence"
        / "distance-resolution-v1.csv",
        "candidate_review": RELEASE_DIR
        / "evidence"
        / "external-distance-required.parquet",
        "pipeline_candidates": RELEASE_DIR
        / "evidence"
        / "current-pipeline-candidates.parquet",
        "gaia_staged": RELEASE_DIR / "evidence" / "gaia-staged.parquet",
        "hip_staged": RELEASE_DIR / "evidence" / "hip-staged.parquet",
    }
    embedded_inputs = catalog["dataset"]["inputs"]
    for name, path in input_paths.items():
        digest = _sha256(path)
        assert embedded_inputs[name]["sha256"] == digest
        assert build_report["input_sha256"][name] == digest
        assert provenance["published_inputs"][name]["sha256"] == digest

    assert build_report["deterministic_rebuild_match"] is True
    assert build_report["yaml_rows"] == 48
    assert build_report["provisional_tracker_rows"] == 33
    assert build_report["output_sha256"] == _sha256(CATALOG_PATH)
    assert provenance["source_code"]["catalog_sha256"] == _sha256(CATALOG_PATH)
    assert (
        provenance["source_code"]["commit"]
        == "ffd569dd1e733c5bd39bb2dd6050763d98e06a43"
    )
    assert provenance["validation_environment"]["local_checkout_imported"] is False


def test_distance_override_publication_checksums_cover_every_release_file():
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
        assert _sha256(RELEASE_DIR / relative_path) == expected_digest
