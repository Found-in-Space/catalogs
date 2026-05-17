from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

PUBLICATION_DIR = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = PUBLICATION_DIR / "evidence"

RELEASE = "20260517.1"
GENERATED_AT = "2026-05-17T00:00:00Z"
COHORT_SIZE = 500

COHORT_WEIGHTS = {
    "brightest": 30.0,
    "nearest": 30.0,
    "high_pm": 18.0,
}

QUALITY_FLAG_WEIGHTS = {
    "ruwe_gt_1p4": 10.0,
    "astrometric_excess_noise_gt_1": 8.0,
    "ipd_frac_multi_peak_gt_10": 8.0,
    "duplicated_source": 8.0,
    "non_single_star": 6.0,
    "astrometric_params_not_31_or_95": 6.0,
    "visibility_periods_lt_8": 5.0,
    "missing_bp_or_rp": 5.0,
    "parallax_frac_error_gt_0p1": 5.0,
    "non_positive_parallax": 10.0,
    "phot_variable": 2.0,
    "hip_solution_type_not_5": 10.0,
    "hip_component_flag": 8.0,
}

SCORE_COLUMNS = [
    "priority_rank",
    "priority_score",
    "priority_tier",
    "catalog",
    "source_id",
    "cohorts",
    "cohort_ranks",
    "cohort_count",
    "cohort_score",
    "visibility_score",
    "quality_score",
    "crossmatch_gap_score",
    "priority_reasons",
    "quality_flags",
    "quality_flag_count",
    "has_official_best_neighbour",
    "has_fis_supplemental_match",
    "has_any_gaia_hip_match",
    "official_neighbourhood_ids",
    "counterpart_ids",
    "apparent_mag",
    "r_pc_parallax",
    "pm_total_masyr",
]


