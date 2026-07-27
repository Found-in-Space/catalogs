from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from astropy.table import Table

from foundinspace.catalogs.audit.raw_match import (
    RAW_PAIRING_EVIDENCE_COLS,
    RAW_PAIRING_EVIDENCE_FILENAME,
    RAW_PAIRING_REPORT_FILENAME,
    propagate_hip_sky_to_gaia_epoch,
    run_raw_gaia_hip_match,
)


def _write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        pa.Table.from_pandas(df, preserve_index=False), str(path), compression="zstd"
    )


def _write_mapping(path: Path, rows: list[dict]) -> None:
    columns = [
        "gaia_source_id",
        "hip_source_id",
        "mapping_source",
        "number_of_neighbours",
        "angular_distance",
    ]
    _write_parquet(pd.DataFrame(rows, columns=columns), path)


def test_raw_match_writes_policy_neutral_union_and_measurements(tmp_path: Path):
    pytest.importorskip("scipy")

    hip_ecsv = tmp_path / "hip.ecsv"
    gaia_path = tmp_path / "gaia.parquet"
    h2bn_path = tmp_path / "h2bn.parquet"
    neighbourhood_path = tmp_path / "neighbourhood.parquet"
    output_dir = tmp_path / "raw"
    Table(
        {
            "HIP": [10, 11, 12],
            "RArad": [10.0, 20.0, 30.0],
            "DErad": [0.0, 0.0, 0.0],
            "Plx": [10.0, 20.0, 10.0],
            "e_Plx": [0.1, 0.2, 0.1],
            "pmRA": [0.0, 0.0, 0.0],
            "pmDE": [0.0, 0.0, 0.0],
            "Hpmag": [9.0, 8.0, 7.0],
            "Sn": [5, 5, 5],
        }
    ).write(hip_ecsv, format="ascii.ecsv", overwrite=True)

    arcsec = 1.0 / 3600.0
    overlap_id = 6_068_663_998_977_123_328
    local_only_id = 6_068_663_998_977_123_456
    missing_gaia_id = 6_068_663_998_977_123_999
    _write_parquet(
        pd.DataFrame(
            {
                "source_id": pd.Series(
                    [overlap_id, local_only_id], dtype="uint64"
                ),
                "ra": [10.0 + 0.1 * arcsec, 30.0 + 0.2 * arcsec],
                "dec": [0.0, 0.0],
                "phot_g_mean_mag": [8.5, 10.0],
                "phot_bp_mean_mag": [9.0, 10.5],
                "phot_rp_mean_mag": [8.0, 9.5],
                "parallax": [5.0, 10.0],
                "parallax_error": [0.1, 0.1],
            }
        ),
        gaia_path,
    )
    _write_mapping(
        h2bn_path,
        [
            {
                "gaia_source_id": overlap_id,
                "hip_source_id": 10,
                "mapping_source": "h2bn",
                "number_of_neighbours": 1,
                "angular_distance": 0.1,
            },
            {
                "gaia_source_id": missing_gaia_id,
                "hip_source_id": 11,
                "mapping_source": "h2bn",
                "number_of_neighbours": 2,
                "angular_distance": 0.3,
            },
        ],
    )
    _write_mapping(
        neighbourhood_path,
        [
            {
                "gaia_source_id": 999,
                "hip_source_id": 12,
                "mapping_source": "neighbourhood",
                "number_of_neighbours": 1,
                "angular_distance": 0.2,
            }
        ],
    )

    report = run_raw_gaia_hip_match(
        hip_ecsv_path=hip_ecsv,
        gaia_parquet_path=gaia_path,
        h2bn_crossmatch_path=h2bn_path,
        hipparcos2_neighbourhood_path=neighbourhood_path,
        output_dir=output_dir,
        max_sep_arcsec=5.0,
        batch_size=1,
        workers=1,
        force=True,
    )

    evidence_path = output_dir / RAW_PAIRING_EVIDENCE_FILENAME
    evidence = pd.read_parquet(evidence_path)
    assert list(evidence.columns) == RAW_PAIRING_EVIDENCE_COLS
    assert (
        pq.ParquetFile(evidence_path).schema_arrow.field("gaia_source_id").type
        == pa.uint64()
    )
    assert len(evidence) == 3
    assert not evidence.duplicated(["gaia_source_id", "hip_source_id"]).any()
    by_pair = {
        (int(row.gaia_source_id), int(row.hip_source_id)): row
        for row in evidence.itertuples(index=False)
    }

    overlap = by_pair[(overlap_id, 10)]
    assert bool(overlap.h2bn_pair) is True
    assert bool(overlap.local_scan_pair) is True
    assert overlap.gaia_g_minus_hip_hp_mag == pytest.approx(-0.5)
    assert overlap.abs_gaia_g_minus_hip_hp_mag == pytest.approx(0.5)
    assert overlap.radial_gap_pc == pytest.approx(100.0)
    assert overlap.combined_distance_sigma_pc == pytest.approx(
        (4.0**2 + 1.0**2) ** 0.5
    )
    assert overlap.radial_gap_sigma > 20
    assert overlap.parallax_3d_separation_pc == pytest.approx(100.0, rel=1e-6)

    local_only = by_pair[(local_only_id, 12)]
    assert bool(local_only.h2bn_pair) is False
    assert bool(local_only.local_scan_pair) is True
    assert bool(local_only.hipparcos2_neighbourhood_conflict) is True

    h2bn_only = by_pair[(missing_gaia_id, 11)]
    assert bool(h2bn_only.h2bn_pair) is True
    assert bool(h2bn_only.local_scan_pair) is False
    assert pd.isna(h2bn_only.gaia_g_mag)
    assert pd.isna(h2bn_only.gaia_candidate_count)
    assert h2bn_only.h2bn_number_of_neighbours == 2

    forbidden = {
        "decision",
        "recommended_action",
        "severity",
        "reasons",
        "gaia_mag_abs",
        "hip_mag_abs",
        "within_tight_sky_threshold",
        "within_parallax_3d_threshold",
    }
    assert forbidden.isdisjoint(evidence.columns)
    assert report.pairing_rows == 3
    assert report.h2bn_rows == 2
    assert report.local_scan_rows == 2
    assert report.h2bn_local_overlap_rows == 1
    assert report.h2bn_only_rows == 1
    assert report.local_only_rows == 1
    assert sum(report.radial_gap_bins.values()) == 3
    assert sum(report.abs_apparent_mag_difference_bins.values()) == 3
    report_json = json.loads((output_dir / RAW_PAIRING_REPORT_FILENAME).read_text())
    assert forbidden.isdisjoint(report_json)

    for forbidden_filename in (
        "raw_supplemental_gaia_hip_map.parquet",
        "raw_combined_gaia_hip_map.parquet",
    ):
        assert not (output_dir / forbidden_filename).exists()


