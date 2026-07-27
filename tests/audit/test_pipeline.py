from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from foundinspace.catalogs.audit.pipeline import (
    MANUAL_CANDIDATES_CSV_FILENAME,
    MANUAL_CANDIDATES_FILENAME,
    MATCH_EVIDENCE_COLS,
    MATCH_EVIDENCE_FILENAME,
    OCTREE_REVIEW_FILENAME,
    run_audit_match,
    run_audit_report,
)
from foundinspace.pipeline.constants import OUTPUT_COLS
from foundinspace.pipeline.gaia_to_hip.pipeline import GAIA_HIP_MAP_COLS


def _write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        pa.Table.from_pandas(df, preserve_index=False), str(path), compression="zstd"
    )


def _row(
    *,
    source: str,
    source_id: int | str,
    ra_deg: float,
    dec_deg: float = 0.0,
    r_pc: float = 100.0,
    mag_abs: float = 4.0,
    astrometry_quality: float = 0.1,
    photometry_quality: float = 0.1,
    teff: float = 5000.0,
) -> dict:
    return {
        "source": source,
        "source_id": source_id,
        "x_icrs_pc": r_pc,
        "y_icrs_pc": 0.0,
        "z_icrs_pc": 0.0,
        "ra_deg": ra_deg,
        "dec_deg": dec_deg,
        "r_pc": r_pc,
        "mag_abs": mag_abs,
        "teff": teff,
        "quality_flags": 1,
        "astrometry_quality": astrometry_quality,
        "photometry_quality": photometry_quality,
    }


def _empty_overrides(path: Path) -> None:
    _write_parquet(
        pd.DataFrame(
            columns=[
                *OUTPUT_COLS,
                "override_id",
                "action",
                "override_reason",
                "override_policy_version",
            ]
        ),
        path,
    )


def test_staged_match_writes_policy_neutral_pair_union(tmp_path: Path):
    pytest.importorskip("scipy")

    gaia_dir = tmp_path / "gaia"
    hip_path = tmp_path / "hip.parquet"
    h2bn_path = tmp_path / "h2bn.parquet"
    audit_dir = tmp_path / "audit"
    arcsec = 1.0 / 3600.0
    overlap_id = 6_068_663_998_977_123_328
    local_only_id = 6_068_663_998_977_123_456
    missing_id = 6_068_663_998_977_123_999

    gaia_rows = [
        {
            **_row(source="gaia", source_id=overlap_id, ra_deg=10.0, r_pc=200.0),
            "ruwe": 1.1,
            "phot_g_mean_mag": 8.5,
        },
        {
            **_row(source="gaia", source_id=local_only_id, ra_deg=20.0, r_pc=100.0),
            "ruwe": 1.2,
            "phot_g_mean_mag": 14.0,
        },
    ]
    _write_parquet(pd.DataFrame(gaia_rows), gaia_dir / "g.parquet")
    hip_rows = [
        {
            **_row(
                source="hip",
                source_id=10,
                ra_deg=10.0 + 0.1 * arcsec,
                r_pc=100.0,
            ),
            "Sn": 5,
            "Hpmag": 9.0,
        },
        {
            **_row(
                source="hip",
                source_id=20,
                ra_deg=20.0 + 0.1 * arcsec,
                r_pc=100.0,
            ),
            "Sn": 5,
            "Hpmag": 7.0,
        },
    ]
    _write_parquet(pd.DataFrame(hip_rows), hip_path)
    _write_parquet(
        pd.DataFrame(
            [
                {
                    "gaia_source_id": overlap_id,
                    "hip_source_id": 10,
                    "mapping_source": "h2bn",
                    "number_of_neighbours": 1,
                    "angular_distance": 0.1,
                },
                {
                    "gaia_source_id": missing_id,
                    "hip_source_id": 99,
                    "mapping_source": "h2bn",
                    "number_of_neighbours": 2,
                    "angular_distance": 0.3,
                },
            ]
        ),
        h2bn_path,
    )

    report = run_audit_match(
        gaia_dir=gaia_dir,
        hip_path=hip_path,
        h2bn_crossmatch_path=h2bn_path,
        audit_dir=audit_dir,
        force=True,
    )

    evidence_path = audit_dir / MATCH_EVIDENCE_FILENAME
    evidence = pd.read_parquet(evidence_path)
    assert list(evidence.columns) == MATCH_EVIDENCE_COLS
    assert (
        pq.ParquetFile(evidence_path).schema_arrow.field("gaia_source_id").type
        == pa.uint64()
    )
    assert len(evidence) == 3
    by_pair = {
        (int(row.gaia_source_id), int(row.hip_source_id)): row
        for row in evidence.itertuples(index=False)
    }
    assert bool(by_pair[(overlap_id, 10)].h2bn_pair) is True
    assert bool(by_pair[(overlap_id, 10)].local_scan_pair) is True
    assert by_pair[(overlap_id, 10)].gaia_g_minus_hip_hp_mag == pytest.approx(-0.5)
    assert by_pair[(overlap_id, 10)].radial_gap_pc == pytest.approx(100.0)
    assert bool(by_pair[(local_only_id, 20)].h2bn_pair) is False
    assert bool(by_pair[(local_only_id, 20)].local_scan_pair) is True
    assert by_pair[(local_only_id, 20)].abs_gaia_g_minus_hip_hp_mag == pytest.approx(
        7.0
    )
    assert pd.isna(by_pair[(missing_id, 99)].gaia_g_mag)
    assert report.pairing_rows == 3
    assert report.h2bn_local_overlap_rows == 1
    assert report.h2bn_only_rows == 1
    assert report.local_only_rows == 1
    assert sum(report.radial_gap_bins.values()) == 3

    forbidden_fields = {"decision", "recommended_action", "severity", "action"}
    assert forbidden_fields.isdisjoint(evidence.columns)
    report_json = json.loads((audit_dir / "pairing_report.json").read_text())
    assert forbidden_fields.isdisjoint(report_json)
    assert not (audit_dir / "supplemental_gaia_hip_map.parquet").exists()
    assert not (audit_dir / "combined_gaia_hip_map.parquet").exists()