def main() -> None:
    scored = score_review_candidates(
        pd.read_parquet(EVIDENCE_DIR / "review_candidates.parquet")
    )
    _write_dataframe(scored, EVIDENCE_DIR / "review_priority_candidates")

    report = {
        "release": RELEASE,
        "generated_at": GENERATED_AT,
        "input_rows": int(len(scored)),
        "scored_rows": int(len(scored)),
        "score_components": {
            "cohort_score": (
                "Rank-weighted membership in the 500 brightest, nearest, and "
                "highest proper-motion cohorts, plus a multi-cohort bonus."
            ),
            "visibility_score": (
                "Additional practical display impact from apparent magnitude, "
                "parallax distance, and total proper motion."
            ),
            "quality_score": (
                "Weighted Gaia and Hipparcos warning flags, capped at 30 points."
            ),
            "crossmatch_gap_score": (
                "Penalty for lacking official/FIS Gaia-HIP overlap, or for "
                "having only neighbourhood/local-supplemental context."
            ),
        },
        "notes": [
            "Scores use only the systematic candidate cohorts and catalog quality/context signals.",
            "Scores prioritize review effort, not astrophysical truth or override decisions.",
        ],
    }
    (EVIDENCE_DIR / "review_priority_report.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )


def score_review_candidates(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["source_id"] = out["source_id"].astype(str)
    out["cohort_rank_map"] = out["cohort_ranks"].map(_parse_cohort_ranks)
    out["cohort_count"] = out["cohorts"].map(_cohort_count)
    out["cohort_score"] = out["cohort_rank_map"].map(_cohort_score)
    out["quality_score"] = out["quality_flags"].map(_quality_score)
    out["apparent_mag"] = out.apply(_apparent_mag, axis=1)
    out["visibility_score"] = out.apply(_visibility_score, axis=1)
    out["has_official_best_neighbour"] = out.apply(_has_official_best_neighbour, axis=1)
    out["has_fis_supplemental_match"] = out["has_fis_supplemental_match"].map(_truthy)
    out["has_any_gaia_hip_match"] = out["has_any_gaia_hip_match"].map(_truthy)
    out["official_neighbourhood_ids"] = out.apply(_official_neighbourhood_ids, axis=1)
    out["counterpart_ids"] = out.apply(_counterpart_ids, axis=1)
    out["crossmatch_gap_score"] = out.apply(_crossmatch_gap_score, axis=1)
    out["priority_score"] = (
        out["cohort_score"]
        + out["visibility_score"]
        + out["quality_score"]
        + out["crossmatch_gap_score"]
    ).round(3)
    out["priority_tier"] = out.apply(_priority_tier, axis=1)
    out["priority_reasons"] = out.apply(_priority_reasons, axis=1)
    out = out.sort_values(
        [
            "priority_score",
            "cohort_score",
            "visibility_score",
            "quality_score",
            "crossmatch_gap_score",
            "catalog",
            "source_id",
        ],
        ascending=[False, False, False, False, False, True, True],
        kind="mergesort",
        ignore_index=True,
    )
    out.insert(0, "priority_rank", np.arange(1, len(out) + 1, dtype=np.int32))
    return out[SCORE_COLUMNS]


def _parse_cohort_ranks(value: Any) -> dict[str, int]:
    if pd.isna(value):
        return {}
    ranks: dict[str, int] = {}
    for part in str(value).split(";"):
        if ":" not in part:
            continue
        name, rank_text = part.split(":", 1)
        try:
            ranks[name.strip()] = int(rank_text)
        except ValueError:
            continue
    return ranks


def _cohort_count(value: Any) -> int:
    if pd.isna(value):
        return 0
    return len([part for part in str(value).split(";") if part])


def _cohort_score(ranks: dict[str, int]) -> float:
    score = 0.0
    for cohort, weight in COHORT_WEIGHTS.items():
        rank = ranks.get(cohort)
        if rank is None:
            continue
        rank_fraction = max(0.0, (COHORT_SIZE + 1 - rank) / COHORT_SIZE)
        score += weight * rank_fraction
    count = len(ranks)
    if count == 2:
        score += 10.0
    elif count >= 3:
        score += 18.0
    return round(score, 3)


def _quality_score(value: Any) -> float:
    score = 0.0
    for flag in _split_flags(value):
        score += QUALITY_FLAG_WEIGHTS.get(flag, 0.0)
    return min(score, 30.0)


def _apparent_mag(row: pd.Series) -> float:
    for col in ("phot_g_mean_mag", "Hpmag"):
        value = row.get(col)
        if _finite(value):
            return float(value)
    return math.nan


def _visibility_score(row: pd.Series) -> float:
    score = 0.0
    mag = row.get("apparent_mag")
    if _finite(mag):
        if mag <= 2.0:
            score += 12.0
        elif mag <= 4.0:
            score += 8.0
        elif mag <= 6.0:
            score += 5.0
        elif mag <= 8.0:
            score += 2.0

    r_pc = row.get("r_pc_parallax")
    if _finite(r_pc):
        if r_pc <= 5.0:
            score += 12.0
        elif r_pc <= 10.0:
            score += 8.0
        elif r_pc <= 20.0:
            score += 4.0

    pm_total = row.get("pm_total_masyr")
    if _finite(pm_total):
        if pm_total >= 3000.0:
            score += 12.0
        elif pm_total >= 2000.0:
            score += 9.0
        elif pm_total >= 1000.0:
            score += 6.0
    return score


def _has_official_best_neighbour(row: pd.Series) -> bool:
    return bool(
        _text(row.get("official_best_hip_ids"))
        or _text(row.get("official_best_gaia_ids"))
    )


def _official_neighbourhood_ids(row: pd.Series) -> str:
    return _join_values(
        row.get("official_neighbourhood_hip_ids"),
        row.get("official_neighbourhood_gaia_ids"),
    )


def _counterpart_ids(row: pd.Series) -> str:
    return _join_values(
        row.get("any_gaia_hip_hip_ids"),
        row.get("any_gaia_hip_gaia_ids"),
    )


def _crossmatch_gap_score(row: pd.Series) -> float:
    score = 0.0
    has_official = bool(row["has_official_best_neighbour"])
    has_fis = bool(row["has_fis_supplemental_match"])
    has_any = bool(row["has_any_gaia_hip_match"])
    has_neighbourhood = bool(_text(row["official_neighbourhood_ids"]))

    if not has_any:
        score += 22.0
    elif has_fis and not has_official:
        score += 6.0

    if has_neighbourhood and not has_official:
        score += 8.0
    return score


def _priority_tier(row: pd.Series) -> str:
    score = float(row["priority_score"])
    no_match = not bool(row["has_any_gaia_hip_match"])
    multi_cohort = int(row["cohort_count"]) >= 2
    quality = float(row["quality_score"])
    if score >= 105.0 or (no_match and multi_cohort and quality >= 15.0):
        return "P1"
    if score >= 80.0 or (no_match and quality >= 10.0):
        return "P2"
    if score >= 55.0:
        return "P3"
    return "P4"


def _priority_reasons(row: pd.Series) -> str:
    reasons: list[str] = []
    ranks = row["cohort_rank_map"]
    if "brightest" in ranks:
        reasons.append(f"brightest_rank={ranks['brightest']}")
    if "nearest" in ranks:
        reasons.append(f"nearest_rank={ranks['nearest']}")
    if "high_pm" in ranks:
        reasons.append(f"high_pm_rank={ranks['high_pm']}")
    if int(row["cohort_count"]) >= 2:
        reasons.append(f"multi_cohort={int(row['cohort_count'])}")
    if not bool(row["has_any_gaia_hip_match"]):
        reasons.append("no_official_or_fis_gaia_hip_match")
    elif bool(row["has_fis_supplemental_match"]) and not bool(
        row["has_official_best_neighbour"]
    ):
        reasons.append("fis_supplemental_only_match")
    if _text(row["official_neighbourhood_ids"]) and not bool(
        row["has_official_best_neighbour"]
    ):
        reasons.append("official_neighbourhood_without_best_match")
    reasons.extend(_split_flags(row.get("quality_flags")))
    return ";".join(reasons)


def _split_flags(value: Any) -> list[str]:
    if pd.isna(value):
        return []
    return [part for part in str(value).split(";") if part]


def _join_values(*values: Any) -> str:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        text = _text(value)
        if not text:
            continue
        for part in text.split(";"):
            if part and part not in seen:
                seen.add(part)
                out.append(part)
    return ";".join(out)


def _text(value: Any) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "<na>"}:
        return ""
    return text


def _truthy(value: Any) -> bool:
    if isinstance(value, bool | np.bool_):
        return bool(value)
    if pd.isna(value):
        return False
    if isinstance(value, int | float):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _write_dataframe(df: pd.DataFrame, stem: Path) -> None:
    stem.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(stem.with_suffix(".csv"), index=False)
    pq.write_table(
        pa.Table.from_pandas(df, preserve_index=False),
        str(stem.with_suffix(".parquet")),
        compression="zstd",
    )


if __name__ == "__main__":
    main()
