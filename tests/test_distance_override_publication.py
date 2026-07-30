from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path

import pandas as pd
import yaml

from foundinspace.catalogs.audit.publication import regenerate_checksums
from foundinspace.pipeline.overrides.pipeline import build_overrides_dataframe

RELEASE_DIR = Path(__file__).parents[1] / "publications" / "20260730.2"
ALPHA_PATH = RELEASE_DIR / "catalog" / "alpha_cen.yaml"
DISTANCE_PATH = RELEASE_DIR / "catalog" / "distance_resolution_v1_resolved.yaml"
CATALOG_PATHS = (ALPHA_PATH, DISTANCE_PATH)
EXPECTED_LEGACY_IDS = {
    "manual.alpha_cen_a.replace.v1",
    "manual.alpha_cen_b.replace.v1",
    "manual.proxima_cen.replace.v1",
}
RETIRED_BINARY_IDS = {
    "manual.procyon_b.replace.v1",
    "manual.sirius_b.replace.v1",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stars(path: Path) -> list[dict]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))["stars"]


def test_override_publication_scope_selection_and_runtime_contract():
    with (RELEASE_DIR / "manifest.toml").open("rb") as stream:
        manifest = tomllib.load(stream)
    alpha_stars = _stars(ALPHA_PATH)
    distance_stars = _stars(DISTANCE_PATH)
    all_stars = [*alpha_stars, *distance_stars]
    tracker = pd.read_csv(RELEASE_DIR / "evidence" / "distance-resolution-v1.csv")

    assert manifest["release"] == "20260730.2"
    assert manifest["series_id"] == "fis.overrides"
    assert manifest["publication_model"] == "evolving-versioned-series"
    assert manifest["release_contents_model"] == "cumulative"
    assert manifest["lifecycle"] == {
        "release_snapshot": "immutable",
        "zenodo_record_model": "single-version-chain",
        "content_change_process": "zenodo-new-version",
        "metadata_only_change_process": "edit-published-record-metadata",
        "version_doi_policy": "new-for-each-published-version",
        "concept_doi_policy": "stable-across-version-chain",
        "citation_policy": "version-doi-for-reproducibility",
        "initial_zenodo_deposit": True,
        "prior_zenodo_version_exists": False,
        "version_doi_status": "assigned-on-publication",
        "concept_doi_status": "assigned-on-first-publication",
    }
    assert manifest["scope"]["total_override_rows"] == 51
    assert manifest["scope"]["retained_legacy_rows"] == 3
    assert manifest["scope"]["reviewed_addition_rows"] == 48
    assert manifest["scope"]["tracker_rows"] == 81
    assert manifest["scope"]["excluded_provisional_rows"] == 33
    assert manifest["scope"]["excluded_retired_binary_rows"] == 2
    assert manifest["scope"]["excluded_sun_rows"] == 1
    assert manifest["scope"]["replace_actions"] == 51
    assert manifest["scope"]["quality_checked_rows"] == 51
    assert manifest["scope"]["includes_sun"] is False
    assert manifest["scope"]["changes_pairing_policy"] is False

    assert len(alpha_stars) == 3
    assert len(distance_stars) == 48
    assert len(all_stars) == 51
    assert len({star["override_id"] for star in all_stars}) == 51
    assert len(
        {(star["source"], str(star["source_id"])) for star in all_stars}
    ) == 51
    assert {star["action"] for star in all_stars} == {"replace"}
    assert not RETIRED_BINARY_IDS.intersection(
        star["override_id"] for star in all_stars
    )
    assert not any(
        star["source"] == "manual" or str(star["source_id"]).lower() == "sun"
        for star in all_stars
    )

    assert tracker["status"].value_counts().to_dict() == {
        "resolved": 48,
        "provisional": 33,
    }
    tracker_resolved = {
        (str(row.official_source), str(row.official_source_id))
        for row in tracker.loc[tracker["status"] == "resolved"].itertuples()
    }
    published_additions = {
        (star["source"], str(star["source_id"])) for star in distance_stars
    }
    assert published_additions == tracker_resolved

    runtime = build_overrides_dataframe(source_paths=CATALOG_PATHS)
    assert len(runtime) == 51
    assert set(runtime["action"]) == {"replace"}
    assert set(runtime["override_id"]) == {
        star["override_id"] for star in all_stars
    }


