"""Raw Gaia/HIP sky-and-magnitude matching for catalog publications."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from astropy.table import Table

from foundinspace.catalogs.audit.pipeline import (
    combine_crossmatches,
    validate_one_to_one_crossmatch,
)
from foundinspace.pipeline.gaia_to_hip.pipeline import (
    GAIA_HIP_MAP_COLS,
    MAPPING_SOURCE_HIPPARCOS2_BEST_NEIGHBOUR,
    empty_gaia_hip_mapping,
    write_gaia_hip_mapping,
)

HIPPARCOS_EPOCH_JYEAR = 1991.25
GAIA_EPOCH_JYEAR = 2016.0
MAS_TO_RAD = np.pi / (180.0 * 3_600_000.0)

RAW_HIP_MATCH_SOURCES_FILENAME = "raw_hip_match_sources.parquet"
RAW_MATCH_EVIDENCE_FILENAME = "raw_match_evidence.parquet"
RAW_SUPPLEMENTAL_MAP_FILENAME = "raw_supplemental_gaia_hip_map.parquet"
RAW_COMBINED_MAP_FILENAME = "raw_combined_gaia_hip_map.parquet"
RAW_MATCH_REPORT_FILENAME = "raw_match_report.json"

RAW_SKY_MAG_MAPPING_SOURCE = "fis_raw_sky_mag_v1"

RAW_MATCH_EVIDENCE_COLS = [
    "gaia_source_id",
    "hip_source_id",
    "decision",
    "recommended_action",
    "severity",
    "reasons",
    "separation_arcsec",
    "apparent_mag_delta",
    "gaia_ra_deg",
    "gaia_dec_deg",
    "hip_ra_deg",
    "hip_dec_deg",
    "hip_ra_deg_epoch1991",
    "hip_dec_deg_epoch1991",
    "gaia_apparent_mag",
    "hip_apparent_mag",
    "gaia_phot_bp_mean_mag",
    "gaia_phot_rp_mean_mag",
    "gaia_bp_rp",
    "hip_plx_mas",
    "hip_e_plx_mas",
    "hip_pmra_masyr",
    "hip_pmdec_masyr",
    "hip_solution_type",
    "gaia_sky_neighbour_count",
    "hip_sky_neighbour_count",
    "gaia_candidate_count",
    "hip_candidate_count",
    "one_to_one_candidate",
    "isolated_sky_pair",
    "official_pair",
    "gaia_has_official_map",
    "hip_has_official_map",
    "official_conflict",
    "gaia_official_hip_source_id",
    "hip_official_gaia_source_id",
]


@dataclass(frozen=True)
class RawMatchReport:
    """JSON summary for a raw sky-and-magnitude Gaia/HIP match scan."""

    hip_ecsv_path: str
    gaia_parquet_path: str
    official_crossmatch_path: str
    output_dir: str
    hip_match_sources_path: str
    match_evidence_path: str
    supplemental_crossmatch_path: str
    combined_crossmatch_path: str
    report_path: str
    max_sep_arcsec: float
    max_mag_delta: float
    gaia_rows_scanned: int
    gaia_rows_skipped: int
    hip_rows_raw: int
    hip_rows_prepared: int
    evidence_rows: int
    supplemental_rows: int
    combined_rows: int
    decision_counts: dict[str, int]
    official_rows: int
    official_pairs_in_evidence: int
    official_pairs_confirmed: int


def run_raw_gaia_hip_match(
    *,
    hip_ecsv_path: Path,
    gaia_parquet_path: Path,
    official_crossmatch_path: Path,
    output_dir: Path,
    max_sep_arcsec: float = 5.0,
    max_mag_delta: float = 0.5,
    batch_size: int = 500_000,
    workers: int = -1,
    force: bool = False,
) -> RawMatchReport:
    """Prepare raw HIP match sources, scan skinny Gaia, and write match artifacts."""

    hip_ecsv_path = Path(hip_ecsv_path).expanduser()
    gaia_parquet_path = Path(gaia_parquet_path).expanduser()
    official_crossmatch_path = Path(official_crossmatch_path).expanduser()
    output_dir = Path(output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    for path in (hip_ecsv_path, gaia_parquet_path, official_crossmatch_path):
        if not path.is_file():
            raise FileNotFoundError(str(path))

    hip_sources_path = output_dir / RAW_HIP_MATCH_SOURCES_FILENAME
    evidence_path = output_dir / RAW_MATCH_EVIDENCE_FILENAME
    supplemental_path = output_dir / RAW_SUPPLEMENTAL_MAP_FILENAME
    combined_path = output_dir / RAW_COMBINED_MAP_FILENAME
    report_path = output_dir / RAW_MATCH_REPORT_FILENAME
    outputs = [
        hip_sources_path,
        evidence_path,
        supplemental_path,
        combined_path,
        report_path,
    ]
    if not force:
        existing = [str(path) for path in outputs if path.exists()]
        if existing:
            joined = ", ".join(existing)
            raise FileExistsError(f"Raw match outputs already exist: {joined}")

    hip_raw_rows = prepare_raw_hip_match_sources(
        hip_ecsv_path=hip_ecsv_path,
        output_path=hip_sources_path,
        overwrite=True,
    )
    official = read_official_crossmatch(official_crossmatch_path)
    evidence, scan_counts = build_raw_match_evidence(
        gaia_parquet_path=gaia_parquet_path,
        hip_sources_path=hip_sources_path,
        official_crossmatch=official,
        max_sep_arcsec=max_sep_arcsec,
        max_mag_delta=max_mag_delta,
        batch_size=batch_size,
        workers=workers,
    )

    _write_dataframe(evidence, evidence_path)
    supplemental = build_raw_supplemental_crossmatch(evidence)
    validate_one_to_one_crossmatch(supplemental, label="raw supplemental")
    write_gaia_hip_mapping(supplemental, supplemental_path)

    combined = combine_crossmatches(official, supplemental)
    validate_one_to_one_crossmatch(combined, label="raw combined")
    write_gaia_hip_mapping(combined, combined_path)

    decision_counts = {
        str(key): int(value)
        for key, value in evidence["decision"].value_counts(dropna=False).items()
    }
    official_pair_mask = evidence["official_pair"].fillna(False).astype(bool)
    report = RawMatchReport(
        hip_ecsv_path=str(hip_ecsv_path),
        gaia_parquet_path=str(gaia_parquet_path),
        official_crossmatch_path=str(official_crossmatch_path),
        output_dir=str(output_dir),
        hip_match_sources_path=str(hip_sources_path),
        match_evidence_path=str(evidence_path),
        supplemental_crossmatch_path=str(supplemental_path),
        combined_crossmatch_path=str(combined_path),
        report_path=str(report_path),
        max_sep_arcsec=max_sep_arcsec,
        max_mag_delta=max_mag_delta,
        gaia_rows_scanned=int(scan_counts["gaia_rows_scanned"]),
        gaia_rows_skipped=int(scan_counts["gaia_rows_skipped"]),
        hip_rows_raw=int(hip_raw_rows),
        hip_rows_prepared=int(pq.ParquetFile(hip_sources_path).metadata.num_rows),
        evidence_rows=int(len(evidence)),
        supplemental_rows=int(len(supplemental)),
        combined_rows=int(len(combined)),
        decision_counts=decision_counts,
        official_rows=int(len(official)),
        official_pairs_in_evidence=int(official_pair_mask.sum()),
        official_pairs_confirmed=int(
            evidence["decision"].astype(str).eq("official_confirmed").sum()
        ),
    )
    report_path.write_text(json.dumps(asdict(report), indent=2) + "\n")
    return report


def prepare_raw_hip_match_sources(
    *,
    hip_ecsv_path: Path,
    output_path: Path,
    overwrite: bool = False,
) -> int:
    """Write minimally normalized HIP rows for raw sky-and-magnitude matching."""

    hip_ecsv_path = Path(hip_ecsv_path).expanduser()
    output_path = Path(output_path).expanduser()
    if output_path.exists() and not overwrite:
        raise FileExistsError(str(output_path))

    table = Table.read(hip_ecsv_path, format="ascii.ecsv")
    raw = table.to_pandas()
    required = {"HIP", "RArad", "DErad", "pmRA", "pmDE", "Hpmag"}
    missing = sorted(required - set(raw.columns))
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Missing required raw Hipparcos columns: {joined}")

    work = pd.DataFrame(
        {
            "source": "hip",
            "source_id": pd.to_numeric(raw["HIP"], errors="coerce"),
            "ra_deg_epoch1991": pd.to_numeric(raw["RArad"], errors="coerce"),
            "dec_deg_epoch1991": pd.to_numeric(raw["DErad"], errors="coerce"),
            "pmra_masyr": pd.to_numeric(raw["pmRA"], errors="coerce"),
            "pmdec_masyr": pd.to_numeric(raw["pmDE"], errors="coerce"),
            "apparent_mag": pd.to_numeric(raw["Hpmag"], errors="coerce"),
            "Hpmag": pd.to_numeric(raw["Hpmag"], errors="coerce"),
        }
    )
    optional_defaults = {
        "Plx": np.nan,
        "e_Plx": np.nan,
        "Sn": np.nan,
    }
    for col, default in optional_defaults.items():
        work[col] = pd.to_numeric(raw[col], errors="coerce") if col in raw else default

    finite = (
        np.isfinite(work["source_id"])
        & np.isfinite(work["ra_deg_epoch1991"])
        & np.isfinite(work["dec_deg_epoch1991"])
        & np.isfinite(work["pmra_masyr"])
        & np.isfinite(work["pmdec_masyr"])
        & np.isfinite(work["apparent_mag"])
    )
    out = work.loc[finite].copy()
    out["source_id"] = out["source_id"].astype("uint64")
    out["ra_deg"], out["dec_deg"] = propagate_hip_sky_to_gaia_epoch(
        out["ra_deg_epoch1991"].to_numpy(dtype=float),
        out["dec_deg_epoch1991"].to_numpy(dtype=float),
        out["pmra_masyr"].to_numpy(dtype=float),
        out["pmdec_masyr"].to_numpy(dtype=float),
    )
    out = out.rename(
        columns={
            "Plx": "plx_mas",
            "e_Plx": "e_plx_mas",
            "Sn": "solution_type",
        }
    )
    out = out[
        [
            "source",
            "source_id",
            "ra_deg",
            "dec_deg",
            "apparent_mag",
            "Hpmag",
            "ra_deg_epoch1991",
            "dec_deg_epoch1991",
            "pmra_masyr",
            "pmdec_masyr",
            "plx_mas",
            "e_plx_mas",
            "solution_type",
        ]
    ].sort_values("source_id", kind="mergesort", ignore_index=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    _write_dataframe(out, output_path)
    return len(raw)


def build_raw_match_evidence(
    *,
    gaia_parquet_path: Path,
    hip_sources_path: Path,
    official_crossmatch: pd.DataFrame,
    max_sep_arcsec: float,
    max_mag_delta: float,
    batch_size: int = 500_000,
    workers: int = -1,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Return Gaia/HIP evidence rows using only sky proximity and apparent mag."""

    ckdtree = _require_ckdtree()
    hip = pq.read_table(hip_sources_path).to_pandas()
    if hip.empty:
        return _empty_raw_match_evidence(), {
            "gaia_rows_scanned": 0,
            "gaia_rows_skipped": 0,
        }
    hip["source_id_str"] = hip["source_id"].astype("uint64").astype(str)

    hip_xyz = _unit_vectors(hip["ra_deg"].to_numpy(), hip["dec_deg"].to_numpy())
    hip_tree = ckdtree(hip_xyz)
    chord_radius = 2.0 * math.sin(math.radians(max_sep_arcsec / 3600.0) / 2.0)
    official_gaia_to_hip = _mapping_dict(official_crossmatch, "gaia_source_id")
    official_hip_to_gaia = _mapping_dict(official_crossmatch, "hip_source_id")

    rows: list[dict[str, Any]] = []
    hip_sky_counts = np.zeros(len(hip), dtype=np.int32)
    gaia_rows_scanned = 0
    gaia_rows_skipped = 0
    parquet = pq.ParquetFile(gaia_parquet_path)
    columns = [
        "source_id",
        "ra",
        "dec",
        "phot_g_mean_mag",
        "phot_bp_mean_mag",
        "phot_rp_mean_mag",
    ]
    for batch in parquet.iter_batches(batch_size=batch_size, columns=columns):
        gaia = batch.to_pandas()
        gaia_rows_scanned += len(gaia)
        numeric_cols = [
            "ra",
            "dec",
            "phot_g_mean_mag",
            "phot_bp_mean_mag",
            "phot_rp_mean_mag",
        ]
        for col in numeric_cols:
            gaia[col] = pd.to_numeric(gaia[col], errors="coerce")
        finite = (
            np.isfinite(gaia["ra"])
            & np.isfinite(gaia["dec"])
            & np.isfinite(gaia["phot_g_mean_mag"])
        )
        gaia_rows_skipped += int((~finite).sum())
        if not finite.any():
            continue
        gaia = gaia.loc[finite].reset_index(drop=True)
        gaia["source_id_str"] = gaia["source_id"].astype("uint64").astype(str)
        gaia_xyz = _unit_vectors(gaia["ra"].to_numpy(), gaia["dec"].to_numpy())
        neighbour_lists = hip_tree.query_ball_point(
            gaia_xyz,
            r=chord_radius,
            workers=workers,
        )
        for gaia_i, hip_indices in enumerate(neighbour_lists):
            if not hip_indices:
                continue
            gaia_rec = gaia.iloc[gaia_i]
            gaia_vec = gaia_xyz[gaia_i]
            hip_idx = np.asarray(hip_indices, dtype=np.int64)
            hip_sky_counts[hip_idx] += 1
            hip_subset = hip.iloc[hip_idx]
            mag_delta = np.abs(
                hip_subset["apparent_mag"].to_numpy(dtype=float)
                - float(gaia_rec["phot_g_mean_mag"])
            )
            keep = mag_delta <= max_mag_delta
            if not keep.any():
                continue
            dots = np.clip(hip_xyz[hip_idx[keep]] @ gaia_vec, -1.0, 1.0)
            sep_arcsec = np.degrees(np.arccos(dots)) * 3600.0
            for seq, local_i in enumerate(np.flatnonzero(keep)):
                hip_rec = hip_subset.iloc[int(local_i)]
                rows.append(
                    _raw_candidate_record(
                        gaia_rec=gaia_rec,
                        hip_rec=hip_rec,
                        sep_arcsec=float(sep_arcsec[seq]),
                        mag_delta=float(mag_delta[local_i]),
                        gaia_sky_count=len(hip_indices),
                        official_gaia_to_hip=official_gaia_to_hip,
                        official_hip_to_gaia=official_hip_to_gaia,
                    )
                )

    if not rows:
        return _empty_raw_match_evidence(), {
            "gaia_rows_scanned": gaia_rows_scanned,
            "gaia_rows_skipped": gaia_rows_skipped,
        }

    evidence = pd.DataFrame(rows, columns=RAW_MATCH_EVIDENCE_COLS)
    hip_counts = pd.Series(
        hip_sky_counts,
        index=hip["source_id_str"].to_numpy(),
        dtype=np.int32,
    )
    evidence["hip_sky_neighbour_count"] = (
        evidence["hip_source_id"].map(hip_counts).fillna(0).astype(np.int32)
    )
    evidence["gaia_candidate_count"] = evidence.groupby("gaia_source_id")[
        "hip_source_id"
    ].transform("nunique")
    evidence["hip_candidate_count"] = evidence.groupby("hip_source_id")[
        "gaia_source_id"
    ].transform("nunique")
    evidence["one_to_one_candidate"] = evidence["gaia_candidate_count"].eq(1) & evidence[
        "hip_candidate_count"
    ].eq(1)
    evidence["isolated_sky_pair"] = evidence["gaia_sky_neighbour_count"].eq(
        1
    ) & evidence["hip_sky_neighbour_count"].eq(1)
    for idx, rec in evidence.iterrows():
        decision, action, severity, reasons = _classify_raw_evidence_row(rec)
        evidence.loc[idx, "decision"] = decision
        evidence.loc[idx, "recommended_action"] = action
        evidence.loc[idx, "severity"] = severity
        evidence.loc[idx, "reasons"] = ";".join(reasons)
    evidence = evidence.sort_values(
        ["decision", "separation_arcsec", "apparent_mag_delta", "gaia_source_id"],
        kind="mergesort",
        ignore_index=True,
    )
    return evidence, {
        "gaia_rows_scanned": gaia_rows_scanned,
        "gaia_rows_skipped": gaia_rows_skipped,
    }


