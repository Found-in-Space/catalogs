"""Build a compact Gaia table for raw Gaia/HIP matching."""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

GAIA_RAW_MATCH_COLUMNS = [
    "source_id",
    "ra",
    "dec",
    "phot_g_mean_mag",
    "phot_bp_mean_mag",
    "phot_rp_mean_mag",
    "parallax",
    "parallax_error",
]

GAIA_RAW_MATCH_SCHEMA = pa.schema(
    [
        ("source_id", pa.uint64()),
        ("ra", pa.float64()),
        ("dec", pa.float64()),
        ("phot_g_mean_mag", pa.float32()),
        ("phot_bp_mean_mag", pa.float32()),
        ("phot_rp_mean_mag", pa.float32()),
        ("parallax", pa.float64()),
        ("parallax_error", pa.float32()),
    ]
)

_FIELD_TAG_RE = re.compile(rb"<FIELD\b[^>]*>")
_ATTR_RE = re.compile(rb"([A-Za-z_:][\w:.-]*)\s*=\s*(['\"])(.*?)\2")
_NUMPY_DTYPE_BY_VOTABLE_TYPE = {
    "unsignedbyte": ">u1",
    "short": ">i2",
    "int": ">i4",
    "long": ">i8",
    "float": ">f4",
    "double": ">f8",
}
_NATIVE_DTYPE_BY_COLUMN = {
    "source_id": np.uint64,
    "ra": np.float64,
    "dec": np.float64,
    "phot_g_mean_mag": np.float32,
    "phot_bp_mean_mag": np.float32,
    "phot_rp_mean_mag": np.float32,
    "parallax": np.float64,
    "parallax_error": np.float32,
}


@dataclass(frozen=True)
class GaiaMatchTableInputSummary:
    """Per-input-file summary for a compact Gaia match-table conversion."""

    path: str
    bytes: int
    rows_scanned: int
    rows_written: int


@dataclass(frozen=True)
class GaiaMatchTableSummary:
    """JSON summary for the compact Gaia raw-match table."""

    input_paths: list[str]
    output_path: str
    summary_path: str | None
    source_manifest_path: str | None
    source_checksums_path: str | None
    g_mag_limit: float
    columns: list[str]
    rows_scanned: int
    rows_written: int
    input_files: list[GaiaMatchTableInputSummary]
    output_bytes: int
    output_sha256: str
    created_at: str


@dataclass(frozen=True)
class _VOTableField:
    name: str
    datatype: str
    arraysize: str | None


@dataclass(frozen=True)
class _Binary2Layout:
    fields: list[_VOTableField]
    dtype: np.dtype
    dtype_names: dict[str, str]
    field_indices: dict[str, int]
    null_mask_bytes: int
    row_size: int


def build_gaia_raw_match_table(
    *,
    gaia_votable_paths: list[Path],
    output_path: Path,
    summary_path: Path | None = None,
    source_manifest_path: Path | None = None,
    source_checksums_path: Path | None = None,
    g_mag_limit: float = 15.0,
    batch_rows: int = 100_000,
    overwrite: bool = False,
) -> GaiaMatchTableSummary:
    """Stream Gaia VOTables into a compact Parquet table for raw matching."""

    if not gaia_votable_paths:
        raise ValueError("At least one Gaia VOTable path is required")
    if batch_rows <= 0:
        raise ValueError("batch_rows must be positive")
    if not math.isfinite(g_mag_limit):
        raise ValueError("g_mag_limit must be finite")

    output_path = Path(output_path).expanduser()
    if summary_path is not None:
        summary_path = Path(summary_path).expanduser()
    if source_manifest_path is not None:
        source_manifest_path = Path(source_manifest_path).expanduser()
    if source_checksums_path is not None:
        source_checksums_path = Path(source_checksums_path).expanduser()

    existing_outputs = [output_path]
    if summary_path is not None:
        existing_outputs.append(summary_path)
    if not overwrite:
        existing = [str(path) for path in existing_outputs if path.exists()]
        if existing:
            joined = ", ".join(existing)
            raise FileExistsError(f"Gaia match-table outputs already exist: {joined}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    writer: pq.ParquetWriter | None = None
    rows_scanned = 0
    rows_written = 0
    input_summaries: list[GaiaMatchTableInputSummary] = []

    try:
        writer = pq.ParquetWriter(
            output_path,
            GAIA_RAW_MATCH_SCHEMA,
            compression="zstd",
        )
        for raw_path in gaia_votable_paths:
            path = Path(raw_path).expanduser()
            if not path.is_file():
                raise FileNotFoundError(str(path))
            file_scanned = 0
            file_written = 0
            for table, scanned, written in _iter_gaia_raw_match_tables(
                path,
                g_mag_limit=g_mag_limit,
                batch_rows=batch_rows,
            ):
                file_scanned += scanned
                file_written += written
                if written:
                    writer.write_table(table)
            rows_scanned += file_scanned
            rows_written += file_written
            input_summaries.append(
                GaiaMatchTableInputSummary(
                    path=str(path),
                    bytes=path.stat().st_size,
                    rows_scanned=file_scanned,
                    rows_written=file_written,
                )
            )
    finally:
        if writer is not None:
            writer.close()

    summary = GaiaMatchTableSummary(
        input_paths=[str(Path(path).expanduser()) for path in gaia_votable_paths],
        output_path=str(output_path),
        summary_path=str(summary_path) if summary_path is not None else None,
        source_manifest_path=(
            str(source_manifest_path) if source_manifest_path is not None else None
        ),
        source_checksums_path=(
            str(source_checksums_path) if source_checksums_path is not None else None
        ),
        g_mag_limit=float(g_mag_limit),
        columns=list(GAIA_RAW_MATCH_COLUMNS),
        rows_scanned=int(rows_scanned),
        rows_written=int(rows_written),
        input_files=input_summaries,
        output_bytes=output_path.stat().st_size,
        output_sha256=_sha256_file(output_path),
        created_at=datetime.now(UTC).isoformat(),
    )
    if summary_path is not None:
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(_summary_dict(summary), indent=2) + "\n")
    return summary