def test_raw_match_includes_h2bn_pair_with_missing_hip_measurements(tmp_path: Path):
    pytest.importorskip("scipy")

    hip_ecsv = tmp_path / "hip.ecsv"
    gaia_path = tmp_path / "gaia.parquet"
    h2bn_path = tmp_path / "h2bn.parquet"
    output_dir = tmp_path / "raw"
    Table(
        {
            "HIP": [10],
            "RArad": [10.0],
            "DErad": [0.0],
            "pmRA": [0.0],
            "pmDE": [0.0],
            "Hpmag": [9.0],
        }
    ).write(hip_ecsv, format="ascii.ecsv", overwrite=True)
    _write_parquet(
        pd.DataFrame(
            {
                "source_id": pd.Series([100], dtype="uint64"),
                "ra": [10.0],
                "dec": [0.0],
                "phot_g_mean_mag": [9.0],
                "phot_bp_mean_mag": [9.5],
                "phot_rp_mean_mag": [8.5],
            }
        ),
        gaia_path,
    )
    _write_mapping(
        h2bn_path,
        [
            {
                "gaia_source_id": 100,
                "hip_source_id": 999,
                "mapping_source": "h2bn",
                "number_of_neighbours": 1,
                "angular_distance": 0.5,
            }
        ],
    )

    report = run_raw_gaia_hip_match(
        hip_ecsv_path=hip_ecsv,
        gaia_parquet_path=gaia_path,
        h2bn_crossmatch_path=h2bn_path,
        output_dir=output_dir,
        max_sep_arcsec=1.0,
        workers=1,
        force=True,
    )
    evidence = pd.read_parquet(output_dir / RAW_PAIRING_EVIDENCE_FILENAME)
    h2bn = evidence.loc[evidence["hip_source_id"].eq(999)].iloc[0]
    assert bool(h2bn["h2bn_pair"]) is True
    assert pd.isna(h2bn["hip_hp_mag"])
    assert report.rows_missing_hip_measurements == 1


def test_hip_propagation_uses_proper_motion():
    ra, dec = propagate_hip_sky_to_gaia_epoch(
        pd.Series([10.0]).to_numpy(),
        pd.Series([0.0]).to_numpy(),
        pd.Series([1000.0]).to_numpy(),
        pd.Series([0.0]).to_numpy(),
    )
    expected_deg = 10.0 + 24.75 / 3600.0
    assert ra[0] == pytest.approx(expected_deg, abs=1e-6)
    assert dec[0] == pytest.approx(0.0)
