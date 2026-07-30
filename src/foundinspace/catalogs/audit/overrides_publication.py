"""Assembly and validation for the versioned stellar override publication."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import tomllib
from collections import Counter
from dataclasses import dataclass
from importlib.metadata import distribution
from pathlib import Path
from typing import Any

import foundinspace.pipeline as pipeline_package
import yaml
from foundinspace.pipeline.overrides.pipeline import build_overrides_dataframe

from foundinspace.catalogs.audit.publication import regenerate_checksums

RELEASE = "20260730.2"
SERIES_ID = "fis.overrides"
LEGACY_PIPELINE_COMMIT = "74635226a917ec4c2c1c08c46b38cd05d227732a"
DISTANCE_PIPELINE_COMMIT = "ffd569dd1e733c5bd39bb2dd6050763d98e06a43"
LIFECYCLE_POLICY = {
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

ALPHA_COMPONENT = {
    "path": "catalog/alpha_cen.yaml",
    "source_path": "src/foundinspace/pipeline/overrides/data/alpha_cen.yaml",
    "historical_evidence_path": "evidence/alpha_cen_legacy_source.yaml",
    "historical_sha256": (
        "8626f9a9f4a4550921108280a1092e0190503f4912a77549e1e50f228bbafb9f"
    ),
    "rows": 3,
}
PAIRING_REVIEW_PATH = "evidence/alpha_cen_pairing_review.json"
DISTANCE_COMPONENT = {
    "path": "catalog/distance_resolution_v1_resolved.yaml",
    "source_path": (
        "tools/curation/distance_resolution_v1/"
        "distance-resolution-v1-resolved.yaml"
    ),
    "sha256": "a53122ace82402969eace466adc9178ab184e7c4758ddd3e90a69372985a43c4",
    "rows": 48,
}
DISTANCE_EVIDENCE_INPUTS = {
    "distance_resolution_tracker": "evidence/distance-resolution-v1.csv",
    "candidate_review": "evidence/external-distance-required.parquet",
    "pipeline_candidates": "evidence/current-pipeline-candidates.parquet",
    "gaia_staged": "evidence/gaia-staged.parquet",
    "hip_staged": "evidence/hip-staged.parquet",
}
PUBLICATION_EVIDENCE_INPUTS = {
    **DISTANCE_EVIDENCE_INPUTS,
    "alpha_cen_legacy_source": ALPHA_COMPONENT["historical_evidence_path"],
    "alpha_cen_pairing_review": PAIRING_REVIEW_PATH,
}
EXPECTED_LEGACY_IDS = {
    "manual.alpha_cen_a.replace.v1",
    "manual.alpha_cen_b.replace.v1",
    "manual.proxima_cen.replace.v1",
}
RETIRED_BINARY_IDS = {
    "manual.procyon_b.replace.v1",
    "manual.sirius_b.replace.v1",
}
EXECUTABLE_FIELDS = (
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
)


@dataclass(frozen=True)
class OverridesPublicationResult:
    release: str
    total_rows: int
    legacy_rows: int
    reviewed_rows: int
    report_path: str
    quality_report_path: str
    provenance_path: str
    checksums_path: str


def assemble_overrides_publication(
    *,
    release_dir: Path,
) -> OverridesPublicationResult:
    """Validate the cumulative override set and regenerate derived records."""

    release_dir = Path(release_dir).resolve()
    if release_dir.name != RELEASE:
        raise ValueError(
            f"Expected release directory named {RELEASE}, got {release_dir.name}"
        )

    manifest = _read_manifest(release_dir / "manifest.toml")
    alpha_path = release_dir / ALPHA_COMPONENT["path"]
    distance_path = release_dir / DISTANCE_COMPONENT["path"]
    historical_alpha_path = (
        release_dir / ALPHA_COMPONENT["historical_evidence_path"]
    )
    pairing_review_path = release_dir / PAIRING_REVIEW_PATH
    required_paths = (
        alpha_path,
        distance_path,
        historical_alpha_path,
        pairing_review_path,
        *(
            release_dir / relative_path
            for relative_path in DISTANCE_EVIDENCE_INPUTS.values()
        ),
    )
    for path in required_paths:
        if not path.is_file():
            raise FileNotFoundError(path)

    alpha_stars = _read_stars(alpha_path)
    distance_stars = _read_stars(distance_path)
    historical_alpha_stars = _read_stars(historical_alpha_path)

    _require_equal("Alpha row count", len(alpha_stars), 3)
    _require_equal("reviewed row count", len(distance_stars), 48)
    _require_equal(
        "historical Alpha SHA-256",
        _sha256(historical_alpha_path),
        ALPHA_COMPONENT["historical_sha256"],
    )
    _require_equal(
        "distance component SHA-256",
        _sha256(distance_path),
        DISTANCE_COMPONENT["sha256"],
    )
    _validate_legacy_projection(alpha_stars, historical_alpha_stars)
    _validate_pairing_review(alpha_stars, pairing_review_path)

    all_stars = [*alpha_stars, *distance_stars]
    override_ids = [str(star["override_id"]) for star in all_stars]
    target_keys = [
        (str(star["source"]), str(star["source_id"])) for star in all_stars
    ]
    _require_unique("override_id", override_ids)
    _require_unique("override target", target_keys)
    _require_equal(
        "legacy override IDs",
        {str(star["override_id"]) for star in alpha_stars},
        EXPECTED_LEGACY_IDS,
    )
    if RETIRED_BINARY_IDS.intersection(override_ids):
        raise ValueError("Retired Sirius B or Procyon B override is executable")
    if any(
        source.lower() == "manual" and source_id.lower() == "sun"
        for source, source_id in target_keys
    ):
        raise ValueError("The cumulative override publication must not contain the Sun")

    tracker_path = (
        release_dir / DISTANCE_EVIDENCE_INPUTS["distance_resolution_tracker"]
    )
    with tracker_path.open(newline="", encoding="utf-8") as stream:
        tracker_rows = list(csv.DictReader(stream))
    tracker_statuses = Counter(row["status"] for row in tracker_rows)
    _require_equal("tracker rows", len(tracker_rows), 81)
    _require_equal("resolved tracker rows", tracker_statuses["resolved"], 48)
    _require_equal("provisional tracker rows", tracker_statuses["provisional"], 33)
    resolved_tracker_targets = {
        (str(row["official_source"]), str(row["official_source_id"]))
        for row in tracker_rows
        if row["status"] == "resolved"
    }
    distance_targets = {
        (str(star["source"]), str(star["source_id"]))
        for star in distance_stars
    }
    _require_equal(
        "resolved tracker targets",
        distance_targets,
        resolved_tracker_targets,
    )

    component_paths = (alpha_path, distance_path)
    runtime = build_overrides_dataframe(source_paths=component_paths)
    _require_equal("runtime override rows", len(runtime), 51)

    quality_report = _build_quality_report(
        alpha_stars=alpha_stars,
        distance_stars=distance_stars,
        runtime=runtime,
        catalog_hashes={
            ALPHA_COMPONENT["path"]: _sha256(alpha_path),
            DISTANCE_COMPONENT["path"]: _sha256(distance_path),
        },
    )
    _require_equal("quality rows", quality_report["summary"]["rows_checked"], 51)
    _require_equal("quality failures", quality_report["summary"]["rows_failed"], 0)
    validation_environment = _validate_pipeline_dependency(
        repo_root=release_dir.parents[1]
    )

    evidence_hashes = {
        name: {
            "path": relative_path,
            "sha256": _sha256(release_dir / relative_path),
        }
        for name, relative_path in PUBLICATION_EVIDENCE_INPUTS.items()
    }
    action_counts = Counter(str(star["action"]) for star in all_stars)
    counts = {
        "total_override_rows": len(all_stars),
        "retained_legacy_rows": len(alpha_stars),
        "reviewed_addition_rows": len(distance_stars),
        "excluded_provisional_rows": tracker_statuses["provisional"],
        "excluded_retired_binary_rows": len(RETIRED_BINARY_IDS),
        "excluded_sun_rows": 1,
        "runtime_override_rows": len(runtime),
        "quality_checked_rows": quality_report["summary"]["rows_checked"],
        "quality_passed_rows": quality_report["summary"]["rows_passed"],
        "actions": dict(sorted(action_counts.items())),
    }
    _validate_manifest(manifest, counts)

    report = {
        "format_version": 1,
        "release": RELEASE,
        "series_id": SERIES_ID,
        "supersedes_unpublished_release_candidate": "20260730.1",
        "publication_lifecycle": LIFECYCLE_POLICY,
        "catalog_files": {
            ALPHA_COMPONENT["path"]: {
                "rows": len(alpha_stars),
                "sha256": _sha256(alpha_path),
                "role": "retained legacy base with refreshed provenance",
            },
            DISTANCE_COMPONENT["path"]: {
                "rows": len(distance_stars),
                "sha256": _sha256(distance_path),
                "role": "reviewed additions",
            },
        },
        "counts": counts,
        "validation": {
            "legacy_source_evidence_matches_public_history": True,
            "legacy_executable_projection_unchanged": True,
            "legacy_provenance_refreshed": True,
            "current_best_neighbour_state_reviewed": True,
            "distance_component_matches_public_source": True,
            "resolved_tracker_targets_match_distance_component": True,
            "override_ids_unique": True,
            "target_keys_unique": True,
            "retired_binary_overrides_absent": True,
            "sun_absent": True,
            "runtime_loader_passed": True,
            "pinned_public_pipeline_dependency_verified": True,
            "all_rows_pass_quality_checks": True,
            "immutable_release_snapshot_declared": True,
            "single_zenodo_version_chain_declared": True,
            "version_and_concept_doi_roles_declared": True,
        },
        "legacy_override_ids": sorted(EXPECTED_LEGACY_IDS),
        "retired_binary_override_ids": sorted(RETIRED_BINARY_IDS),
        "evidence_sha256": evidence_hashes,
    }

    provenance = {
        "format_version": 1,
        "release": RELEASE,
        "series_id": SERIES_ID,
        "publication_lifecycle": LIFECYCLE_POLICY,
        "legacy_base": {
            "repository": "https://github.com/Found-in-Space/pipeline",
            "commit": LEGACY_PIPELINE_COMMIT,
            "commit_time": "2026-07-29T09:41:55+01:00",
            "source_path": ALPHA_COMPONENT["source_path"],
            "source_sha256": ALPHA_COMPONENT["historical_sha256"],
            "published_historical_evidence": (
                ALPHA_COMPONENT["historical_evidence_path"]
            ),
            "publication_catalog_path": ALPHA_COMPONENT["path"],
            "publication_catalog_sha256": _sha256(alpha_path),
            "retained_override_rows": len(alpha_stars),
            "transformation": (
                "Executable fields and override IDs are unchanged. Stale pairing "
                "prose was replaced and structured row-level provenance was added."
            ),
        },
        "current_pairing_review": {
            "catalog": "gaiadr3.hipparcos2_best_neighbour",
            "evidence_path": PAIRING_REVIEW_PATH,
            "evidence_sha256": _sha256(pairing_review_path),
            "policy_changed": False,
            "supplemental_pairing_map_used": False,
        },
        "reviewed_addition": {
            "repository": "https://github.com/Found-in-Space/pipeline",
            "commit": DISTANCE_PIPELINE_COMMIT,
            "commit_time": "2026-07-30T12:02:20+02:00",
            "catalog_source_path": DISTANCE_COMPONENT["source_path"],
            "catalog_path": DISTANCE_COMPONENT["path"],
            "catalog_sha256": DISTANCE_COMPONENT["sha256"],
            "rows": len(distance_stars),
            "build_entrypoint": (
                "tools.curation.distance_resolution_v1.build_overrides_cli"
            ),
        },
        "explicit_exclusions": {
            "retired_binary_component": {
                "historical_path": (
                    "src/foundinspace/pipeline/overrides/data/binaries.yaml"
                ),
                "historical_sha256": (
                    "2f752a0b38d3e5ad123199a97557b68fc0120521ba006e5c352bc8e0b54ec7d7"
                ),
                "override_ids": sorted(RETIRED_BINARY_IDS),
                "retired_on_main_commit": (
                    "7fcb20d2506d50540445a6c990e9080e6faf6de6"
                ),
                "reason": (
                    "Sirius B and Procyon B were deliberately retired before "
                    "the original publication was assembled."
                ),
            },
            "sun_component": {
                "historical_path": (
                    "src/foundinspace/pipeline/overrides/data/sun.yaml"
                ),
                "historical_sha256": (
                    "6010b9016f35847f276c36aca313cee16c87f9e6adc975018bc5f26c5be5e6dd"
                ),
                "reason": (
                    "The Sun is a separate opt-in reference publication, not "
                    "an executable stellar override in this series."
                ),
            },
        },
        "validation_environment": validation_environment,
        "published_inputs": evidence_hashes,
        "observed_counts": counts,
        "policy_boundary": (
            "The three original Alpha Centauri overrides retain their executable "
            "identities and values. Exactly 48 tracker rows reviewed as resolved "
            "are added. Thirty-three provisional rows, two retired binary "
            "overrides, and the Sun remain non-executable."
        ),
    }

    evidence_dir = release_dir / "evidence"
    report_path = evidence_dir / "publication_build_report.json"
    quality_report_path = evidence_dir / "override_quality_report.json"
    provenance_path = evidence_dir / "input_provenance.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    quality_report_path.write_text(
        json.dumps(quality_report, indent=2) + "\n",
        encoding="utf-8",
    )
    provenance_path.write_text(
        json.dumps(provenance, indent=2) + "\n",
        encoding="utf-8",
    )

    checksums_path = release_dir / "checksums.sha256"
    regenerate_checksums(release_dir, checksums_path=checksums_path)
    return OverridesPublicationResult(
        release=RELEASE,
        total_rows=len(all_stars),
        legacy_rows=len(alpha_stars),
        reviewed_rows=len(distance_stars),
        report_path=str(report_path),
        quality_report_path=str(quality_report_path),
        provenance_path=str(provenance_path),
        checksums_path=str(checksums_path),
    )


def _read_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open("rb") as stream:
        return tomllib.load(stream)


def _read_stars(path: Path) -> list[dict[str, Any]]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or not isinstance(document.get("stars"), list):
        raise ValueError(f"{path} has no stars list")
    if not all(isinstance(star, dict) for star in document["stars"]):
        raise ValueError(f"{path} contains a non-mapping star entry")
    return document["stars"]


def _validate_legacy_projection(
    current: list[dict[str, Any]],
    historical: list[dict[str, Any]],
) -> None:
    historical_by_id = {
        str(star["override_id"]): star for star in historical
    }
    _require_equal("historical Alpha rows", len(historical_by_id), 3)
    for star in current:
        override_id = str(star["override_id"])
        if override_id not in historical_by_id:
            raise ValueError(f"Unknown legacy override ID: {override_id}")
        expected = historical_by_id[override_id]
        for field in EXECUTABLE_FIELDS:
            _require_equal(
                f"{override_id} legacy field {field}",
                star.get(field),
                expected.get(field),
            )
        provenance = star.get("provenance")
        if not isinstance(provenance, dict):
            raise ValueError(f"{override_id} lacks structured provenance")
        legacy_source = provenance.get("legacy_source")
        if not isinstance(legacy_source, dict):
            raise ValueError(f"{override_id} lacks legacy source provenance")
        _require_equal(
            f"{override_id} executable values changed",
            legacy_source.get("executable_values_changed"),
            False,
        )
        _require_equal(
            f"{override_id} legacy source SHA-256",
            legacy_source.get("source_sha256"),
            ALPHA_COMPONENT["historical_sha256"],
        )


def _validate_pairing_review(
    alpha_stars: list[dict[str, Any]],
    pairing_review_path: Path,
) -> None:
    review = json.loads(pairing_review_path.read_text(encoding="utf-8"))
    _require_equal(
        "pairing review catalog",
        review["source"]["catalog"],
        "gaiadr3.hipparcos2_best_neighbour",
    )
    _require_equal("pairing review raw rows", review["source"]["raw_rows"], 99_525)
    _require_equal(
        "pairing review raw SHA-256",
        review["source"]["raw_sha256"],
        "2590acdbfd6016527dcb028a76a4ee9ea7775e6c3161924f2a9844b1ce221159",
    )
    expected = {
        "manual.alpha_cen_a.replace.v1": (71683, False, None),
        "manual.alpha_cen_b.replace.v1": (
            71681,
            True,
            "5877748442128924544",
        ),
        "manual.proxima_cen.replace.v1": (
            70890,
            True,
            "5853498713190525696",
        ),
    }
    observed = {
        str(row["override_id"]): (
            int(row["hip_source_id"]),
            bool(row["mapping_found"]),
            row["gaia_source_id"],
        )
        for row in review["results"]
    }
    _require_equal("pairing review results", observed, expected)
    _require_equal(
        "supplemental pairing used",
        review["validation"]["supplemental_pairing_map_used"],
        False,
    )
    _require_equal(
        "pairing policy changed",
        review["validation"]["pairing_policy_changed"],
        False,
    )
    for star in alpha_stars:
        override_id = str(star["override_id"])
        pairing = star["provenance"]["pairing"]
        _, mapping_found, gaia_source_id = expected[override_id]
        _require_equal(
            f"{override_id} mapping status",
            pairing["mapping_found"],
            mapping_found,
        )
        _require_equal(
            f"{override_id} pairing Gaia source",
            pairing.get("gaia_source_id"),
            gaia_source_id,
        )


def _build_quality_report(
    *,
    alpha_stars: list[dict[str, Any]],
    distance_stars: list[dict[str, Any]],
    runtime: Any,
    catalog_hashes: dict[str, str],
) -> dict[str, Any]:
    runtime_by_id = {
        str(row.override_id): row for row in runtime.itertuples(index=False)
    }
    rows = []
    for component, stars in (
        ("retained_legacy", alpha_stars),
        ("reviewed_addition", distance_stars),
    ):
        for star in stars:
            rows.append(
                _quality_record(
                    star=star,
                    component=component,
                    runtime_row=runtime_by_id.get(str(star["override_id"])),
                )
            )
    failed = [row for row in rows if not row["passed"]]
    check_names = sorted(
        {check_name for row in rows for check_name in row["checks"]}
    )
    return {
        "format_version": 1,
        "release": RELEASE,
        "series_id": SERIES_ID,
        "catalog_sha256": catalog_hashes,
        "summary": {
            "rows_checked": len(rows),
            "rows_passed": len(rows) - len(failed),
            "rows_failed": len(failed),
            "checks_per_row": len(check_names),
            "check_names": check_names,
        },
        "rows": rows,
    }


def _quality_record(
    *,
    star: dict[str, Any],
    component: str,
    runtime_row: Any,
) -> dict[str, Any]:
    override_id = str(star.get("override_id", ""))
    provenance = star.get("provenance")
    provenance = provenance if isinstance(provenance, dict) else {}
    distance = provenance.get("selected_distance")
    distance = distance if isinstance(distance, dict) else {}
    payload = provenance.get("preserved_payload")
    payload = payload if isinstance(payload, dict) else {}
    position = provenance.get("position")
    position = position if isinstance(position, dict) else {}

    numeric_fields = ("ra_deg", "dec_deg", "r_pc", "mag_abs", "teff")
    numeric_values = [_as_finite_float(star.get(field)) for field in numeric_fields]
    numeric_finite = all(value is not None for value in numeric_values)
    ra, dec, radius, mag_abs, teff = numeric_values
    apparent_mag = _as_finite_float(payload.get("apparent_magnitude"))
    selected_distance = _as_finite_float(distance.get("value_pc"))
    distance_error = _as_finite_float(distance.get("symmetric_error_pc"))

    magnitude_rebase_matches = False
    if (
        apparent_mag is not None
        and radius is not None
        and radius > 0
        and mag_abs is not None
    ):
        expected_mag_abs = apparent_mag - 5.0 * math.log10(radius) + 5.0
        magnitude_rebase_matches = math.isclose(
            mag_abs,
            expected_mag_abs,
            rel_tol=0.0,
            abs_tol=5e-4,
        )

    runtime_values_match = False
    runtime_cartesian_norm_matches_distance = False
    if runtime_row is not None and numeric_finite:
        runtime_values_match = all(
            math.isclose(
                float(getattr(runtime_row, field)),
                float(star[field]),
                rel_tol=0.0,
                abs_tol=1e-10,
            )
            for field in numeric_fields
        )
        runtime_norm = math.sqrt(
            float(runtime_row.x_icrs_pc) ** 2
            + float(runtime_row.y_icrs_pc) ** 2
            + float(runtime_row.z_icrs_pc) ** 2
        )
        runtime_cartesian_norm_matches_distance = math.isclose(
            runtime_norm,
            float(star["r_pc"]),
            rel_tol=1e-12,
            abs_tol=1e-12,
        )

    if component == "retained_legacy":
        astrometry_traceable = bool(position.get("reference"))
        photometry_traceable = bool(
            payload.get("photometry_reference")
            and payload.get("photometry_quality")
        )
        temperature_traceable = bool(payload.get("temperature_reference"))
        expected_review_status = "retained_after_current_state_review"
    else:
        astrometry_traceable = bool(payload.get("astrometry_donor"))
        photometry_traceable = bool(payload.get("photometry_donor"))
        temperature_traceable = bool(payload.get("temperature_donor"))
        expected_review_status = "resolved"

    source = str(star.get("source", ""))
    source_id = str(star.get("source_id", ""))
    checks = {
        "required_identity_fields_present": all(
            star.get(field) not in (None, "")
            for field in (
                "override_id",
                "action",
                "source",
                "source_id",
                "override_reason",
                "override_policy_version",
            )
        ),
        "numeric_payload_finite": numeric_finite,
        "coordinates_in_range": (
            numeric_finite
            and ra is not None
            and dec is not None
            and 0.0 <= ra < 360.0
            and -90.0 <= dec <= 90.0
        ),
        "distance_and_temperature_positive": (
            numeric_finite
            and radius is not None
            and teff is not None
            and radius > 0.0
            and teff > 0.0
        ),
        "action_is_replace": star.get("action") == "replace",
        "review_status_matches_component": (
            provenance.get("review_status") == expected_review_status
        ),
        "distance_provenance_present": bool(distance),
        "distance_matches_provenance": (
            radius is not None
            and selected_distance is not None
            and math.isclose(
                radius,
                selected_distance,
                rel_tol=0.0,
                abs_tol=1e-10,
            )
        ),
        "distance_uncertainty_positive": (
            distance_error is not None and distance_error > 0.0
        ),
        "distance_reference_and_notes_present": bool(
            distance.get("reference") and distance.get("notes")
        ),
        "apparent_magnitude_provenance_present": apparent_mag is not None,
        "absolute_magnitude_rebase_matches": magnitude_rebase_matches,
        "astrometry_traceable": astrometry_traceable,
        "photometry_traceable": photometry_traceable,
        "temperature_traceable": temperature_traceable,
        "runtime_row_present": runtime_row is not None,
        "runtime_values_match": runtime_values_match,
        "runtime_cartesian_norm_matches_distance": (
            runtime_cartesian_norm_matches_distance
        ),
        "target_is_not_explicitly_excluded": (
            override_id not in RETIRED_BINARY_IDS
            and not (source.lower() == "manual" and source_id.lower() == "sun")
        ),
    }
    failed_checks = [name for name, passed in checks.items() if not passed]
    references = {
        "distance": distance.get("reference"),
        "position": (
            position.get("reference")
            if component == "retained_legacy"
            else payload.get("astrometry_donor")
        ),
        "photometry": (
            payload.get("photometry_reference")
            if component == "retained_legacy"
            else payload.get("photometry_donor")
        ),
        "temperature": (
            payload.get("temperature_reference")
            if component == "retained_legacy"
            else payload.get("temperature_donor")
        ),
    }
    return {
        "override_id": override_id,
        "component": component,
        "source": source,
        "source_id": source_id,
        "action": star.get("action"),
        "references": references,
        "checks": checks,
        "passed": not failed_checks,
        "failed_checks": failed_checks,
    }


def _validate_manifest(
    manifest: dict[str, Any],
    observed_counts: dict[str, Any],
) -> None:
    _require_equal("manifest release", manifest.get("release"), RELEASE)
    _require_equal("manifest series", manifest.get("series_id"), SERIES_ID)
    _require_equal(
        "manifest publication model",
        manifest.get("publication_model"),
        "evolving-versioned-series",
    )
    _require_equal(
        "manifest release contents model",
        manifest.get("release_contents_model"),
        "cumulative",
    )
    lifecycle = manifest.get("lifecycle", {})
    for field, expected in LIFECYCLE_POLICY.items():
        _require_equal(
            f"manifest lifecycle {field}",
            lifecycle.get(field),
            expected,
        )
    scope = manifest.get("scope", {})
    for field in (
        "total_override_rows",
        "retained_legacy_rows",
        "reviewed_addition_rows",
        "excluded_provisional_rows",
        "excluded_retired_binary_rows",
        "excluded_sun_rows",
        "quality_checked_rows",
    ):
        _require_equal(
            f"manifest {field}",
            scope.get(field),
            observed_counts[field],
        )
    _require_equal(
        "manifest replace actions",
        scope.get("replace_actions"),
        observed_counts["actions"].get("replace"),
    )
    _require_equal("manifest includes Sun", scope.get("includes_sun"), False)
    _require_equal(
        "manifest changes pairing policy",
        scope.get("changes_pairing_policy"),
        False,
    )


def _validate_pipeline_dependency(*, repo_root: Path) -> dict[str, Any]:
    package = distribution("found-in-space-pipeline")
    direct_url_text = package.read_text("direct_url.json")
    if direct_url_text is None:
        raise ValueError(
            "found-in-space-pipeline has no direct_url.json provenance"
        )
    direct_url = json.loads(direct_url_text)
    expected_url = "https://github.com/Found-in-Space/pipeline.git"
    vcs_info = direct_url.get("vcs_info", {})
    _require_equal("pipeline dependency URL", direct_url.get("url"), expected_url)
    _require_equal("pipeline dependency VCS", vcs_info.get("vcs"), "git")
    _require_equal(
        "pipeline dependency requested revision",
        vcs_info.get("requested_revision"),
        DISTANCE_PIPELINE_COMMIT,
    )
    _require_equal(
        "pipeline dependency resolved commit",
        vcs_info.get("commit_id"),
        DISTANCE_PIPELINE_COMMIT,
    )

    module_path = Path(pipeline_package.__file__).resolve()
    local_pipeline_checkout = (repo_root.parent / "pipeline").resolve()
    local_checkout_imported = module_path.is_relative_to(local_pipeline_checkout)
    _require_equal(
        "local pipeline checkout imported",
        local_checkout_imported,
        False,
    )

    for declaration in ("pyproject.toml", "uv.lock"):
        declaration_path = repo_root / declaration
        if not declaration_path.is_file():
            raise FileNotFoundError(declaration_path)
        if DISTANCE_PIPELINE_COMMIT not in declaration_path.read_text(
            encoding="utf-8"
        ):
            raise ValueError(
                f"{declaration} does not pin pipeline commit "
                f"{DISTANCE_PIPELINE_COMMIT}"
            )

    return {
        "dependency": "found-in-space-pipeline",
        "source": f"git+{expected_url}",
        "requested_revision": vcs_info["requested_revision"],
        "resolved_commit": vcs_info["commit_id"],
        "declared_in": ["pyproject.toml", "uv.lock"],
        "imported_module_location": "installed environment site-packages",
        "local_checkout_imported": local_checkout_imported,
        "direct_url_verified": True,
    }


def _as_finite_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_equal(label: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        raise ValueError(f"{label}: expected {expected!r}, got {actual!r}")


def _require_unique(label: str, values: list[Any]) -> None:
    if len(values) != len(set(values)):
        duplicates = sorted(
            (value for value, count in Counter(values).items() if count > 1),
            key=str,
        )
        raise ValueError(f"Duplicate {label} values: {duplicates}")