def _iter_gaia_raw_match_tables(
    path: Path,
    *,
    g_mag_limit: float,
    batch_rows: int,
):
    with _open_votable(path) as stream:
        fields, first_stream_bytes = _read_fields_to_stream(stream)
        layout = _build_binary2_layout(fields)
        yield from _iter_binary2_gaia_tables(
            stream,
            layout=layout,
            first_stream_bytes=first_stream_bytes,
            g_mag_limit=g_mag_limit,
            batch_rows=batch_rows,
        )


def _open_votable(path: Path) -> BinaryIO:
    if path.name.endswith(".gz"):
        return gzip.open(path, "rb")
    return path.open("rb")


def _read_fields_to_stream(stream: BinaryIO) -> tuple[list[_VOTableField], bytes]:
    fields: list[_VOTableField] = []
    for line in stream:
        fields.extend(_parse_field_tags(line))
        if b"<STREAM" in line:
            return fields, line.split(b">", 1)[1]
    raise ValueError("VOTable does not contain a STREAM element")


def _parse_field_tags(line: bytes) -> list[_VOTableField]:
    out: list[_VOTableField] = []
    for tag_match in _FIELD_TAG_RE.finditer(line):
        attrs = {
            key.decode("ascii").lower(): value.decode("utf-8")
            for key, _, value in _ATTR_RE.findall(tag_match.group(0))
        }
        name = attrs.get("name")
        datatype = attrs.get("datatype")
        if not name or not datatype:
            continue
        out.append(
            _VOTableField(
                name=name,
                datatype=datatype.lower(),
                arraysize=attrs.get("arraysize"),
            )
        )
    return out


def _build_binary2_layout(fields: list[_VOTableField]) -> _Binary2Layout:
    if not fields:
        raise ValueError("VOTable STREAM appears before any FIELD definitions")
    dtype_fields: list[tuple[str, object]] = []
    dtype_names: dict[str, str] = {}
    field_indices: dict[str, int] = {}
    null_mask_bytes = (len(fields) + 7) // 8
    dtype_fields.append(("__null_flags", ("u1", null_mask_bytes)))
    for index, field in enumerate(fields):
        if field.arraysize not in (None, "", "1"):
            raise NotImplementedError(
                f"Unsupported VOTable arraysize for {field.name}: {field.arraysize}"
            )
        dtype_code = _NUMPY_DTYPE_BY_VOTABLE_TYPE.get(field.datatype)
        if dtype_code is None:
            raise NotImplementedError(
                f"Unsupported VOTable datatype for {field.name}: {field.datatype}"
            )
        dtype_name = f"f{index}"
        dtype_fields.append((dtype_name, dtype_code))
        dtype_names[field.name] = dtype_name
        field_indices[field.name] = index

    missing = [col for col in GAIA_RAW_MATCH_COLUMNS if col not in dtype_names]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Gaia VOTable is missing required columns: {joined}")

    dtype = np.dtype(dtype_fields)
    return _Binary2Layout(
        fields=fields,
        dtype=dtype,
        dtype_names=dtype_names,
        field_indices=field_indices,
        null_mask_bytes=null_mask_bytes,
        row_size=dtype.itemsize,
    )


