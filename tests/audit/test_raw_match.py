from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from astropy.table import Table

from foundinspace.catalogs.audit.raw_match import (
    RAW_COMBINED_MAP_FILENAME,
    RAW_MATCH_EVIDENCE_FILENAME,
    RAW_SUPPLEMENTAL_MAP_FILENAME,
    build_raw_supplemental_crossmatch,
    propagate_hip_sky_to_gaia_epoch,
    run_raw_gaia_hip_match,
)


def _write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        pa.Table.from_pandas(df, preserve_index=False), str(path), compression="zstd"
    )


def _write_hip_ecsv(path: Path) -> None:
    table = Table(
        {
            "HIP": [10, 11, 12, 13],
            "RArad": [10.0, 20.0, 30.0, 40.0],
            "DErad": [0.0, 0.0, 0.0, 0.0],
            "Plx": [10.0, 20.0, -1.0, 5.0],
            "e_Plx": [0.1, 0.1, 9.0, 0.2],
            "pmRA": [0.0, 0.0, 0.0, 0.0],
            "pmDE": [0.0, 0.0, 0.0, 0.0],
            "Hpmag": [9.0, 8.0, 10.0, 7.0],
            "Sn": [5, 5, 5, 5],
        }
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    table.write(path, format="ascii.ecsv", overwrite=True)


def test_raw_match_writes_clean_supplemental_and_official_comparison(tmp_path: Path):
    pytest.importorskip("scipy")

    hip_ecsv = tmp_path / "hip.ecsv"
    gaia_path = tmp_path / "gaia.parquet"
    official_path = tmp_path / "official.parquet"
    output_dir = tmp_path / "raw"
    _write_hip_ecsv(hip_ecsv)

    arcsec = 1.0 / 3600.0
    _write_parquet(
        pd.DataFrame(
            {
                "source_id": [100, 101, 102, 103, 104],
                "ra": [
                    10.0 + 0.10 * arcsec,
                    20.0 + 0.10 * arcsec,
                    30.0 + 0.10 * arcsec,
                    30.0 + 0.20 * arcsec,
                    40.0 + 0.10 * arcsec,
                ],
                "dec": [0.0, 0.0, 0.0, 0.0, 0.0],
                "phot_g_mean_mag": [9.05, 8.05, 10.05, 10.10, 7.05],
                "phot_bp_mean_mag": [9.5, 8.5, 10.5, 10.6, 7.5],
                "phot_rp_mean_mag": [8.5, 7.5, 9.5, 9.6, 6.5],
            }
        ),
        gaia_path,
    )
    _write_parquet(
        pd.DataFrame(
            {
                "gaia_source_id": [101, 999],
                "hip_source_id": [11, 13],
                "mapping_source": ["official", "official"],
                "number_of_neighbours": [1, 1],
                "angular_distance": [0.1, 0.1],
            }
        ),
        official_path,
    )

    report = run_raw_gaia_hip_match(
        hip_ecsv_path=hip_ecsv,
        gaia_parquet_path=gaia_path,
        official_crossmatch_path=official_path,
        output_dir=output_dir,
        max_sep_arcsec=1.0,
        max_mag_delta=0.5,
        batch_size=2,
        workers=1,
        force=True,
    )

    evidence = pd.read_parquet(output_dir / RAW_MATCH_EVIDENCE_FILENAME)
    by_pair = {
        (row.gaia_source_id, row.hip_source_id): row.decision
        for row in evidence.itertuples(index=False)
    }
    assert by_pair[("100", "10")] == "supplemental_match"
    assert by_pair[("101", "11")] == "official_confirmed"
    assert by_pair[("102", "12")] == "manual_review"
    assert by_pair[("103", "12")] == "manual_review"
    assert by_pair[("104", "13")] == "manual_review"

    supplemental = pd.read_parquet(output_dir / RAW_SUPPLEMENTAL_MAP_FILENAME)
    assert supplemental[["gaia_source_id", "hip_source_id"]].values.tolist() == [
        [100, 10]
    ]

    combined = pd.read_parquet(output_dir / RAW_COMBINED_MAP_FILENAME)
    assert combined[["gaia_source_id", "hip_source_id"]].values.tolist() == [
        [100, 10],
        [101, 11],
        [999, 13],
    ]
    assert report.evidence_rows == 5
    assert report.supplemental_rows == 1
    assert report.official_pairs_confirmed == 1


def test_raw_supplemental_crossmatch_is_empty_without_clean_matches():
    evidence = pd.DataFrame(
        {
            "gaia_source_id": ["1"],
            "hip_source_id": ["2"],
            "decision": ["manual_review"],
            "separation_arcsec": [0.1],
        }
    )
    supplemental = build_raw_supplemental_crossmatch(evidence)
    assert supplemental.empty


def test_raw_match_preserves_large_gaia_source_ids(tmp_path: Path):
    pytest.importorskip("scipy")

    hip_ecsv = tmp_path / "hip.ecsv"
    gaia_path = tmp_path / "gaia.parquet"
    official_path = tmp_path / "official.parquet"
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
    arcsec = 1.0 / 3600.0
    large_ids = [6068663998977123328, 6068663998977123456]
    _write_parquet(
        pd.DataFrame(
            {
                "source_id": large_ids,
                "ra": [10.0 + 0.1 * arcsec, 10.0 + 0.2 * arcsec],
                "dec": [0.0, 0.0],
                "phot_g_mean_mag": [9.05, 9.10],
                "phot_bp_mean_mag": [9.5, 9.6],
                "phot_rp_mean_mag": [8.5, 8.6],
            }
        ),
        gaia_path,
    )
    _write_parquet(
        pd.DataFrame(
            columns=[
                "gaia_source_id",
                "hip_source_id",
                "mapping_source",
                "number_of_neighbours",
                "angular_distance",
            ]
        ),
        official_path,
    )

    run_raw_gaia_hip_match(
        hip_ecsv_path=hip_ecsv,
        gaia_parquet_path=gaia_path,
        official_crossmatch_path=official_path,
        output_dir=output_dir,
        max_sep_arcsec=1.0,
        max_mag_delta=0.5,
        batch_size=2,
        workers=1,
        force=True,
    )
    evidence = pd.read_parquet(output_dir / RAW_MATCH_EVIDENCE_FILENAME)
    assert sorted(evidence["gaia_source_id"].tolist()) == [str(v) for v in large_ids]
    assert set(evidence["decision"]) == {"manual_review"}


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
