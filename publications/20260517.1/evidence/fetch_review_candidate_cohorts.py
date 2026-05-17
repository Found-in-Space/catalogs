from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from astroquery.gaia import Gaia
from astroquery.vizier import Vizier

PUBLICATION_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = PUBLICATION_DIR.parents[1]
EVIDENCE_DIR = PUBLICATION_DIR / "evidence"
ADQL_DIR = EVIDENCE_DIR / "adql"
LOCAL_WORK_DIR = REPO_DIR / "local/runs/20260517.1/review-candidates/working"
FIS_SUPPLEMENTAL_MAP_PATH = (
    PUBLICATION_DIR.parent
    / "20260515.1/catalog/fis_gaia_hip_supplemental_display_map.parquet"
)

RELEASE = "20260517.1"
GENERATED_AT = "2026-05-17T00:00:00Z"
COHORT_SIZE = 500
CROSSMATCH_CHUNK_SIZE = 350

GAIA_FIELDS = [
    "source_id",
    "ra",
    "dec",
    "ref_epoch",
    "parallax",
    "parallax_error",
    "pmra",
    "pmra_error",
    "pmdec",
    "pmdec_error",
    "ruwe",
    "astrometric_params_solved",
    "non_single_star",
    "duplicated_source",
    "visibility_periods_used",
    "astrometric_excess_noise",
    "astrometric_sigma5d_max",
    "ipd_frac_multi_peak",
    "ipd_frac_odd_win",
    "phot_g_mean_mag",
    "phot_g_mean_flux_over_error",
    "phot_bp_mean_mag",
    "phot_bp_mean_flux_over_error",
    "phot_rp_mean_mag",
    "phot_rp_mean_flux_over_error",
    "phot_bp_rp_excess_factor",
    "bp_rp",
    "phot_variable_flag",
    "teff_gspphot",
]

GAIA_COHORTS = {
    "brightest": {
        "filename": "gaia_review_brightest_500",
        "where": "g.phot_g_mean_mag IS NOT NULL",
        "order_by": "g.phot_g_mean_mag ASC",
        "rank_metric": "phot_g_mean_mag",
    },
    "nearest": {
        "filename": "gaia_review_nearest_500",
        "where": "g.parallax IS NOT NULL AND g.parallax > 0",
        "order_by": "g.parallax DESC",
        "rank_metric": "parallax",
    },
    "high_pm": {
        "filename": "gaia_review_high_pm_500",
        "where": "g.pmra IS NOT NULL AND g.pmdec IS NOT NULL",
        "extra_select": "SQRT(g.pmra * g.pmra + g.pmdec * g.pmdec) AS pm_total_query",
        "order_by": "pm_total_query DESC",
        "rank_metric": "pm_total_masyr",
    },
}

HIP_COHORTS = {
    "brightest": {
        "filename": "hipparcos2_review_brightest_500",
        "rank_metric": "Hpmag",
        "ascending": True,
    },
    "nearest": {
        "filename": "hipparcos2_review_nearest_500",
        "rank_metric": "Plx",
        "ascending": False,
    },
    "high_pm": {
        "filename": "hipparcos2_review_high_pm_500",
        "rank_metric": "pm_total_masyr",
        "ascending": False,
    },
}