def _iter_binary2_gaia_tables(
    stream: BinaryIO,
    *,
    layout: _Binary2Layout,
    first_stream_bytes: bytes,
    g_mag_limit: float,
    batch_rows: int,
):
    b64_buffer = bytearray()
    binary_buffer = bytearray()
    end_seen = False

    def consume(raw: bytes, *, final: bool) -> bytes:
        nonlocal b64_buffer
        b64_buffer.extend(b"".join(raw.split()))
        valid_len = len(b64_buffer) if final else (len(b64_buffer) // 4) * 4
        if not valid_len:
            return b""
        decoded = base64.b64decode(bytes(b64_buffer[:valid_len]))
        del b64_buffer[:valid_len]
        return decoded

    for chunk in [first_stream_bytes]:
        if b"</STREAM" in chunk:
            chunk = chunk.split(b"</STREAM", 1)[0]
            binary_buffer.extend(consume(chunk, final=True))
            end_seen = True
        else:
            binary_buffer.extend(consume(chunk, final=False))
        yield from _drain_binary_buffer(
            binary_buffer,
            layout=layout,
            g_mag_limit=g_mag_limit,
            batch_rows=batch_rows,
            final=False,
        )

    if not end_seen:
        for line in stream:
            if b"</STREAM" in line:
                binary_buffer.extend(consume(line.split(b"</STREAM", 1)[0], final=True))
                end_seen = True
                break
            binary_buffer.extend(consume(line, final=False))
            yield from _drain_binary_buffer(
                binary_buffer,
                layout=layout,
                g_mag_limit=g_mag_limit,
                batch_rows=batch_rows,
                final=False,
            )

    if not end_seen:
        raise ValueError("VOTable STREAM was not closed")
    if b64_buffer:
        raise ValueError("Trailing incomplete base64 data at end of STREAM")
    yield from _drain_binary_buffer(
        binary_buffer,
        layout=layout,
        g_mag_limit=g_mag_limit,
        batch_rows=batch_rows,
        final=True,
    )
    if binary_buffer:
        raise ValueError("Trailing incomplete BINARY2 row at end of STREAM")


def _drain_binary_buffer(
    binary_buffer: bytearray,
    *,
    layout: _Binary2Layout,
    g_mag_limit: float,
    batch_rows: int,
    final: bool,
):
    target_rows = len(binary_buffer) // layout.row_size if final else batch_rows
    while len(binary_buffer) >= layout.row_size * target_rows and target_rows:
        block_size = layout.row_size * target_rows
        block = bytes(binary_buffer[:block_size])
        del binary_buffer[:block_size]
        table, scanned, written = _binary2_block_to_gaia_table(
            block,
            layout=layout,
            g_mag_limit=g_mag_limit,
        )
        yield table, scanned, written
        if final:
            target_rows = len(binary_buffer) // layout.row_size


def _binary2_block_to_gaia_table(
    block: bytes,
    *,
    layout: _Binary2Layout,
    g_mag_limit: float,
) -> tuple[pa.Table, int, int]:
    rows = np.frombuffer(block, dtype=layout.dtype)
    scanned = len(rows)
    source_null = _null_mask(rows["__null_flags"], layout.field_indices["source_id"])
    source_id = rows[layout.dtype_names["source_id"]].astype(np.uint64, copy=True)
    g_mag = _float_column(rows, layout, "phot_g_mean_mag", np.float32)
    ra = _float_column(rows, layout, "ra", np.float64)
    dec = _float_column(rows, layout, "dec", np.float64)
    selected = (
        ~source_null
        & np.isfinite(ra)
        & np.isfinite(dec)
        & np.isfinite(g_mag)
        & (g_mag <= g_mag_limit)
    )
    if not selected.any():
        return _empty_table(), scanned, 0

    table = pa.Table.from_arrays(
        [
            pa.array(source_id[selected], type=pa.uint64()),
            pa.array(ra[selected], type=pa.float64()),
            pa.array(dec[selected], type=pa.float64()),
            pa.array(g_mag[selected], type=pa.float32()),
            pa.array(
                _float_column(rows, layout, "phot_bp_mean_mag", np.float32)[selected],
                type=pa.float32(),
            ),
            pa.array(
                _float_column(rows, layout, "phot_rp_mean_mag", np.float32)[selected],
                type=pa.float32(),
            ),
            pa.array(
                _float_column(rows, layout, "parallax", np.float64)[selected],
                type=pa.float64(),
            ),
            pa.array(
                _float_column(rows, layout, "parallax_error", np.float32)[selected],
                type=pa.float32(),
            ),
        ],
        schema=GAIA_RAW_MATCH_SCHEMA,
    )
    return table, scanned, int(selected.sum())


def _float_column(
    rows: np.ndarray,
    layout: _Binary2Layout,
    column: str,
    dtype,
) -> np.ndarray:
    values = rows[layout.dtype_names[column]].astype(dtype, copy=True)
    values[_null_mask(rows["__null_flags"], layout.field_indices[column])] = np.nan
    return values


def _null_mask(flags: np.ndarray, field_index: int) -> np.ndarray:
    return (flags[:, field_index // 8] & (1 << (7 - (field_index % 8)))) != 0


def _empty_table() -> pa.Table:
    return pa.Table.from_arrays(
        [
            pa.array([], type=field.type)
            for field in GAIA_RAW_MATCH_SCHEMA
        ],
        schema=GAIA_RAW_MATCH_SCHEMA,
    )


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _summary_dict(summary: GaiaMatchTableSummary) -> dict[str, object]:
    raw = asdict(summary)
    raw["input_files"] = [asdict(item) for item in summary.input_files]
    return raw