def test_audit_report_ignores_policy_neutral_pairing_rows(tmp_path: Path):
    pytest.importorskip("scipy")

    gaia_dir = tmp_path / "gaia"
    hip_path = tmp_path / "hip.parquet"
    crossmatch_path = tmp_path / "official.parquet"
    overrides_path = tmp_path / "overrides.parquet"
    identifiers_path = tmp_path / "identifiers.parquet"
    merge_dir = tmp_path / "merged"
    sidecar_dir = tmp_path / "sidecars"
    audit_dir = merge_dir / "audit"

    _write_parquet(pd.DataFrame(columns=OUTPUT_COLS), gaia_dir / "g.parquet")
    _write_parquet(pd.DataFrame(columns=[*OUTPUT_COLS, "Sn", "Hpmag"]), hip_path)
    _write_parquet(pd.DataFrame(columns=GAIA_HIP_MAP_COLS), crossmatch_path)
    _empty_overrides(overrides_path)
    _write_parquet(
        pd.DataFrame(
            columns=[
                "source",
                "source_id",
                "proper_name",
                "bayer",
                "constellation",
                "hd",
                "hip_id",
            ]
        ),
        identifiers_path,
    )
    _write_parquet(pd.DataFrame(), merge_dir / "merge_decisions.parquet")
    _write_parquet(
        pd.DataFrame(
            [
                _row(
                    source="hip",
                    source_id="90910",
                    ra_deg=100.0,
                    dec_deg=10.0,
                    r_pc=50_000.0,
                    mag_abs=-12.0,
                    astrometry_quality=10.0,
                )
            ],
            columns=OUTPUT_COLS,
        ),
        merge_dir / "healpix" / "0" / "part.parquet",
    )
    neutral_evidence = pd.DataFrame(
        [
            {
                **dict.fromkeys(MATCH_EVIDENCE_COLS, pd.NA),
                "gaia_source_id": 100,
                "hip_source_id": 200,
                "h2bn_pair": False,
                "local_scan_pair": True,
                "separation_arcsec": 0.5,
            }
        ],
        columns=MATCH_EVIDENCE_COLS,
    )
    _write_parquet(neutral_evidence, audit_dir / MATCH_EVIDENCE_FILENAME)

    report = run_audit_report(
        gaia_dir=gaia_dir,
        hip_path=hip_path,
        official_crossmatch_path=crossmatch_path,
        overrides_path=overrides_path,
        identifiers_path=identifiers_path,
        merge_dir=merge_dir,
        sidecar_output_dir=sidecar_dir,
        healpix_order=1,
        audit_dir=audit_dir,
        force=True,
    )

    octree = pd.read_parquet(audit_dir / OCTREE_REVIEW_FILENAME)
    manual = pd.read_parquet(audit_dir / MANUAL_CANDIDATES_FILENAME)
    manual_csv = pd.read_csv(audit_dir / MANUAL_CANDIDATES_CSV_FILENAME)
    assert report.octree_review_rows == 1
    assert octree["display_action"].tolist() == ["quarantine_suspicious_star"]
    assert len(manual) == 1
    assert len(manual_csv) == len(manual)
    assert manual["issue_type"].iloc[0] == "merged_row_extreme"