def main() -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    ADQL_DIR.mkdir(parents=True, exist_ok=True)
    LOCAL_WORK_DIR.mkdir(parents=True, exist_ok=True)
    _login_gaia_if_configured()

    gaia_cohort_frames = []
    for cohort, spec in GAIA_COHORTS.items():
        query = _gaia_cohort_query(
            spec["where"],
            spec["order_by"],
            extra_select=spec.get("extra_select"),
        )
        (ADQL_DIR / f"{spec['filename']}.adql").write_text(
            query + "\n",
            encoding="utf-8",
        )
        df = _gaia_query(query)
        df = _with_gaia_quality_columns(df)
        df.insert(0, "catalog", "gaia_dr3")
        df.insert(1, "cohort", cohort)
        df.insert(2, "cohort_rank", np.arange(1, len(df) + 1, dtype=np.int32))
        _write_dataframe(df, EVIDENCE_DIR / spec["filename"])
        gaia_cohort_frames.append(df)

    hip_raw = _fetch_hipparcos2()
    hip_raw = _with_hip_quality_columns(hip_raw)
    _write_dataframe(hip_raw, LOCAL_WORK_DIR / "hipparcos2_review_source_rows")
    hip_cohort_frames = []
    for cohort, spec in HIP_COHORTS.items():
        metric = spec["rank_metric"]
        work = hip_raw.loc[np.isfinite(pd.to_numeric(hip_raw[metric], errors="coerce"))]
        if cohort == "nearest":
            work = work.loc[pd.to_numeric(work["Plx"], errors="coerce") > 0]
        df = (
            work.sort_values(metric, ascending=bool(spec["ascending"]), kind="mergesort")
            .head(COHORT_SIZE)
            .copy()
            .reset_index(drop=True)
        )
        df.insert(0, "catalog", "hipparcos2")
        df.insert(1, "cohort", cohort)
        df.insert(2, "cohort_rank", np.arange(1, len(df) + 1, dtype=np.int32))
        _write_dataframe(df, EVIDENCE_DIR / spec["filename"])
        hip_cohort_frames.append(df)

    gaia_candidates = _aggregate_gaia_candidates(pd.concat(gaia_cohort_frames))
    hip_candidates = _aggregate_hip_candidates(pd.concat(hip_cohort_frames))

    best_neighbour = _fetch_crossmatch_lookup(
        table="gaiadr3.hipparcos2_best_neighbour",
        fields=[
            "source_id",
            "original_ext_source_id",
            "angular_distance",
            "number_of_neighbours",
            "xm_flag",
        ],
        gaia_ids=_id_list(gaia_candidates, "source_id"),
        hip_ids=_id_list(hip_candidates, "HIP"),
        output_stem="gaia_hip_review_best_neighbour_lookup",
    )
    fis_supplemental = _load_fis_supplemental_lookup(
        FIS_SUPPLEMENTAL_MAP_PATH,
        gaia_ids=_id_list(gaia_candidates, "source_id"),
        hip_ids=_id_list(hip_candidates, "HIP"),
    )
    _write_dataframe(
        fis_supplemental,
        EVIDENCE_DIR / "fis_20260515_1_review_supplemental_lookup",
    )
    neighbourhood = _fetch_crossmatch_lookup(
        table="gaiadr3.hipparcos2_neighbourhood",
        fields=[
            "source_id",
            "original_ext_source_id",
            "angular_distance",
            "score",
            "xm_flag",
        ],
        gaia_ids=_id_list(gaia_candidates, "source_id"),
        hip_ids=_id_list(hip_candidates, "HIP"),
        output_stem="gaia_hip_review_neighbourhood_lookup",
    )

    gaia_candidates = _annotate_gaia_crossmatch(gaia_candidates, best_neighbour)
    hip_candidates = _annotate_hip_crossmatch(hip_candidates, best_neighbour)
    gaia_candidates = _annotate_gaia_supplemental(gaia_candidates, fis_supplemental)
    hip_candidates = _annotate_hip_supplemental(hip_candidates, fis_supplemental)
    gaia_candidates = _annotate_crossmatch_neighbourhood(
        gaia_candidates,
        neighbourhood,
        key_col="source_id",
        match_key_col="source_id",
        value_col="original_ext_source_id",
        out_col="official_neighbourhood_hip_ids",
    )
    hip_candidates = _annotate_crossmatch_neighbourhood(
        hip_candidates,
        neighbourhood,
        key_col="HIP",
        match_key_col="original_ext_source_id",
        value_col="source_id",
        out_col="official_neighbourhood_gaia_ids",
    )

    _write_dataframe(gaia_candidates, EVIDENCE_DIR / "gaia_review_candidates")
    _write_dataframe(hip_candidates, EVIDENCE_DIR / "hipparcos2_review_candidates")

    combined = pd.concat(
        [
            _combined_candidate_view(gaia_candidates, "gaia_dr3", "source_id"),
            _combined_candidate_view(hip_candidates, "hipparcos2", "HIP"),
        ],
        ignore_index=True,
    )
    _write_dataframe(combined, EVIDENCE_DIR / "review_candidates")

    report = {
        "release": RELEASE,
        "generated_at": GENERATED_AT,
        "purpose": (
            "Objective first-pass review candidates for future Gaia/Hipparcos "
            "astrometry and photometry inspection."
        ),
        "cohort_size": COHORT_SIZE,
        "cohorts": ["brightest", "nearest", "high_pm"],
        "gaia_rows_by_cohort": {
            cohort: int(len(df)) for cohort, df in zip(GAIA_COHORTS, gaia_cohort_frames)
        },
        "hipparcos2_rows_by_cohort": {
            cohort: int(len(df)) for cohort, df in zip(HIP_COHORTS, hip_cohort_frames)
        },
        "unique_gaia_candidates": int(len(gaia_candidates)),
        "unique_hipparcos2_candidates": int(len(hip_candidates)),
        "hipparcos2_source_rows_fetched": int(len(hip_raw)),
        "combined_candidate_rows": int(len(combined)),
        "best_neighbour_rows": int(len(best_neighbour)),
        "fis_supplemental_rows": int(len(fis_supplemental)),
        "official_candidate_candidate_pairs": int(
            _candidate_pair_count(
                best_neighbour,
                gaia_ids=_id_list(gaia_candidates, "source_id"),
                hip_ids=_id_list(hip_candidates, "HIP"),
            )
        ),
        "fis_supplemental_candidate_candidate_pairs": int(
            _candidate_pair_count(
                fis_supplemental,
                gaia_ids=_id_list(gaia_candidates, "source_id"),
                hip_ids=_id_list(hip_candidates, "HIP"),
            )
        ),
        "combined_candidate_candidate_pairs": int(
            _candidate_pair_count(
                pd.concat(
                    [
                        _normalized_pair_frame(best_neighbour),
                        _normalized_pair_frame(fis_supplemental),
                    ],
                    ignore_index=True,
                ).drop_duplicates(),
                gaia_ids=_id_list(gaia_candidates, "source_id"),
                hip_ids=_id_list(hip_candidates, "HIP"),
            )
        ),
        "neighbourhood_rows": int(len(neighbourhood)),
        "quality_flag_counts": _quality_flag_counts(combined),
        "local_working_outputs": {
            "hipparcos2_review_source_rows": str(
                LOCAL_WORK_DIR / "hipparcos2_review_source_rows.parquet"
            ),
            "hipparcos2_review_source_rows_count": int(len(hip_raw)),
        },
        "notes": [
            "Rows are review candidates only; they are not override decisions.",
            "Cohorts are selected from Gaia DR3 and Hipparcos-2 by apparent brightness, parallax, and total proper motion.",
            "The 20260515.1 Found-In-Space supplemental Gaia-HIP display map is included as crossmatch context alongside the official Gaia best-neighbour table.",
            "Quality flags are intentionally broad signals for later inspection against source catalogs and literature.",
            "Full source working copies are written under local/ and are not publication artifacts.",
        ],
    }
    (EVIDENCE_DIR / "review_candidate_report.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )


def _login_gaia_if_configured() -> None:
    credentials_file = os.environ.get("GAIA_CREDENTIALS_FILE")
    if credentials_file:
        Gaia.login(credentials_file=credentials_file)
        return
    user = os.environ.get("GAIA_USER")
    password = os.environ.get("GAIA_PASS")
    if user and password:
        Gaia.login(user=user, password=password)


def _gaia_cohort_query(
    where: str,
    order_by: str,
    *,
    extra_select: str | None = None,
) -> str:
    selected_fields = [f"g.{field}" for field in GAIA_FIELDS]
    if extra_select is not None:
        selected_fields.append(extra_select)
    fields = ",\n  ".join(selected_fields)
    return f"""SELECT TOP {COHORT_SIZE}
  {fields}
FROM gaiadr3.gaia_source AS g
WHERE {where}
ORDER BY {order_by}"""


def _gaia_query(query: str) -> pd.DataFrame:
    job = Gaia.launch_job_async(query)
    return _normalize_dataframe(job.get_results().to_pandas())


def _fetch_hipparcos2() -> pd.DataFrame:
    v = Vizier(columns=["*"], row_limit=-1)
    tables = v.get_catalogs("I/311/hip2")
    if not tables:
        raise RuntimeError("VizieR returned no I/311/hip2 table")
    return _normalize_dataframe(tables[0].to_pandas())


def _fetch_crossmatch_lookup(
    *,
    table: str,
    fields: list[str],
    gaia_ids: list[int],
    hip_ids: list[int],
    output_stem: str,
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for index, chunk in enumerate(_chunks(gaia_ids, CROSSMATCH_CHUNK_SIZE), start=1):
        query = _crossmatch_query(table, fields, "source_id", chunk)
        (ADQL_DIR / f"{output_stem}_gaia_{index:03d}.adql").write_text(
            query + "\n",
            encoding="utf-8",
        )
        frames.append(_gaia_query(query))
    for index, chunk in enumerate(_chunks(hip_ids, CROSSMATCH_CHUNK_SIZE), start=1):
        query = _crossmatch_query(table, fields, "original_ext_source_id", chunk)
        (ADQL_DIR / f"{output_stem}_hip_{index:03d}.adql").write_text(
            query + "\n",
            encoding="utf-8",
        )
        frames.append(_gaia_query(query))
    if not frames:
        out = pd.DataFrame(columns=fields)
    else:
        out = pd.concat(frames, ignore_index=True)
        out = out.drop_duplicates(ignore_index=True)
    _write_dataframe(out, EVIDENCE_DIR / output_stem)
    return out


def _load_fis_supplemental_lookup(
    path: Path,
    *,
    gaia_ids: list[int],
    hip_ids: list[int],
) -> pd.DataFrame:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(str(path))
    raw = pd.read_parquet(path)
    work = _normalized_pair_frame(raw)
    gaia_set = set(gaia_ids)
    hip_set = set(hip_ids)
    out = work.loc[work["gaia_source_id"].isin(gaia_set) | work["hip_source_id"].isin(hip_set)]
    return out.sort_values(
        ["gaia_source_id", "hip_source_id"],
        kind="mergesort",
        ignore_index=True,
    )


def _crossmatch_query(
    table: str,
    fields: list[str],
    key_col: str,
    ids: list[int],
) -> str:
    selected = ",\n  ".join(fields)
    return f"""SELECT
  {selected}
FROM {table}
WHERE {key_col} IN ({_comma_ints(ids)})"""


def _with_gaia_quality_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in GAIA_FIELDS:
        if col not in out:
            out[col] = pd.NA
    _numeric(out, [c for c in GAIA_FIELDS if c not in {"source_id", "phot_variable_flag"}])
    out["source_id"] = pd.to_numeric(out["source_id"], errors="raise").astype("uint64")
    out["pm_total_masyr"] = np.hypot(out["pmra"], out["pmdec"])
    out["r_pc_parallax"] = _distance_from_parallax(out["parallax"])
    out["parallax_frac_error"] = _fraction(out["parallax_error"], out["parallax"])
    out["quality_flags"] = out.apply(_gaia_quality_flags, axis=1)
    out["quality_flag_count"] = out["quality_flags"].map(_flag_count)
    return out


def _with_hip_quality_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    _numeric(out, ["HIP", "Plx", "e_Plx", "pmRA", "pmDE", "Hpmag", "Sn", "B-V"])
    out["HIP"] = pd.to_numeric(out["HIP"], errors="raise").astype("uint64")
    out["pm_total_masyr"] = np.hypot(out["pmRA"], out["pmDE"])
    out["r_pc_parallax"] = _distance_from_parallax(out["Plx"])
    out["parallax_frac_error"] = _fraction(out["e_Plx"], out["Plx"])
    out["quality_flags"] = out.apply(_hip_quality_flags, axis=1)
    out["quality_flag_count"] = out["quality_flags"].map(_flag_count)
    return out


def _aggregate_gaia_candidates(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["source_id", "cohort_rank"], kind="mergesort")
    base = df.drop_duplicates("source_id", keep="first").copy()
    cohorts = df.groupby("source_id")["cohort"].apply(_join_unique).rename("cohorts")
    ranks = (
        df.assign(cohort_rank_text=df["cohort"] + ":" + df["cohort_rank"].astype(str))
        .groupby("source_id")["cohort_rank_text"]
        .apply(_join_unique)
        .rename("cohort_ranks")
    )
    out = base.drop(columns=["catalog", "cohort", "cohort_rank"]).merge(
        cohorts,
        on="source_id",
    )
    out = out.merge(ranks, on="source_id")
    out.insert(0, "catalog", "gaia_dr3")
    return out.sort_values(["quality_flag_count", "source_id"], ascending=[False, True])


def _aggregate_hip_candidates(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["HIP", "cohort_rank"], kind="mergesort")
    base = df.drop_duplicates("HIP", keep="first").copy()
    cohorts = df.groupby("HIP")["cohort"].apply(_join_unique).rename("cohorts")
    ranks = (
        df.assign(cohort_rank_text=df["cohort"] + ":" + df["cohort_rank"].astype(str))
        .groupby("HIP")["cohort_rank_text"]
        .apply(_join_unique)
        .rename("cohort_ranks")
    )
    out = base.drop(columns=["catalog", "cohort", "cohort_rank"]).merge(cohorts, on="HIP")
    out = out.merge(ranks, on="HIP")
    out.insert(0, "catalog", "hipparcos2")
    return out.sort_values(["quality_flag_count", "HIP"], ascending=[False, True])


def _annotate_gaia_crossmatch(
    candidates: pd.DataFrame,
    best_neighbour: pd.DataFrame,
) -> pd.DataFrame:
    mapping = _group_values(best_neighbour, "source_id", "original_ext_source_id")
    out = candidates.copy()
    out["official_best_hip_ids"] = out["source_id"].map(
        lambda value: ";".join(mapping.get(str(int(value)), []))
    )
    out["has_official_best_neighbour"] = out["official_best_hip_ids"].astype(bool)
    return out


def _annotate_gaia_supplemental(
    candidates: pd.DataFrame,
    supplemental: pd.DataFrame,
) -> pd.DataFrame:
    mapping = _group_values(supplemental, "gaia_source_id", "hip_source_id")
    out = candidates.copy()
    out["fis_supplemental_hip_ids"] = out["source_id"].map(
        lambda value: ";".join(mapping.get(str(int(value)), []))
    )
    out["has_fis_supplemental_match"] = out["fis_supplemental_hip_ids"].astype(bool)
    out["any_gaia_hip_hip_ids"] = out.apply(
        lambda row: _join_semicolon_ids(
            row.get("official_best_hip_ids", ""),
            row.get("fis_supplemental_hip_ids", ""),
        ),
        axis=1,
    )
    out["has_any_gaia_hip_match"] = out["any_gaia_hip_hip_ids"].astype(bool)
    return out


def _annotate_hip_crossmatch(
    candidates: pd.DataFrame,
    best_neighbour: pd.DataFrame,
) -> pd.DataFrame:
    mapping = _group_values(best_neighbour, "original_ext_source_id", "source_id")
    out = candidates.copy()
    out["official_best_gaia_ids"] = out["HIP"].map(
        lambda value: ";".join(mapping.get(str(int(value)), []))
    )
    out["has_official_best_neighbour"] = out["official_best_gaia_ids"].astype(bool)
    return out


def _annotate_hip_supplemental(
    candidates: pd.DataFrame,
    supplemental: pd.DataFrame,
) -> pd.DataFrame:
    mapping = _group_values(supplemental, "hip_source_id", "gaia_source_id")
    out = candidates.copy()
    out["fis_supplemental_gaia_ids"] = out["HIP"].map(
        lambda value: ";".join(mapping.get(str(int(value)), []))
    )
    out["has_fis_supplemental_match"] = out["fis_supplemental_gaia_ids"].astype(bool)
    out["any_gaia_hip_gaia_ids"] = out.apply(
        lambda row: _join_semicolon_ids(
            row.get("official_best_gaia_ids", ""),
            row.get("fis_supplemental_gaia_ids", ""),
        ),
        axis=1,
    )
    out["has_any_gaia_hip_match"] = out["any_gaia_hip_gaia_ids"].astype(bool)
    return out


def _annotate_crossmatch_neighbourhood(
    candidates: pd.DataFrame,
    neighbourhood: pd.DataFrame,
    *,
    key_col: str,
    match_key_col: str,
    value_col: str,
    out_col: str,
) -> pd.DataFrame:
    mapping = _group_values(neighbourhood, match_key_col, value_col)
    out = candidates.copy()
    out[out_col] = out[key_col].map(lambda value: ";".join(mapping.get(str(int(value)), [])))
    return out


def _combined_candidate_view(
    candidates: pd.DataFrame,
    catalog: str,
    id_col: str,
) -> pd.DataFrame:
    fields = [
        "catalog",
        id_col,
        "cohorts",
        "cohort_ranks",
        "quality_flags",
        "quality_flag_count",
        "pm_total_masyr",
        "r_pc_parallax",
        "parallax_frac_error",
    ]
    optional = [
        "phot_g_mean_mag",
        "Hpmag",
        "ruwe",
        "duplicated_source",
        "non_single_star",
        "Sn",
        "n_HIP",
        "official_best_hip_ids",
        "official_best_gaia_ids",
        "fis_supplemental_hip_ids",
        "fis_supplemental_gaia_ids",
        "any_gaia_hip_hip_ids",
        "any_gaia_hip_gaia_ids",
        "has_fis_supplemental_match",
        "has_any_gaia_hip_match",
        "official_neighbourhood_hip_ids",
        "official_neighbourhood_gaia_ids",
    ]
    present = [col for col in fields + optional if col in candidates]
    out = candidates[present].copy()
    out = out.rename(columns={id_col: "source_id"})
    out["source_id"] = out["source_id"].map(lambda value: str(int(value)))
    out["catalog"] = catalog
    return out


def _gaia_quality_flags(row: pd.Series) -> str:
    flags: list[str] = []
    if _finite(row.get("ruwe")) and row["ruwe"] > 1.4:
        flags.append("ruwe_gt_1p4")
    if _finite(row.get("parallax_frac_error")) and row["parallax_frac_error"] > 0.1:
        flags.append("parallax_frac_error_gt_0p1")
    if _finite(row.get("parallax")) and row["parallax"] <= 0:
        flags.append("non_positive_parallax")
    if _finite(row.get("astrometric_params_solved")) and int(row["astrometric_params_solved"]) not in {
        31,
        95,
    }:
        flags.append("astrometric_params_not_31_or_95")
    if _finite(row.get("visibility_periods_used")) and row["visibility_periods_used"] < 8:
        flags.append("visibility_periods_lt_8")
    if _finite(row.get("astrometric_excess_noise")) and row["astrometric_excess_noise"] > 1.0:
        flags.append("astrometric_excess_noise_gt_1")
    if _finite(row.get("ipd_frac_multi_peak")) and row["ipd_frac_multi_peak"] > 10:
        flags.append("ipd_frac_multi_peak_gt_10")
    if bool(row.get("duplicated_source")):
        flags.append("duplicated_source")
    if _finite(row.get("non_single_star")) and int(row["non_single_star"]) != 0:
        flags.append("non_single_star")
    if pd.isna(row.get("phot_bp_mean_mag")) or pd.isna(row.get("phot_rp_mean_mag")):
        flags.append("missing_bp_or_rp")
    if str(row.get("phot_variable_flag", "")).upper() not in {"", "NOT_AVAILABLE", "NAN"}:
        flags.append("phot_variable")
    return ";".join(flags)


def _hip_quality_flags(row: pd.Series) -> str:
    flags: list[str] = []
    if _finite(row.get("parallax_frac_error")) and row["parallax_frac_error"] > 0.1:
        flags.append("parallax_frac_error_gt_0p1")
    if _finite(row.get("Plx")) and row["Plx"] <= 0:
        flags.append("non_positive_parallax")
    if _finite(row.get("Sn")) and int(row["Sn"]) != 5:
        flags.append("hip_solution_type_not_5")
    if pd.notna(row.get("n_HIP")) and str(row.get("n_HIP")).strip():
        flags.append("hip_component_flag")
    return ";".join(flags)


def _quality_flag_counts(df: pd.DataFrame) -> dict[str, int]:
    counts: dict[str, int] = {}
    if "quality_flags" not in df:
        return counts
    for raw in df["quality_flags"].fillna("").astype(str):
        for flag in raw.split(";"):
            if flag:
                counts[flag] = counts.get(flag, 0) + 1
    return dict(sorted(counts.items()))


def _candidate_pair_count(
    df: pd.DataFrame,
    *,
    gaia_ids: list[int],
    hip_ids: list[int],
) -> int:
    if df.empty:
        return 0
    pairs = _normalized_pair_frame(df)
    gaia_set = set(gaia_ids)
    hip_set = set(hip_ids)
    return int(
        (
            pairs["gaia_source_id"].isin(gaia_set)
            & pairs["hip_source_id"].isin(hip_set)
        ).sum()
    )


def _normalized_pair_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            {
                "gaia_source_id": pd.Series(dtype="uint64"),
                "hip_source_id": pd.Series(dtype="uint64"),
            }
        )
    if {"gaia_source_id", "hip_source_id"}.issubset(df.columns):
        out = pd.DataFrame(
            {
                "gaia_source_id": pd.to_numeric(
                    df["gaia_source_id"],
                    errors="raise",
                ).astype("uint64"),
                "hip_source_id": pd.to_numeric(
                    df["hip_source_id"],
                    errors="raise",
                ).astype("uint64"),
            }
        )
    else:
        out = pd.DataFrame(
            {
                "gaia_source_id": pd.to_numeric(
                    df["source_id"],
                    errors="raise",
                ).astype("uint64"),
                "hip_source_id": pd.to_numeric(
                    df["original_ext_source_id"],
                    errors="raise",
                ).astype("uint64"),
            }
        )
    if "mapping_source" in df:
        out["mapping_source"] = df["mapping_source"].astype(str).to_numpy()
    elif "xm_flag" in df:
        out["mapping_source"] = "hipparcos2_best_neighbour"
    else:
        out["mapping_source"] = "unknown"
    if "angular_distance" in df:
        out["angular_distance"] = pd.to_numeric(
            df["angular_distance"],
            errors="coerce",
        ).to_numpy()
    return out.drop_duplicates(
        ["gaia_source_id", "hip_source_id"],
        ignore_index=True,
    )


def _write_dataframe(df: pd.DataFrame, stem: Path) -> None:
    stem.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(stem.with_suffix(".csv"), index=False)
    pq.write_table(
        pa.Table.from_pandas(df, preserve_index=False),
        str(stem.with_suffix(".parquet")),
        compression="zstd",
    )


def _normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        dtype = str(out[col].dtype)
        if dtype == "object" or dtype.startswith("str"):
            out[col] = out[col].map(_decode_if_bytes)
    return out


def _decode_if_bytes(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _numeric(df: pd.DataFrame, cols: list[str]) -> None:
    for col in cols:
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce")


def _distance_from_parallax(parallax_mas: pd.Series) -> pd.Series:
    parallax = pd.to_numeric(parallax_mas, errors="coerce")
    return pd.Series(np.where(parallax > 0, 1000.0 / parallax, np.nan), index=parallax.index)


def _fraction(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    num = pd.to_numeric(numerator, errors="coerce").abs()
    den = pd.to_numeric(denominator, errors="coerce").abs()
    return pd.Series(np.where(den > 0, num / den, np.nan), index=den.index)


def _finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _flag_count(flags: str) -> int:
    if not flags:
        return 0
    return len([flag for flag in str(flags).split(";") if flag])


def _join_unique(values: pd.Series) -> str:
    return ";".join(dict.fromkeys(str(value) for value in values if pd.notna(value)))


def _join_semicolon_ids(*values: Any) -> str:
    out: list[str] = []
    for value in values:
        if pd.isna(value):
            continue
        for part in str(value).split(";"):
            clean = part.strip()
            if clean and clean not in out:
                out.append(clean)
    return ";".join(out)


def _group_values(df: pd.DataFrame, key_col: str, value_col: str) -> dict[str, list[str]]:
    if df.empty:
        return {}
    out: dict[str, list[str]] = {}
    for rec in df[[key_col, value_col]].itertuples(index=False):
        key_raw = getattr(rec, key_col)
        value_raw = getattr(rec, value_col)
        if pd.isna(key_raw) or pd.isna(value_raw):
            continue
        out.setdefault(str(int(key_raw)), []).append(str(int(value_raw)))
    return {key: sorted(set(values), key=int) for key, values in out.items()}


def _id_list(df: pd.DataFrame, col: str) -> list[int]:
    return sorted({int(value) for value in df[col] if pd.notna(value)})


def _chunks(values: list[int], size: int) -> list[list[int]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def _comma_ints(values: list[int]) -> str:
    return ", ".join(str(int(value)) for value in values)


if __name__ == "__main__":
    main()
