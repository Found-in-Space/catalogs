"""Reproducible assembly for the Gaia-Hipparcos pairing publication."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from astropy.table import Table

from foundinspace.catalogs.audit.raw_match import (
    RAW_PAIRING_EVIDENCE_FILENAME,
    RAW_PAIRING_REPORT_FILENAME,
)

PUBLICATION_EVIDENCE_FILENAME = "gaia_hip_pairing_evidence.parquet"
PUBLICATION_REPORT_FILENAME = "gaia_hip_pairing_report.json"
SUPPORT_PROVENANCE_FILENAME = "support_input_provenance.json"
CHECKSUMS_FILENAME = "checksums.sha256"

ACQUISITION_EVIDENCE_FILES = {
    "package.json": "gaia_acquisition_package.json",
    "evidence/gaia-download-state-summary.json": (
        "gaia-download-state-summary.json"
    ),
    "manifests/gaia-download-queries-manifest.tsv": (
        "gaia-download-queries-manifest.tsv"
    ),
    "manifests/gaia-votables-manifest.tsv": "gaia-votables-manifest.tsv",
    "manifests/gaia-votables.sha256": "gaia-votables.sha256",
    "provenance/git-head.txt": "gaia-acquisition-git-head.txt",
}

FORBIDDEN_PAIRING_FIELDS = {
    "decision",
    "evidence_category",
    "recommended_action",
    "action",
    "severity",
    "reasons",
    "gaia_mag_abs",
    "hip_mag_abs",
    "gaia_apparent_mag",
    "hip_apparent_mag",
    "apparent_mag_delta",
    "within_auto_thresholds",
    "within_distance_threshold",
    "within_tight_sky_threshold",
    "within_parallax_3d_threshold",
}


@dataclass(frozen=True)
class PairingPublicationAssembly:
    """Summary returned after assembling publication artifacts."""

    release_dir: str
    catalogs_commit: str
    evidence_path: str
    report_path: str
    support_provenance_path: str
    checksums_path: str
    pairing_rows: int
    h2bn_rows: int
    local_scan_rows: int
    overlap_rows: int


def assemble_pairing_publication(
    *,
    release_dir: Path,
    raw_output_dir: Path,
    gaia_compact_parquet: Path,
    gaia_summary: Path,
    gaia_package_dir: Path,
    hip_ecsv: Path,
    h2bn_ecsv: Path,
    h2bn_crossmatch: Path,
    hipparcos2_neighbourhood: Path,
    expected_pairing_rows: int = 124_207,
    expected_h2bn_rows: int = 99_525,
    expected_local_scan_rows: int = 122_678,
    expected_overlap_rows: int = 97_996,
    require_pushed: bool = True,
) -> PairingPublicationAssembly:
    """Assemble and validate the policy-neutral pairing publication."""

    release_dir = Path(release_dir).expanduser().resolve()
    raw_output_dir = Path(raw_output_dir).expanduser().resolve()
    repo_root = _git_repo_root(release_dir)
    catalogs_commit = _require_clean_committed_worktree(
        repo_root, require_pushed=require_pushed
    )

    evidence_source = raw_output_dir / RAW_PAIRING_EVIDENCE_FILENAME
    report_source = raw_output_dir / RAW_PAIRING_REPORT_FILENAME
    support_inputs = {
        "gaia_compact_parquet": Path(gaia_compact_parquet).expanduser().resolve(),
        "gaia_summary": Path(gaia_summary).expanduser().resolve(),
        "hipparcos2_ecsv": Path(hip_ecsv).expanduser().resolve(),
        "h2bn_raw_ecsv": Path(h2bn_ecsv).expanduser().resolve(),
        "h2bn_crossmatch_parquet": Path(h2bn_crossmatch).expanduser().resolve(),
        "hipparcos2_neighbourhood_ecsv": (
            Path(hipparcos2_neighbourhood).expanduser().resolve()
        ),
    }
    required_files = [evidence_source, report_source, *support_inputs.values()]
    for path in required_files:
        if not path.is_file():
            raise FileNotFoundError(str(path))

    gaia_package_dir = Path(gaia_package_dir).expanduser().resolve()
    acquisition_sources = {
        destination: gaia_package_dir / source
        for source, destination in ACQUISITION_EVIDENCE_FILES.items()
    }
    for path in acquisition_sources.values():
        if not path.is_file():
            raise FileNotFoundError(str(path))

    evidence = pq.read_table(evidence_source)
    counts = _validate_pairing_evidence(
        evidence,
        expected_pairing_rows=expected_pairing_rows,
        expected_h2bn_rows=expected_h2bn_rows,
        expected_local_scan_rows=expected_local_scan_rows,
        expected_overlap_rows=expected_overlap_rows,
    )
    source_report = json.loads(report_source.read_text())
    _validate_report(source_report, counts)

    evidence_dir = release_dir / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    publication_evidence = evidence_dir / PUBLICATION_EVIDENCE_FILENAME
    publication_report = evidence_dir / PUBLICATION_REPORT_FILENAME
    shutil.copy2(evidence_source, publication_evidence)
    publication_report.write_text(
        json.dumps(_publication_report(source_report), indent=2) + "\n"
    )
    shutil.copy2(gaia_summary, evidence_dir / "gaia_raw_match_g15_summary.json")
    for destination, source in acquisition_sources.items():
        shutil.copy2(source, evidence_dir / destination)

    obsolete_files = (
        release_dir / "catalog" / "fis_gaia_hip_supplemental_crossmatch_map.parquet",
        evidence_dir / "gaia_hip_crossmatch_evidence.parquet",
        evidence_dir / "gaia_hip_crossmatch_report.json",
    )
    for path in obsolete_files:
        if path.exists():
            path.unlink()
    obsolete_catalog_dir = release_dir / "catalog"
    if obsolete_catalog_dir.is_dir() and not any(obsolete_catalog_dir.iterdir()):
        obsolete_catalog_dir.rmdir()

    support_provenance = {
        "format_version": 1,
        "release": release_dir.name,
        "catalogs_commit": catalogs_commit,
        "catalogs_repository": "https://github.com/Found-in-Space/catalogs",
        "assembly_commit_time": _git_output(
            repo_root, "show", "-s", "--format=%cI", "HEAD"
        ),
        "policy_boundary": (
            "Pairing evidence only; no duplicate identity, winner, removal, "
            "or merged-record decision is made."
        ),
        "acquisition": {
            "max_sep_arcsec": float(source_report["max_sep_arcsec"]),
            "gaia_scope": "phot_g_mean_mag <= 15 in the compact Gaia table",
        },
        "observed_counts": counts,
        "support_inputs": {
            name: _file_record(path) for name, path in support_inputs.items()
        },
        "acquisition_evidence": {
            destination: _file_record(source)
            for destination, source in acquisition_sources.items()
        },
        "publication_artifacts": {
            PUBLICATION_EVIDENCE_FILENAME: _file_record(publication_evidence),
            PUBLICATION_REPORT_FILENAME: _file_record(publication_report),
        },
    }
    support_provenance_path = evidence_dir / SUPPORT_PROVENANCE_FILENAME
    support_provenance_path.write_text(
        json.dumps(support_provenance, indent=2, sort_keys=True) + "\n"
    )

    checksums_path = release_dir / CHECKSUMS_FILENAME
    regenerate_checksums(release_dir, checksums_path=checksums_path)
    return PairingPublicationAssembly(
        release_dir=str(release_dir),
        catalogs_commit=catalogs_commit,
        evidence_path=str(publication_evidence),
        report_path=str(publication_report),
        support_provenance_path=str(support_provenance_path),
        checksums_path=str(checksums_path),
        pairing_rows=counts["pairing_rows"],
        h2bn_rows=counts["h2bn_rows"],
        local_scan_rows=counts["local_scan_rows"],
        overlap_rows=counts["h2bn_local_overlap_rows"],
    )


def regenerate_checksums(release_dir: Path, *, checksums_path: Path) -> None:
    """Regenerate a complete SHA256 manifest for a publication directory."""

    release_dir = Path(release_dir).resolve()
    checksums_path = Path(checksums_path).resolve()
    files = sorted(
        path
        for path in release_dir.rglob("*")
        if path.is_file() and path.resolve() != checksums_path
    )
    lines = [
        f"{_sha256(path)}  {path.relative_to(release_dir).as_posix()}"
        for path in files
    ]
    checksums_path.write_text("\n".join(lines) + "\n")


def _validate_pairing_evidence(
    table: pa.Table,
    *,
    expected_pairing_rows: int,
    expected_h2bn_rows: int,
    expected_local_scan_rows: int,
    expected_overlap_rows: int,
) -> dict[str, int]:
    fields = set(table.column_names)
    missing = {
        "gaia_source_id",
        "hip_source_id",
        "h2bn_pair",
        "local_scan_pair",
        "gaia_g_minus_hip_hp_mag",
        "abs_gaia_g_minus_hip_hp_mag",
        "radial_gap_pc",
        "radial_gap_sigma",
    } - fields
    if missing:
        raise ValueError(f"Pairing evidence is missing fields: {sorted(missing)}")
    forbidden = sorted(fields & FORBIDDEN_PAIRING_FIELDS)
    if forbidden:
        raise ValueError(f"Pairing evidence contains policy fields: {forbidden}")
    if table.schema.field("gaia_source_id").type != pa.uint64():
        raise ValueError("gaia_source_id must be stored as uint64")

    frame = table.select(
        ["gaia_source_id", "hip_source_id", "h2bn_pair", "local_scan_pair"]
    ).to_pandas()
    if frame.duplicated(["gaia_source_id", "hip_source_id"]).any():
        raise ValueError("Pairing evidence contains duplicate Gaia/HIP pairs")
    h2bn = frame["h2bn_pair"].fillna(False).astype(bool)
    local = frame["local_scan_pair"].fillna(False).astype(bool)
    counts = {
        "pairing_rows": int(len(frame)),
        "h2bn_rows": int(h2bn.sum()),
        "local_scan_rows": int(local.sum()),
        "h2bn_local_overlap_rows": int((h2bn & local).sum()),
        "h2bn_only_rows": int((h2bn & ~local).sum()),
        "local_only_rows": int((~h2bn & local).sum()),
    }
    expected = {
        "pairing_rows": expected_pairing_rows,
        "h2bn_rows": expected_h2bn_rows,
        "local_scan_rows": expected_local_scan_rows,
        "h2bn_local_overlap_rows": expected_overlap_rows,
    }
    mismatches = {
        key: {"expected": value, "observed": counts[key]}
        for key, value in expected.items()
        if counts[key] != value
    }
    if mismatches:
        raise ValueError(f"Pairing evidence count mismatch: {mismatches}")
    return counts


def _validate_report(report: dict[str, Any], counts: dict[str, int]) -> None:
    forbidden = sorted(set(report) & FORBIDDEN_PAIRING_FIELDS)
    if forbidden:
        raise ValueError(f"Pairing report contains policy fields: {forbidden}")
    for key, value in counts.items():
        if key in report and int(report[key]) != value:
            raise ValueError(
                f"Pairing report {key}={report[key]} does not match evidence {value}"
            )
    for key in ("radial_gap_bins", "abs_apparent_mag_difference_bins"):
        bins = report.get(key)
        if not isinstance(bins, dict) or sum(int(value) for value in bins.values()) != (
            counts["pairing_rows"]
        ):
            raise ValueError(f"Pairing report {key} does not total pairing rows")


def _publication_report(report: dict[str, Any]) -> dict[str, Any]:
    excluded = {
        key
        for key in report
        if key.endswith("_path") or key in {"output_dir"}
    }
    published = {key: value for key, value in report.items() if key not in excluded}
    published["pairing_evidence_path"] = (
        f"evidence/{PUBLICATION_EVIDENCE_FILENAME}"
    )
    published["report_path"] = f"evidence/{PUBLICATION_REPORT_FILENAME}"
    return published


def _git_repo_root(path: Path) -> Path:
    probe = path if path.exists() else path.parent
    result = subprocess.run(
        ["git", "-C", str(probe), "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip()).resolve()


def _require_clean_committed_worktree(
    repo_root: Path, *, require_pushed: bool
) -> str:
    status = _git_output(
        repo_root, "status", "--porcelain", "--untracked-files=all"
    )
    if status:
        raise ValueError("Publication assembly requires a clean committed worktree")
    commit = _git_output(repo_root, "rev-parse", "HEAD")
    if require_pushed:
        upstream = _git_output(
            repo_root,
            "rev-parse",
            "--abbrev-ref",
            "--symbolic-full-name",
            "@{upstream}",
        )
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "merge-base",
                "--is-ancestor",
                commit,
                upstream,
            ],
            check=False,
        )
        if result.returncode != 0:
            raise ValueError(
                f"Publication assembly requires {commit} to be present on {upstream}"
            )
    return commit


def _git_output(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _file_record(path: Path) -> dict[str, Any]:
    record: dict[str, Any] = {
        "name": path.name,
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
    }
    if path.suffix.lower() == ".parquet":
        record["rows"] = pq.ParquetFile(path).metadata.num_rows
    elif path.suffix.lower() == ".ecsv":
        record["rows"] = len(Table.read(path, format="ascii.ecsv"))
    return record


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