def test_legacy_alpha_values_history_pairing_and_references():
    alpha_stars = _stars(ALPHA_PATH)
    historical_stars = _stars(
        RELEASE_DIR / "evidence" / "alpha_cen_legacy_source.yaml"
    )
    historical_by_id = {
        star["override_id"]: star for star in historical_stars
    }
    assert set(historical_by_id) == EXPECTED_LEGACY_IDS
    assert (
        _sha256(RELEASE_DIR / "evidence" / "alpha_cen_legacy_source.yaml")
        == "8626f9a9f4a4550921108280a1092e0190503f4912a77549e1e50f228bbafb9f"
    )

    executable_fields = {
        "override_id",
        "action",
        "source",
        "source_id",
        "override_reason",
        "override_policy_version",
        "ra_deg",
        "dec_deg",
        "r_pc",
        "mag_abs",
        "teff",
        "photometry_band",
        "photometry_quality",
        "photometry_value",
    }
    for star in alpha_stars:
        historical = historical_by_id[star["override_id"]]
        assert {
            field: star[field] for field in executable_fields
        } == {
            field: historical[field] for field in executable_fields
        }
        provenance = star["provenance"]
        assert provenance["review_status"] == "retained_after_current_state_review"
        assert provenance["legacy_source"]["executable_values_changed"] is False
        assert provenance["position"]["reference"]
        assert provenance["selected_distance"]["reference"]
        assert provenance["selected_distance"]["symmetric_error_pc"] > 0
        assert provenance["preserved_payload"]["photometry_reference"]
        assert provenance["preserved_payload"]["temperature_reference"]

    pairing = json.loads(
        (RELEASE_DIR / "evidence" / "alpha_cen_pairing_review.json").read_text(
            encoding="utf-8"
        )
    )
    assert pairing["source"]["raw_rows"] == 99_525
    assert (
        pairing["source"]["raw_sha256"]
        == "2590acdbfd6016527dcb028a76a4ee9ea7775e6c3161924f2a9844b1ce221159"
    )
    by_id = {row["override_id"]: row for row in pairing["results"]}
    assert by_id["manual.alpha_cen_a.replace.v1"]["mapping_found"] is False
    assert by_id["manual.alpha_cen_b.replace.v1"]["gaia_source_id"] == (
        "5877748442128924544"
    )
    assert by_id["manual.proxima_cen.replace.v1"]["gaia_source_id"] == (
        "5853498713190525696"
    )
    assert pairing["validation"]["supplemental_pairing_map_used"] is False
    assert pairing["validation"]["pairing_policy_changed"] is False