def build_raw_supplemental_crossmatch(evidence: pd.DataFrame) -> pd.DataFrame:
    """Build a supplemental Gaia-HIP map from clean raw sky/mag candidates."""

    if evidence.empty:
        return empty_gaia_hip_mapping()
    matched = evidence.loc[evidence["decision"].eq("supplemental_match")].copy()
    if matched.empty:
        return empty_gaia_hip_mapping()
    out = pd.DataFrame(
        {
            "gaia_source_id": pd.to_numeric(
                matched["gaia_source_id"], errors="raise"
            ).astype("uint64"),
            "hip_source_id": pd.to_numeric(
                matched["hip_source_id"], errors="raise"
            ).astype("uint64"),
            "mapping_source": RAW_SKY_MAG_MAPPING_SOURCE,
            "number_of_neighbours": np.int16(1),
            "angular_distance": pd.to_numeric(
                matched["separation_arcsec"], errors="raise"
            ).astype(np.float32),
        }
    )
    return out[GAIA_HIP_MAP_COLS].sort_values(
        ["gaia_source_id", "hip_source_id"],
        kind="mergesort",
        ignore_index=True,
    )


def read_official_crossmatch(path: Path) -> pd.DataFrame:
    """Read an official Gaia-HIP map from pipeline Parquet or Gaia/Vizier ECSV."""

    path = Path(path).expanduser()
    if path.suffix.lower() == ".parquet":
        df = pq.read_table(path).to_pandas()
    else:
        df = Table.read(path, format="ascii.ecsv").to_pandas()
    df = df.copy()
    df.columns = [str(col).lower() for col in df.columns]
    if {"gaia_source_id", "hip_source_id"}.issubset(df.columns):
        out = pd.DataFrame(
            {
                "gaia_source_id": pd.to_numeric(
                    df["gaia_source_id"], errors="coerce"
                ),
                "hip_source_id": pd.to_numeric(df["hip_source_id"], errors="coerce"),
            }
        )
    elif {"source_id", "original_ext_source_id"}.issubset(df.columns):
        out = pd.DataFrame(
            {
                "gaia_source_id": pd.to_numeric(df["source_id"], errors="coerce"),
                "hip_source_id": pd.to_numeric(
                    df["original_ext_source_id"], errors="coerce"
                ),
            }
        )
    else:
        raise ValueError(
            "Official crossmatch must contain gaia_source_id/hip_source_id or "
            "source_id/original_ext_source_id"
        )
    valid = (
        np.isfinite(out["gaia_source_id"])
        & np.isfinite(out["hip_source_id"])
        & (out["gaia_source_id"] > 0)
        & (out["hip_source_id"] > 0)
    )
    out = out.loc[valid].copy()
    out["gaia_source_id"] = out["gaia_source_id"].astype("uint64")
    out["hip_source_id"] = out["hip_source_id"].astype("uint64")
    if "mapping_source" in df.columns:
        out["mapping_source"] = df.loc[valid, "mapping_source"].astype(str).to_numpy()
    else:
        out["mapping_source"] = MAPPING_SOURCE_HIPPARCOS2_BEST_NEIGHBOUR
    if "number_of_neighbours" in df.columns:
        out["number_of_neighbours"] = (
            pd.to_numeric(df.loc[valid, "number_of_neighbours"], errors="coerce")
            .fillna(0)
            .astype(np.int16)
            .to_numpy()
        )
    else:
        out["number_of_neighbours"] = np.int16(0)
    if "angular_distance" in df.columns:
        out["angular_distance"] = (
            pd.to_numeric(df.loc[valid, "angular_distance"], errors="coerce")
            .astype(np.float32)
            .to_numpy()
        )
    else:
        out["angular_distance"] = np.float32(np.nan)
    return out[GAIA_HIP_MAP_COLS].drop_duplicates(
        ["gaia_source_id", "hip_source_id"], ignore_index=True
    )


