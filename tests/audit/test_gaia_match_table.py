from __future__ import annotations

import base64
import gzip
import json
import struct
from math import isnan
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from foundinspace.catalogs.audit.gaia_match_table import (
    GAIA_RAW_MATCH_COLUMNS,
    build_gaia_raw_match_table,
)

FIELDS = [
    ("source_id", "long", ">q"),
    ("ra", "double", ">d"),
    ("dec", "double", ">d"),
    ("parallax", "double", ">d"),
    ("parallax_error", "float", ">f"),
    ("phot_g_mean_mag", "float", ">f"),
    ("phot_bp_mean_mag", "float", ">f"),
    ("phot_rp_mean_mag", "float", ">f"),
]


def test_gaia_match_table_filters_and_preserves_large_ids(tmp_path: Path) -> None:
    votable = tmp_path / "gaia.vot.gz"
    output = tmp_path / "gaia_match.parquet"
    summary_path = tmp_path / "gaia_match_summary.json"
    manifest = tmp_path / "gaia-votables-manifest.tsv"
    checksums = tmp_path / "gaia-votables.sha256"
    manifest.write_text("filename\tbytes\n", encoding="utf-8")
    checksums.write_text("placeholder  gaia.vot.gz\n", encoding="utf-8")
    large_id = 6068663998977123328
    _write_binary2_votable(
        votable,
        [
            {
                "source_id": large_id,
                "ra": 10.0,
                "dec": -2.0,
                "parallax": 10.0,
                "parallax_error": 0.1,
                "phot_g_mean_mag": 14.5,
                "phot_bp_mean_mag": 15.0,
                "phot_rp_mean_mag": 14.0,
            },
            {
                "source_id": large_id + 1,
                "ra": 11.0,
                "dec": -3.0,
                "parallax": 11.0,
                "parallax_error": 0.2,
                "phot_g_mean_mag": 15.1,
                "phot_bp_mean_mag": 15.6,
                "phot_rp_mean_mag": 14.6,
            },
            {
                "source_id": large_id + 2,
                "ra": 12.0,
                "dec": -4.0,
                "parallax": 12.0,
                "parallax_error": 0.3,
                "phot_bp_mean_mag": 15.2,
                "phot_rp_mean_mag": 14.2,
            },
            {
                "source_id": large_id + 3,
                "ra": 13.0,
                "dec": -5.0,
                "parallax": 13.0,
                "parallax_error": 0.4,
                "phot_g_mean_mag": 15.0,
                "phot_rp_mean_mag": 14.3,
            },
        ],
    )

    summary = build_gaia_raw_match_table(
        gaia_votable_paths=[votable],
        output_path=output,
        summary_path=summary_path,
        source_manifest_path=manifest,
        source_checksums_path=checksums,
        g_mag_limit=15.0,
        batch_rows=2,
    )

    table = pq.read_table(output)
    assert table.schema.field("source_id").type == pa.uint64()
    assert table.column_names == GAIA_RAW_MATCH_COLUMNS
    rows = table.to_pylist()
    assert [row["source_id"] for row in rows] == [large_id, large_id + 3]
    assert rows[0]["phot_g_mean_mag"] == pytest.approx(14.5)
    assert rows[1]["phot_g_mean_mag"] == pytest.approx(15.0)
    assert isnan(rows[1]["phot_bp_mean_mag"])

    summary_json = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary.rows_scanned == 4
    assert summary.rows_written == 2
    assert summary_json["rows_scanned"] == 4
    assert summary_json["rows_written"] == 2
    assert summary_json["source_manifest_path"] == str(manifest)
    assert summary_json["source_checksums_path"] == str(checksums)
    assert len(summary_json["output_sha256"]) == 64
    assert summary_json["input_files"][0]["rows_scanned"] == 4
    assert summary_json["input_files"][0]["rows_written"] == 2


def test_gaia_match_table_requires_overwrite_for_existing_outputs(
    tmp_path: Path,
) -> None:
    votable = tmp_path / "gaia.vot.gz"
    output = tmp_path / "gaia_match.parquet"
    summary_path = tmp_path / "gaia_match_summary.json"
    _write_binary2_votable(
        votable,
        [
            {
                "source_id": 1,
                "ra": 10.0,
                "dec": 0.0,
                "parallax": 10.0,
                "parallax_error": 0.1,
                "phot_g_mean_mag": 9.0,
                "phot_bp_mean_mag": 9.4,
                "phot_rp_mean_mag": 8.4,
            }
        ],
    )
    output.write_bytes(b"existing")

    with pytest.raises(FileExistsError):
        build_gaia_raw_match_table(
            gaia_votable_paths=[votable],
            output_path=output,
            summary_path=summary_path,
        )


def _write_binary2_votable(path: Path, rows: list[dict[str, float | int]]) -> None:
    raw_rows = b"".join(_pack_binary2_row(row) for row in rows)
    payload = base64.b64encode(raw_rows).decode("ascii")
    fields = "\n".join(
        f'<FIELD datatype="{datatype}" name="{name}" />'
        for name, datatype, _ in FIELDS
    )
    text = f"""<?xml version="1.0" encoding="UTF-8"?>
<VOTABLE version="1.4">
<RESOURCE type="results">
<TABLE>
{fields}
<DATA>
<BINARY2>
<STREAM encoding="base64">
{payload}
</STREAM>
</BINARY2>
</DATA>
</TABLE>
</RESOURCE>
</VOTABLE>
"""
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        fh.write(text)


def _pack_binary2_row(row: dict[str, float | int]) -> bytes:
    flags = bytearray((len(FIELDS) + 7) // 8)
    values = bytearray()
    for index, (name, _, fmt) in enumerate(FIELDS):
        if name not in row:
            flags[index // 8] |= 1 << (7 - (index % 8))
            value = 0
        else:
            value = row[name]
        values.extend(struct.pack(fmt, value))
    return bytes(flags) + bytes(values)