def test_override_publication_evidence_build_and_per_row_quality():
    distance_catalog = yaml.safe_load(
        DISTANCE_PATH.read_text(encoding="utf-8")
    )
    build_report = json.loads(
        (RELEASE_DIR / "evidence" / "build_report.json").read_text(
            encoding="utf-8"
        )
    )
    publication_report = json.loads(
        (RELEASE_DIR / "evidence" / "publication_build_report.json").read_text(
            encoding="utf-8"
        )
    )
    quality_report = json.loads(
        (RELEASE_DIR / "evidence" / "override_quality_report.json").read_text(
            encoding="utf-8"
        )
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
    embedded_inputs = distance_catalog["dataset"]["inputs"]
    for name, path in input_paths.items():
        digest = _sha256(path)
        assert embedded_inputs[name]["sha256"] == digest
        assert build_report["input_sha256"][name] == digest
        assert provenance["published_inputs"][name]["sha256"] == digest

    assert build_report["deterministic_rebuild_match"] is True
    assert build_report["yaml_rows"] == 48
    assert build_report["provisional_tracker_rows"] == 33
    assert build_report["output_sha256"] == _sha256(DISTANCE_PATH)

    counts = publication_report["counts"]
    assert counts["total_override_rows"] == 51
    assert counts["retained_legacy_rows"] == 3
    assert counts["reviewed_addition_rows"] == 48
    assert counts["excluded_provisional_rows"] == 33
    assert counts["excluded_retired_binary_rows"] == 2
    assert counts["excluded_sun_rows"] == 1
    assert counts["actions"] == {"replace": 51}
    assert all(publication_report["validation"].values())
    lifecycle = publication_report["publication_lifecycle"]
    assert lifecycle["release_snapshot"] == "immutable"
    assert lifecycle["zenodo_record_model"] == "single-version-chain"
    assert lifecycle["content_change_process"] == "zenodo-new-version"
    assert lifecycle["version_doi_policy"] == (
        "new-for-each-published-version"
    )
    assert lifecycle["concept_doi_policy"] == "stable-across-version-chain"

    assert quality_report["summary"]["rows_checked"] == 51
    assert quality_report["summary"]["rows_passed"] == 51
    assert quality_report["summary"]["rows_failed"] == 0
    assert quality_report["summary"]["checks_per_row"] == 19
    assert len(quality_report["rows"]) == 51
    assert all(row["passed"] for row in quality_report["rows"])
    assert all(
        all(row["checks"].values()) for row in quality_report["rows"]
    )
    assert all(row["references"]["distance"] for row in quality_report["rows"])
    assert all(row["references"]["position"] for row in quality_report["rows"])
    assert all(row["references"]["photometry"] for row in quality_report["rows"])
    assert all(row["references"]["temperature"] for row in quality_report["rows"])

    assert (
        provenance["legacy_base"]["source_sha256"]
        == "8626f9a9f4a4550921108280a1092e0190503f4912a77549e1e50f228bbafb9f"
    )
    assert (
        provenance["reviewed_addition"]["commit"]
        == "ffd569dd1e733c5bd39bb2dd6050763d98e06a43"
    )
    assert provenance["validation_environment"]["local_checkout_imported"] is False
    assert provenance["validation_environment"]["direct_url_verified"] is True
    assert (
        provenance["validation_environment"]["requested_revision"]
        == "ffd569dd1e733c5bd39bb2dd6050763d98e06a43"
    )
    assert (
        provenance["validation_environment"]["resolved_commit"]
        == "ffd569dd1e733c5bd39bb2dd6050763d98e06a43"
    )
    assert provenance["current_pairing_review"]["policy_changed"] is False
    assert (
        provenance["current_pairing_review"]["supplemental_pairing_map_used"]
        is False
    )
    assert provenance["publication_lifecycle"] == lifecycle


def test_override_publication_documents_version_lifecycle_and_zenodo_process():
    required_phrases = {
        "README.md": (
            "evolving, versioned catalog",
            "immutable snapshot",
            "New version",
            "Version DOI",
            "Concept DOI",
        ),
        "NOTICE.md": (
            "evolving catalog",
            "immutable snapshot",
            "New version",
            "Version DOI",
            "Concept DOI",
        ),
        "REFERENCES.md": (
            "evolving `fis.overrides` catalog",
            "Version DOI",
            "Concept DOI",
            "New version",
        ),
        "run_log.md": (
            "one evolving Zenodo version chain",
            "immutable",
            "New version",
            "Version DOI",
            "Concept DOI",
        ),
        "LICENSE.txt": (
            "Version DOI",
            "Concept DOI",
            "evolving `fis.overrides` series",
        ),
        "zenodo/draft-metadata.md": (
            "initial Zenodo deposit",
            "immutable",
            "New version",
            "Version DOI",
            "Concept DOI",
            "No earlier `fis.overrides` record exists",
        ),
    }
    for relative_path, phrases in required_phrases.items():
        text = (RELEASE_DIR / relative_path).read_text(encoding="utf-8")
        for phrase in phrases:
            assert phrase in text, f"{relative_path} is missing {phrase!r}"

    release_text = "\n".join(
        (RELEASE_DIR / relative_path).read_text(encoding="utf-8")
        for relative_path in required_phrases
    )
    assert "one-off controlled rendering dataset" not in release_text


def test_override_publication_checksums_cover_every_release_file():
    checksum_path = RELEASE_DIR / "checksums.sha256"
    recorded = {}
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        digest, relative_path = line.split(maxsplit=1)
        recorded[relative_path] = digest

    expected_files = {
        path.relative_to(RELEASE_DIR).as_posix()
        for path in RELEASE_DIR.rglob("*")
        if (
            path.is_file()
            and path != checksum_path
            and path.relative_to(RELEASE_DIR).as_posix()
            != "zenodo/published-record.toml"
        )
    }
    assert set(recorded) == expected_files

    for relative_path, expected_digest in recorded.items():
        assert _sha256(RELEASE_DIR / relative_path) == expected_digest


def test_checksums_exclude_post_publication_zenodo_tracking(tmp_path):
    release_dir = tmp_path / "20260730.2"
    zenodo_dir = release_dir / "zenodo"
    zenodo_dir.mkdir(parents=True)
    (release_dir / "payload.txt").write_text("payload\n", encoding="utf-8")
    (zenodo_dir / "published-record.toml").write_text(
        'record_doi = "assigned-after-publication"\n',
        encoding="utf-8",
    )
    checksum_path = release_dir / "checksums.sha256"

    regenerate_checksums(release_dir, checksums_path=checksum_path)

    checksum_text = checksum_path.read_text(encoding="utf-8")
    assert "payload.txt" in checksum_text
    assert "published-record.toml" not in checksum_text
