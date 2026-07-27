from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from astropy.table import Table

from foundinspace.catalogs.audit.publication import (
    PUBLICATION_EVIDENCE_FILENAME,
    PUBLICATION_REPORT_FILENAME,
    assemble_pairing_publication,
)
from foundinspace.catalogs.audit.raw_match import (
    RAW_PAIRING_EVIDENCE_FILENAME,
    RAW_PAIRING_REPORT_FILENAME,
)


def _write_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pandas(frame, preserve_index=False), path)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_assemble_pairing_publication_hashes_inputs_and_checksums(tmp_path: Path):
    repo = tmp_path / "catalogs"
    release = repo / "publications" / "20260630.2"
    release.mkdir(parents=True)
    (release / "README.md").write_text("# Pairing evidence\n")

    raw_output = repo / "scratch" / "raw"
    evidence = pd.DataFrame(
        {
            "gaia_source_id": pd.Series([6_068_663_998_977_123_328, 2], dtype="uint64"),
            "hip_source_id": pd.Series([10, 20], dtype="uint64"),
            "h2bn_pair": [True, False],
            "local_scan_pair": [True, True],
            "gaia_g_minus_hip_hp_mag": [-0.5, 2.0],
            "abs_gaia_g_minus_hip_hp_mag": [0.5, 2.0],
            "radial_gap_pc": [1.0, None],
            "radial_gap_sigma": [0.5, None],
        }
    )
    _write_parquet(evidence, raw_output / RAW_PAIRING_EVIDENCE_FILENAME)
    report = {
        "hip_ecsv_path": "inputs/hip.ecsv",
        "gaia_parquet_path": "inputs/gaia.parquet",
        "h2bn_crossmatch_path": "inputs/h2bn.parquet",
        "output_dir": "scratch/raw",
        "pairing_evidence_path": "scratch/raw/raw_pairing_evidence.parquet",
        "report_path": "scratch/raw/raw_pairing_report.json",
        "max_sep_arcsec": 5.0,
        "pairing_rows": 2,
        "h2bn_rows": 1,
        "local_scan_rows": 2,
        "h2bn_local_overlap_rows": 1,
        "h2bn_only_rows": 0,
        "local_only_rows": 1,
        "radial_gap_bins": {
            "le_1_pc": 1,
            "1_to_3_pc": 0,
            "3_to_5_pc": 0,
            "5_to_10_pc": 0,
            "gt_10_pc": 0,
            "missing": 1,
        },
        "abs_apparent_mag_difference_bins": {
            "le_0_5_mag": 1,
            "0_5_to_1_mag": 0,
            "1_to_2_mag": 1,
            "gt_2_mag": 0,
            "missing": 0,
        },
    }
    (raw_output / RAW_PAIRING_REPORT_FILENAME).write_text(
        json.dumps(report) + "\n"
    )

    inputs = repo / "inputs"
    inputs.mkdir()
    gaia_compact = inputs / "gaia.parquet"
    _write_parquet(pd.DataFrame({"source_id": [1]}), gaia_compact)
    gaia_summary = inputs / "gaia-summary.json"
    gaia_summary.write_text('{"rows_written": 1}\n')
    hip_ecsv = inputs / "hip.ecsv"
    Table({"HIP": [10]}).write(hip_ecsv, format="ascii.ecsv")
    h2bn_ecsv = inputs / "h2bn.ecsv"
    Table({"source_id": [1], "original_ext_source_id": [10]}).write(
        h2bn_ecsv, format="ascii.ecsv"
    )
    h2bn_parquet = inputs / "h2bn.parquet"
    _write_parquet(
        pd.DataFrame({"gaia_source_id": [1], "hip_source_id": [10]}),
        h2bn_parquet,
    )
    neighbourhood = inputs / "neighbourhood.ecsv"
    Table({"source_id": [1], "original_ext_source_id": [10]}).write(
        neighbourhood, format="ascii.ecsv"
    )

    package = inputs / "package"
    package_files = {
        "package.json": "{}\n",
        "evidence/gaia-download-state-summary.json": "{}\n",
        "manifests/gaia-download-queries-manifest.tsv": "query\n",
        "manifests/gaia-votables-manifest.tsv": "file\n",
        "manifests/gaia-votables.sha256": "abc  file\n",
        "provenance/git-head.txt": "deadbeef\n",
    }
    for relative, content in package_files.items():
        path = package / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    subprocess.run(["git", "init", "-b", "main", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@example.com"],
        check=True,
    )
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "base"], check=True)

    result = assemble_pairing_publication(
        release_dir=release,
        raw_output_dir=raw_output,
        gaia_compact_parquet=gaia_compact,
        gaia_summary=gaia_summary,
        gaia_package_dir=package,
        hip_ecsv=hip_ecsv,
        h2bn_ecsv=h2bn_ecsv,
        h2bn_crossmatch=h2bn_parquet,
        hipparcos2_neighbourhood=neighbourhood,
        expected_pairing_rows=2,
        expected_h2bn_rows=1,
        expected_local_scan_rows=2,
        expected_overlap_rows=1,
        require_pushed=False,
    )

    evidence_dir = release / "evidence"
    assert (evidence_dir / PUBLICATION_EVIDENCE_FILENAME).is_file()
    published_report = json.loads(
        (evidence_dir / PUBLICATION_REPORT_FILENAME).read_text()
    )
    assert "gaia_parquet_path" not in published_report
    provenance = json.loads(
        (evidence_dir / "support_input_provenance.json").read_text()
    )
    assert provenance["support_inputs"]["h2bn_raw_ecsv"]["sha256"] == _sha256(
        h2bn_ecsv
    )
    assert provenance["observed_counts"]["pairing_rows"] == 2
    checksum_lines = (release / "checksums.sha256").read_text().splitlines()
    checksummed_paths = {line.split("  ", 1)[1] for line in checksum_lines}
    expected_paths = {
        path.relative_to(release).as_posix()
        for path in release.rglob("*")
        if path.is_file() and path.name != "checksums.sha256"
    }
    assert checksummed_paths == expected_paths
    assert result.catalogs_commit == subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