def propagate_hip_sky_to_gaia_epoch(
    ra_deg: np.ndarray,
    dec_deg: np.ndarray,
    pmra_masyr: np.ndarray,
    pmdec_masyr: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Propagate HIP angular positions from J1991.25 to J2016.0 on the unit sphere."""

    ra = np.deg2rad(ra_deg.astype(np.float64, copy=False))
    dec = np.deg2rad(dec_deg.astype(np.float64, copy=False))
    mu_a = pmra_masyr.astype(np.float64, copy=False) * MAS_TO_RAD
    mu_d = pmdec_masyr.astype(np.float64, copy=False) * MAS_TO_RAD
    dt = GAIA_EPOCH_JYEAR - HIPPARCOS_EPOCH_JYEAR

    ca = np.cos(ra)
    sa = np.sin(ra)
    cd = np.cos(dec)
    sd = np.sin(dec)

    ux = cd * ca
    uy = cd * sa
    uz = sd

    eax = -sa
    eay = ca
    edx = -ca * sd
    edy = -sa * sd
    edz = cd

    x = ux + dt * (mu_a * eax + mu_d * edx)
    y = uy + dt * (mu_a * eay + mu_d * edy)
    z = uz + dt * (mu_d * edz)

    xy = np.hypot(x, y)
    ra_out = np.degrees(np.mod(np.arctan2(y, x), 2.0 * np.pi))
    dec_out = np.degrees(np.arctan2(z, xy))
    return ra_out, dec_out


def _raw_candidate_record(
    *,
    gaia_rec: pd.Series,
    hip_rec: pd.Series,
    sep_arcsec: float,
    mag_delta: float,
    gaia_sky_count: int,
    official_gaia_to_hip: dict[str, str],
    official_hip_to_gaia: dict[str, str],
) -> dict[str, Any]:
    gaia_id = str(gaia_rec["source_id_str"])
    hip_id = str(hip_rec["source_id_str"])
    gaia_official_hip = official_gaia_to_hip.get(gaia_id)
    hip_official_gaia = official_hip_to_gaia.get(hip_id)
    gaia_has_map = gaia_official_hip is not None
    hip_has_map = hip_official_gaia is not None
    official_pair = gaia_official_hip == hip_id and hip_official_gaia == gaia_id
    official_conflict = (
        (gaia_has_map and gaia_official_hip != hip_id)
        or (hip_has_map and hip_official_gaia != gaia_id)
    )
    bp = _safe_float(gaia_rec.get("phot_bp_mean_mag"))
    rp = _safe_float(gaia_rec.get("phot_rp_mean_mag"))
    bp_rp = bp - rp if math.isfinite(bp) and math.isfinite(rp) else pd.NA
    return {
        "gaia_source_id": gaia_id,
        "hip_source_id": hip_id,
        "decision": "",
        "recommended_action": "",
        "severity": "",
        "reasons": "",
        "separation_arcsec": sep_arcsec,
        "apparent_mag_delta": mag_delta,
        "gaia_ra_deg": _safe_float(gaia_rec["ra"]),
        "gaia_dec_deg": _safe_float(gaia_rec["dec"]),
        "hip_ra_deg": _safe_float(hip_rec["ra_deg"]),
        "hip_dec_deg": _safe_float(hip_rec["dec_deg"]),
        "hip_ra_deg_epoch1991": _safe_float(hip_rec["ra_deg_epoch1991"]),
        "hip_dec_deg_epoch1991": _safe_float(hip_rec["dec_deg_epoch1991"]),
        "gaia_apparent_mag": _safe_float(gaia_rec["phot_g_mean_mag"]),
        "hip_apparent_mag": _safe_float(hip_rec["apparent_mag"]),
        "gaia_phot_bp_mean_mag": bp if math.isfinite(bp) else pd.NA,
        "gaia_phot_rp_mean_mag": rp if math.isfinite(rp) else pd.NA,
        "gaia_bp_rp": bp_rp,
        "hip_plx_mas": _safe_float(hip_rec.get("plx_mas")),
        "hip_e_plx_mas": _safe_float(hip_rec.get("e_plx_mas")),
        "hip_pmra_masyr": _safe_float(hip_rec.get("pmra_masyr")),
        "hip_pmdec_masyr": _safe_float(hip_rec.get("pmdec_masyr")),
        "hip_solution_type": _safe_float(hip_rec.get("solution_type")),
        "gaia_sky_neighbour_count": int(gaia_sky_count),
        "hip_sky_neighbour_count": 0,
        "gaia_candidate_count": 1,
        "hip_candidate_count": 1,
        "one_to_one_candidate": True,
        "isolated_sky_pair": False,
        "official_pair": bool(official_pair),
        "gaia_has_official_map": bool(gaia_has_map),
        "hip_has_official_map": bool(hip_has_map),
        "official_conflict": bool(official_conflict),
        "gaia_official_hip_source_id": gaia_official_hip or pd.NA,
        "hip_official_gaia_source_id": hip_official_gaia or pd.NA,
    }


def _classify_raw_evidence_row(rec: pd.Series) -> tuple[str, str, str, list[str]]:
    reasons = ["close_sky_position", "close_apparent_magnitude"]
    if bool(rec["isolated_sky_pair"]):
        reasons.append("isolated_within_scan_radius")
    elif bool(rec["one_to_one_candidate"]):
        reasons.append("one_to_one_candidate_but_not_sky_isolated")

    if bool(rec["official_pair"]):
        reasons.append("official_crossmatch_pair")
        if bool(rec["one_to_one_candidate"]):
            return (
                "official_confirmed",
                "already_in_official_crossmatch",
                "info",
                reasons,
            )
        reasons.append("official_pair_has_local_ambiguity")
        return "manual_review", "inspect_ambiguous_official_pair", "medium", reasons

    if bool(rec["official_conflict"]):
        reasons.append("official_crossmatch_conflict")
        return "manual_review", "inspect_official_conflict", "high", reasons

    if not bool(rec["one_to_one_candidate"]):
        reasons.append("ambiguous_candidate_field")
        return "manual_review", "inspect_ambiguous_raw_match", "medium", reasons

    reasons.append("clean_raw_sky_mag_candidate")
    return "supplemental_match", "add_supplemental_crossmatch", "medium", reasons


def _mapping_dict(mapping: pd.DataFrame, key_col: str) -> dict[str, str]:
    value_col = "hip_source_id" if key_col == "gaia_source_id" else "gaia_source_id"
    return {
        str(int(getattr(rec, key_col))): str(int(getattr(rec, value_col)))
        for rec in mapping[[key_col, value_col]].itertuples(index=False)
    }


def _unit_vectors(ra_deg: np.ndarray, dec_deg: np.ndarray) -> np.ndarray:
    ra = np.deg2rad(ra_deg.astype(np.float64, copy=False))
    dec = np.deg2rad(dec_deg.astype(np.float64, copy=False))
    cos_dec = np.cos(dec)
    return np.column_stack(
        (
            cos_dec * np.cos(ra),
            cos_dec * np.sin(ra),
            np.sin(dec),
        )
    )


def _safe_float(value: Any) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return out


def _write_dataframe(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(table, str(path), compression="zstd")


def _empty_raw_match_evidence() -> pd.DataFrame:
    return pd.DataFrame(columns=RAW_MATCH_EVIDENCE_COLS)


def _require_ckdtree():
    try:
        from scipy.spatial import cKDTree
    except ImportError as exc:
        raise RuntimeError(
            "Raw Gaia/HIP matching requires the optional audit dependency group. "
            "Run with `uv run --group audit ...`."
        ) from exc
    return cKDTree
