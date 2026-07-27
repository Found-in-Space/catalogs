"""Audit helpers for Gaia/HIP pairing evidence and review reports."""

from __future__ import annotations

import json
import math
import shutil
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from foundinspace.pipeline.gaia_to_hip.pipeline import (
    GAIA_HIP_MAP_COLS,
    MAPPING_SOURCE_HIPPARCOS2_BEST_NEIGHBOUR,
    empty_gaia_hip_mapping,
)
from foundinspace.pipeline.merge import shards
from foundinspace.pipeline.merge.quality_report import (
    ISSUES_FILENAME,
    run_quality_report,
)

MATCH_EVIDENCE_FILENAME = "pairing_evidence.parquet"
MATCH_REPORT_FILENAME = "pairing_report.json"
LEGACY_MATCH_OUTPUT_FILENAMES = (
    "match_evidence.parquet",
    "supplemental_gaia_hip_map.parquet",
    "combined_gaia_hip_map.parquet",
    "audit_match_report.json",
)
OCTREE_REVIEW_FILENAME = "octree_review.parquet"
MANUAL_CANDIDATES_FILENAME = "manual_override_candidates.parquet"
MANUAL_CANDIDATES_CSV_FILENAME = "manual_override_candidates.csv"
AUDIT_REPORT_FILENAME = "audit_report.json"
DISTANCE_HISTOGRAM_PNG_FILENAME = "distance_pct_histogram.png"
DISTANCE_HISTOGRAM_SVG_FILENAME = "distance_pct_histogram.svg"
DISTANCE_HISTOGRAM_BINS_FILENAME = "distance_pct_histogram_bins.csv"
DISTANCE_THRESHOLD_SUMMARY_FILENAME = "distance_threshold_summary.csv"
DISTANCE_THRESHOLD_SUMMARY_JSON_FILENAME = "distance_threshold_summary.json"
DISTANCE_QUALITY_PLOT_PNG_FILENAME = "distance_pct_vs_astrometry_quality.png"
DISTANCE_QUALITY_PLOT_SVG_FILENAME = "distance_pct_vs_astrometry_quality.svg"
DISTANCE_QUALITY_SUMMARY_FILENAME = "distance_quality_summary.csv"

BATCH_SIZE = 250_000
DISTANCE_HISTOGRAM_BINS = [
    0,
    1,
    2,
    3,
    4,
    5,
    7.5,
    10,
    12.5,
    15,
    20,
    25,
    30,
    40,
    50,
    75,
    100,
]

MATCH_EVIDENCE_COLS = [
    "gaia_source_id",
    "hip_source_id",
    "h2bn_pair",
    "local_scan_pair",
    "separation_arcsec",
    "gaia_ra_deg",
    "gaia_dec_deg",
    "hip_ra_deg",
    "hip_dec_deg",
    "gaia_g_mag",
    "hip_hp_mag",
    "gaia_g_minus_hip_hp_mag",
    "abs_gaia_g_minus_hip_hp_mag",
    "gaia_r_pc",
    "hip_r_pc",
    "radial_gap_pc",
    "combined_distance_sigma_pc",
    "radial_gap_sigma",
    "parallax_3d_separation_pc",
    "gaia_plx_mas",
    "gaia_e_plx_mas",
    "hip_plx_mas",
    "hip_e_plx_mas",
    "gaia_astrometry_quality",
    "hip_astrometry_quality",
    "gaia_photometry_quality",
    "hip_photometry_quality",
    "gaia_ruwe",
    "gaia_phot_g_mean_mag",
    "hip_solution_type",
    "hip_hpmag",
    "gaia_has_h2bn_map",
    "hip_has_h2bn_map",
    "h2bn_conflict",
    "gaia_h2bn_hip_source_id",
    "hip_h2bn_gaia_source_id",
    "h2bn_number_of_neighbours",
    "h2bn_angular_distance",
    "gaia_candidate_count",
    "hip_candidate_count",
    "one_to_one_candidate",
]

OCTREE_REVIEW_COLS = [
    "source",
    "source_id",
    "issue_type",
    "severity",
    "display_action",
    "linked_source",
    "linked_source_id",
    "reasons",
    "ra_deg",
    "dec_deg",
    "r_pc",
    "mag_abs",
    "separation_arcsec",
    "apparent_mag_delta",
]

MANUAL_CANDIDATE_COLS = [
    "issue_type",
    "severity",
    "recommended_action",
    "reasons",
    "source",
    "source_id",
    "gaia_source_id",
    "hip_source_id",
    "label",
    "separation_arcsec",
    "apparent_mag_delta",
    "distance_ratio",
    "distance_frac_diff",
    "gaia_r_pc",
    "hip_r_pc",
    "gaia_mag_abs",
    "hip_mag_abs",
    "merged_r_pc",
    "merged_mag_abs",
    "astrometry_quality",
    "gaia_score",
    "hip_score",
    "gaia_ruwe",
    "hip_solution_type",
]


@dataclass
class AuditMatchReport:
    """JSON summary for the staged policy-neutral pairing audit."""

    gaia_dir: str
    hip_path: str
    h2bn_crossmatch_path: str
    audit_dir: str
    pairing_evidence_path: str
    report_path: str
    max_sep_arcsec: float
    pairing_rows: int
    local_scan_rows: int
    h2bn_rows: int
    h2bn_local_overlap_rows: int
    h2bn_only_rows: int
    local_only_rows: int
    rows_missing_gaia_measurements: int
    rows_missing_hip_measurements: int
    rows_missing_gaia_distance: int
    rows_missing_hip_distance: int
    rows_missing_distance_pair: int
    context_counts: dict[str, int]
    radial_gap_bins: dict[str, int]
    abs_apparent_mag_difference_bins: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AuditReport:
    """JSON summary for post-merge audit review artifacts."""

    merge_dir: str
    audit_dir: str
    octree_review_path: str
    manual_candidates_path: str
    manual_candidates_csv_path: str
    octree_review_rows: int
    octree_review_sharded_rows: int
    manual_candidate_rows: int
    manual_counts_by_type: dict[str, int]
    octree_counts_by_action: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_audit_dir(merge_dir: Path) -> Path:
    return Path(merge_dir).expanduser() / "audit"


def run_audit_match(
    *,
    gaia_dir: Path,
    hip_path: Path,
    h2bn_crossmatch_path: Path,
    audit_dir: Path,
    max_sep_arcsec: float = 5.0,
    force: bool = False,
) -> AuditMatchReport:
    """Write the union of H2BN and staged local-scan pairing evidence."""
    gaia_dir = Path(gaia_dir).expanduser()
    hip_path = Path(hip_path).expanduser()
    h2bn_crossmatch_path = Path(h2bn_crossmatch_path).expanduser()
    audit_dir = Path(audit_dir).expanduser()

    if not gaia_dir.is_dir():
        raise FileNotFoundError(str(gaia_dir))
    for path in (hip_path, h2bn_crossmatch_path):
        if not path.is_file():
            raise FileNotFoundError(str(path))

    _prepare_output_dir(audit_dir, force=force)
    for filename in LEGACY_MATCH_OUTPUT_FILENAMES:
        legacy_path = audit_dir / filename
        if legacy_path.exists():
            legacy_path.unlink()

    evidence_path = audit_dir / MATCH_EVIDENCE_FILENAME
    report_path = audit_dir / MATCH_REPORT_FILENAME

    h2bn = _read_crossmatch(h2bn_crossmatch_path)
    evidence = build_match_evidence(
        gaia_dir=gaia_dir,
        hip_path=hip_path,
        h2bn_crossmatch=h2bn,
        max_sep_arcsec=max_sep_arcsec,
    )
    _write_parquet(evidence, evidence_path)

    h2bn_mask = evidence["h2bn_pair"].fillna(False).astype(bool)
    local_mask = evidence["local_scan_pair"].fillna(False).astype(bool)
    report = AuditMatchReport(
        gaia_dir=str(gaia_dir),
        hip_path=str(hip_path),
        h2bn_crossmatch_path=str(h2bn_crossmatch_path),
        audit_dir=str(audit_dir),
        pairing_evidence_path=str(evidence_path),
        report_path=str(report_path),
        max_sep_arcsec=max_sep_arcsec,
        pairing_rows=int(len(evidence)),
        local_scan_rows=int(local_mask.sum()),
        h2bn_rows=int(h2bn_mask.sum()),
        h2bn_local_overlap_rows=int((h2bn_mask & local_mask).sum()),
        h2bn_only_rows=int((h2bn_mask & ~local_mask).sum()),
        local_only_rows=int((~h2bn_mask & local_mask).sum()),
        rows_missing_gaia_measurements=int(evidence["gaia_g_mag"].isna().sum()),
        rows_missing_hip_measurements=int(evidence["hip_hp_mag"].isna().sum()),
        rows_missing_gaia_distance=int(evidence["gaia_r_pc"].isna().sum()),
        rows_missing_hip_distance=int(evidence["hip_r_pc"].isna().sum()),
        rows_missing_distance_pair=int(
            (evidence["gaia_r_pc"].isna() | evidence["hip_r_pc"].isna()).sum()
        ),
        context_counts=_staged_pairing_context_counts(evidence),
        radial_gap_bins=_descriptive_bins(
            evidence["radial_gap_pc"],
            edges=(1.0, 3.0, 5.0, 10.0),
            labels=("le_1_pc", "1_to_3_pc", "3_to_5_pc", "5_to_10_pc", "gt_10_pc"),
        ),
        abs_apparent_mag_difference_bins=_descriptive_bins(
            evidence["abs_gaia_g_minus_hip_hp_mag"],
            edges=(0.5, 1.0, 2.0),
            labels=("le_0_5_mag", "0_5_to_1_mag", "1_to_2_mag", "gt_2_mag"),
        ),
    )
    _write_json(report.to_dict(), report_path)
    return report


def build_match_evidence(
    *,
    gaia_dir: Path,
    hip_path: Path,
    h2bn_crossmatch: pd.DataFrame,
    max_sep_arcsec: float,
) -> pd.DataFrame:
    """Return the union of H2BN and staged local-scan pairing evidence."""
    ckdtree = _require_ckdtree()
    gaia = _load_processed_candidates(sorted(Path(gaia_dir).glob("*.parquet")), "gaia")
    hip = _load_processed_candidates([Path(hip_path)], "hip")
    gaia_by_id = {str(rec["source_id"]): rec for _, rec in gaia.iterrows()}
    hip_by_id = {str(rec["source_id"]): rec for _, rec in hip.iterrows()}
    h2bn_gaia_to_hip = _mapping_dict(h2bn_crossmatch, "gaia_source_id")
    h2bn_hip_to_gaia = _mapping_dict(h2bn_crossmatch, "hip_source_id")
    h2bn_pairs = {
        (str(int(rec.gaia_source_id)), str(int(rec.hip_source_id)))
        for rec in h2bn_crossmatch.itertuples(index=False)
    }
    h2bn_metadata = {
        (str(int(rec.gaia_source_id)), str(int(rec.hip_source_id))): (
            int(rec.number_of_neighbours),
            _safe_float(rec.angular_distance),
        )
        for rec in h2bn_crossmatch.itertuples(index=False)
    }

    rows: list[dict[str, Any]] = []
    scannable_gaia = gaia.loc[
        np.isfinite(gaia["ra_deg"]) & np.isfinite(gaia["dec_deg"])
    ].reset_index(drop=True)
    scannable_hip = hip.loc[
        np.isfinite(hip["ra_deg"]) & np.isfinite(hip["dec_deg"])
    ].reset_index(drop=True)
    if not scannable_gaia.empty and not scannable_hip.empty:
        gaia_xyz = _unit_vectors(scannable_gaia["ra_deg"], scannable_gaia["dec_deg"])
        hip_xyz = _unit_vectors(scannable_hip["ra_deg"], scannable_hip["dec_deg"])
        chord_radius = 2.0 * math.sin(
            math.radians(max_sep_arcsec / 3600.0) / 2.0
        )
        neighbour_lists = ckdtree(gaia_xyz).query_ball_tree(
            ckdtree(hip_xyz),
            r=chord_radius,
        )
        for gaia_i, hip_indices in enumerate(neighbour_lists):
            if not hip_indices:
                continue
            gaia_rec = scannable_gaia.iloc[gaia_i]
            gaia_vec = gaia_xyz[gaia_i]
            hip_subset = scannable_hip.iloc[hip_indices]
            dots = np.clip(hip_xyz[hip_indices] @ gaia_vec, -1.0, 1.0)
            separations = np.degrees(np.arccos(dots)) * 3600.0
            for local_i, separation in enumerate(separations):
                rows.append(
                    _candidate_record(
                        gaia_rec=gaia_rec,
                        hip_rec=hip_subset.iloc[int(local_i)],
                        sep_arcsec=float(separation),
                        local_scan_pair=True,
                        h2bn_gaia_to_hip=h2bn_gaia_to_hip,
                        h2bn_hip_to_gaia=h2bn_hip_to_gaia,
                        h2bn_pairs=h2bn_pairs,
                        h2bn_metadata=h2bn_metadata,
                    )
                )

    evidence = pd.DataFrame(rows, columns=MATCH_EVIDENCE_COLS)
    if not evidence.empty:
        evidence["gaia_candidate_count"] = evidence.groupby("gaia_source_id")[
            "hip_source_id"
        ].transform("nunique")
        evidence["hip_candidate_count"] = evidence.groupby("hip_source_id")[
            "gaia_source_id"
        ].transform("nunique")
        evidence["one_to_one_candidate"] = evidence["gaia_candidate_count"].eq(
            1
        ) & evidence["hip_candidate_count"].eq(1)

    local_pairs = {
        (str(int(rec.gaia_source_id)), str(int(rec.hip_source_id)))
        for rec in evidence.itertuples(index=False)
    }
    h2bn_only_rows = [
        _candidate_record(
            gaia_rec=gaia_by_id.get(gaia_id),
            hip_rec=hip_by_id.get(hip_id),
            gaia_source_id=gaia_id,
            hip_source_id=hip_id,
            sep_arcsec=_processed_angular_separation_arcsec(
                gaia_by_id.get(gaia_id), hip_by_id.get(hip_id)
            ),
            local_scan_pair=False,
            h2bn_gaia_to_hip=h2bn_gaia_to_hip,
            h2bn_hip_to_gaia=h2bn_hip_to_gaia,
            h2bn_pairs=h2bn_pairs,
            h2bn_metadata=h2bn_metadata,
        )
        for gaia_id, hip_id in sorted(h2bn_pairs - local_pairs)
    ]
    if h2bn_only_rows:
        evidence = pd.concat(
            [evidence, pd.DataFrame(h2bn_only_rows, columns=MATCH_EVIDENCE_COLS)],
            ignore_index=True,
        )
    if evidence.empty:
        return _empty_match_evidence()
    evidence["gaia_source_id"] = _parse_uint_series(
        evidence["gaia_source_id"]
    ).astype("uint64")
    evidence["hip_source_id"] = _parse_uint_series(
        evidence["hip_source_id"]
    ).astype("uint64")
    return evidence.sort_values(
        ["gaia_source_id", "hip_source_id"],
        kind="mergesort",
        ignore_index=True,
    )


def write_distance_threshold_diagnostics(
    evidence: pd.DataFrame,
    *,
    audit_dir: Path,
    auto_distance_frac_diff: float,
) -> dict[str, str | None]:
    """Write threshold-summary tables and a distance-disagreement histogram."""
    audit_dir = Path(audit_dir)
    work = _distance_diagnostics_frame(evidence)
    clean = work.loc[
        (~work["official_conflict"].astype(bool))
        & (~work["overridden"].astype(bool))
        & work["one_to_one"].astype(bool)
        & np.isfinite(work["distance_frac_diff"])
    ].copy()
    finite = work.loc[np.isfinite(work["distance_frac_diff"])].copy()

    tight = clean["within_auto_thresholds"].astype(bool)
    old_distance_policy = tight | clean["distance_frac_diff"].le(
        auto_distance_frac_diff
    )
    pct25 = tight | clean["distance_frac_diff"].le(0.25)
    broad_scan = pd.Series(True, index=clean.index, dtype=bool)

    summary = pd.DataFrame(
        [
            {
                "policy": "tight sky/mag only",
                "matched_clean_count": int(tight.sum()),
                "delta_vs_broad_scan_policy": int(tight.sum() - broad_scan.sum()),
                "non_tight_added": 0,
            },
            {
                "policy": f"tight or distance <= {auto_distance_frac_diff:.0%}",
                "matched_clean_count": int(old_distance_policy.sum()),
                "delta_vs_broad_scan_policy": int(
                    old_distance_policy.sum() - broad_scan.sum()
                ),
                "non_tight_added": int(
                    (
                        ~tight
                        & clean["distance_frac_diff"].le(auto_distance_frac_diff)
                    ).sum()
                ),
            },
            {
                "policy": "tight or distance <= 25%",
                "matched_clean_count": int(pct25.sum()),
                "delta_vs_broad_scan_policy": int(pct25.sum() - broad_scan.sum()),
                "non_tight_added": int(
                    (~tight & clean["distance_frac_diff"].le(0.25)).sum()
                ),
            },
            {
                "policy": "broad clean one-to-one",
                "matched_clean_count": int(broad_scan.sum()),
                "delta_vs_broad_scan_policy": 0,
                "non_tight_added": int((~tight).sum()),
            },
        ]
    )
    summary_path = audit_dir / DISTANCE_THRESHOLD_SUMMARY_FILENAME
    summary.to_csv(summary_path, index=False)

    histogram = _distance_histogram_bins(finite, clean)
    histogram_path = audit_dir / DISTANCE_HISTOGRAM_BINS_FILENAME
    histogram.to_csv(histogram_path, index=False)

    quality_summary = _distance_quality_summary(clean)
    quality_summary_path = audit_dir / DISTANCE_QUALITY_SUMMARY_FILENAME
    quality_summary.to_csv(quality_summary_path, index=False)

    summary_json_path = audit_dir / DISTANCE_THRESHOLD_SUMMARY_JSON_FILENAME
    _write_json(
        {
            "rows": {
                "all_finite_distance_candidates": int(len(finite)),
                "clean_auto_eligible_candidates": int(len(clean)),
            },
            "policy_counts_clean_eligible": summary.to_dict(orient="records"),
            "selected_policy": "broad clean one-to-one",
            "distance_used_as_veto": False,
            "quantiles_clean_pct_diff": _quantiles(
                clean["distance_frac_diff"] * 100.0
            ),
            "quantiles_clean_3d_sep_pc": _quantiles(clean["separation_3d_pc"]),
        },
        summary_json_path,
    )

    png_path: Path | None = None
    svg_path: Path | None = None
    quality_png_path: Path | None = None
    quality_svg_path: Path | None = None
    if not finite.empty or not clean.empty:
        candidate_png_path = audit_dir / DISTANCE_HISTOGRAM_PNG_FILENAME
        candidate_svg_path = audit_dir / DISTANCE_HISTOGRAM_SVG_FILENAME
        wrote_plot = _write_distance_histogram_plot(
            finite=finite,
            clean=clean,
            summary=summary,
            auto_distance_frac_diff=auto_distance_frac_diff,
            png_path=candidate_png_path,
            svg_path=candidate_svg_path,
        )
        if wrote_plot:
            png_path = candidate_png_path
            svg_path = candidate_svg_path
        candidate_quality_png_path = audit_dir / DISTANCE_QUALITY_PLOT_PNG_FILENAME
        candidate_quality_svg_path = audit_dir / DISTANCE_QUALITY_PLOT_SVG_FILENAME
        wrote_quality_plot = _write_distance_quality_plot(
            clean=clean,
            quality_summary=quality_summary,
            auto_distance_frac_diff=auto_distance_frac_diff,
            png_path=candidate_quality_png_path,
            svg_path=candidate_quality_svg_path,
        )
        if wrote_quality_plot:
            quality_png_path = candidate_quality_png_path
            quality_svg_path = candidate_quality_svg_path

    return {
        "png_path": str(png_path) if png_path is not None else None,
        "svg_path": str(svg_path) if svg_path is not None else None,
        "histogram_bins_path": str(histogram_path),
        "summary_path": str(summary_path),
        "summary_json_path": str(summary_json_path),
        "quality_png_path": str(quality_png_path)
        if quality_png_path is not None
        else None,
        "quality_svg_path": str(quality_svg_path)
        if quality_svg_path is not None
        else None,
        "quality_summary_path": str(quality_summary_path),
    }


def run_audit_report(
    *,
    gaia_dir: Path,
    hip_path: Path,
    official_crossmatch_path: Path,
    overrides_path: Path,
    identifiers_path: Path | None,
    merge_dir: Path,
    sidecar_output_dir: Path,
    healpix_order: int,
    audit_dir: Path,
    force: bool = False,
) -> AuditReport:
    """Write octree and manual-review audit reports after a merge."""
    merge_dir = Path(merge_dir).expanduser()
    sidecar_output_dir = Path(sidecar_output_dir).expanduser()
    audit_dir = Path(audit_dir).expanduser()
    evidence_path = audit_dir / MATCH_EVIDENCE_FILENAME
    if not evidence_path.is_file():
        raise FileNotFoundError(str(evidence_path))
    if not (merge_dir / "healpix").is_dir():
        raise FileNotFoundError(str(merge_dir / "healpix"))

    _prepare_report_outputs(audit_dir, sidecar_output_dir, force=force)

    evidence = pd.read_parquet(evidence_path)
    run_quality_report(
        gaia_dir=gaia_dir,
        hip_path=hip_path,
        crossmatch_path=official_crossmatch_path,
        overrides_path=overrides_path,
        merge_dir=merge_dir,
        identifiers_path=identifiers_path,
        output_dir=audit_dir,
        force=force,
    )
    quality_issues = pd.read_parquet(audit_dir / ISSUES_FILENAME)

    octree_review = build_octree_review(evidence, quality_issues)
    octree_path = audit_dir / OCTREE_REVIEW_FILENAME
    _write_parquet(octree_review, octree_path)
    sharded_rows = write_octree_review_sidecar(
        octree_review,
        sidecar_output_dir=sidecar_output_dir,
        healpix_order=healpix_order,
    )

    manual_candidates = build_manual_override_candidates(evidence, quality_issues)
    manual_path = audit_dir / MANUAL_CANDIDATES_FILENAME
    manual_csv_path = audit_dir / MANUAL_CANDIDATES_CSV_FILENAME
    _write_parquet(manual_candidates, manual_path)
    manual_candidates.to_csv(manual_csv_path, index=False)

    report = AuditReport(
        merge_dir=str(merge_dir),
        audit_dir=str(audit_dir),
        octree_review_path=str(octree_path),
        manual_candidates_path=str(manual_path),
        manual_candidates_csv_path=str(manual_csv_path),
        octree_review_rows=int(len(octree_review)),
        octree_review_sharded_rows=int(sharded_rows),
        manual_candidate_rows=int(len(manual_candidates)),
        manual_counts_by_type=_value_counts(manual_candidates, "issue_type"),
        octree_counts_by_action=_value_counts(octree_review, "display_action"),
    )
    _write_json(report.to_dict(), audit_dir / AUDIT_REPORT_FILENAME)
    return report


def build_octree_review(
    evidence: pd.DataFrame,
    quality_issues: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if not evidence.empty and "decision" in evidence.columns:
        for rec in evidence.loc[
            evidence["decision"].astype(str).eq("octree_review")
        ].itertuples(index=False):
            rows.append(
                _octree_record(
                    source="hip",
                    source_id=rec.hip_source_id,
                    issue_type="close_cross_catalog_pair",
                    severity=rec.severity,
                    display_action="suppress_candidate_duplicate",
                    linked_source="gaia",
                    linked_source_id=rec.gaia_source_id,
                    reasons=rec.reasons,
                    ra_deg=rec.hip_ra_deg,
                    dec_deg=rec.hip_dec_deg,
                    r_pc=rec.hip_r_pc,
                    mag_abs=rec.hip_mag_abs,
                    separation_arcsec=rec.separation_arcsec,
                    apparent_mag_delta=rec.apparent_mag_delta,
                )
            )
    if not quality_issues.empty:
        for rec in quality_issues.loc[
            quality_issues["issue_type"].astype(str).eq("merged_row_extreme")
        ].itertuples(index=False):
            rows.append(
                _octree_record(
                    source=rec.source,
                    source_id=rec.source_id,
                    issue_type="merged_row_extreme",
                    severity=rec.severity,
                    display_action="quarantine_suspicious_star",
                    linked_source=pd.NA,
                    linked_source_id=pd.NA,
                    reasons=rec.reasons,
                    ra_deg=getattr(rec, "merged_ra_deg", pd.NA),
                    dec_deg=getattr(rec, "merged_dec_deg", pd.NA),
                    r_pc=rec.merged_r_pc,
                    mag_abs=rec.merged_mag_abs,
                    separation_arcsec=pd.NA,
                    apparent_mag_delta=pd.NA,
                )
            )
    return pd.DataFrame(rows, columns=OCTREE_REVIEW_COLS)


def build_manual_override_candidates(
    evidence: pd.DataFrame,
    quality_issues: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if not evidence.empty and "decision" in evidence.columns:
        manual = evidence.loc[evidence["decision"].astype(str).eq("manual_review")]
        for rec in manual.itertuples(index=False):
            rows.append(
                _manual_record(
                    issue_type="close_pair_manual_review",
                    severity=rec.severity,
                    recommended_action=rec.recommended_action,
                    reasons=rec.reasons,
                    source="hip",
                    source_id=rec.hip_source_id,
                    gaia_source_id=rec.gaia_source_id,
                    hip_source_id=rec.hip_source_id,
                    separation_arcsec=rec.separation_arcsec,
                    apparent_mag_delta=rec.apparent_mag_delta,
                    distance_ratio=rec.distance_ratio,
                    distance_frac_diff=rec.distance_frac_diff,
                    gaia_r_pc=rec.gaia_r_pc,
                    hip_r_pc=rec.hip_r_pc,
                    gaia_mag_abs=rec.gaia_mag_abs,
                    hip_mag_abs=rec.hip_mag_abs,
                    gaia_score=rec.gaia_astrometry_quality,
                    hip_score=rec.hip_astrometry_quality,
                    gaia_ruwe=rec.gaia_ruwe,
                    hip_solution_type=rec.hip_solution_type,
                )
            )
    if not quality_issues.empty:
        review_types = {"matched_pair_conflict", "merged_row_extreme"}
        quality_review = quality_issues.loc[
            quality_issues["issue_type"].astype(str).isin(review_types)
        ]
        for rec in quality_review.itertuples(index=False):
            rows.append(
                _manual_record(
                    issue_type=rec.issue_type,
                    severity=rec.severity,
                    recommended_action="create_or_review_override",
                    reasons=rec.reasons,
                    source=rec.source,
                    source_id=rec.source_id,
                    gaia_source_id=rec.gaia_source_id,
                    hip_source_id=rec.hip_source_id,
                    label=getattr(rec, "label", pd.NA),
                    separation_arcsec=getattr(rec, "angular_distance_arcsec", pd.NA),
                    apparent_mag_delta=getattr(rec, "apparent_mag_delta", pd.NA),
                    distance_ratio=getattr(rec, "distance_ratio", pd.NA),
                    distance_frac_diff=getattr(rec, "distance_frac_diff", pd.NA),
                    gaia_r_pc=getattr(rec, "gaia_r_pc", pd.NA),
                    hip_r_pc=getattr(rec, "hip_r_pc", pd.NA),
                    gaia_mag_abs=getattr(rec, "gaia_mag_abs", pd.NA),
                    hip_mag_abs=getattr(rec, "hip_mag_abs", pd.NA),
                    merged_r_pc=getattr(rec, "merged_r_pc", pd.NA),
                    merged_mag_abs=getattr(rec, "merged_mag_abs", pd.NA),
                    astrometry_quality=getattr(rec, "astrometry_quality", pd.NA),
                    gaia_score=getattr(rec, "gaia_score", pd.NA),
                    hip_score=getattr(rec, "hip_score", pd.NA),
                    gaia_ruwe=getattr(rec, "gaia_ruwe", pd.NA),
                    hip_solution_type=getattr(rec, "hip_solution_type", pd.NA),
                )
            )
    if not rows:
        return pd.DataFrame(columns=MANUAL_CANDIDATE_COLS)
    return pd.DataFrame(rows, columns=MANUAL_CANDIDATE_COLS).sort_values(
        ["severity", "issue_type", "source", "source_id"],
        ascending=[True, True, True, True],
        kind="mergesort",
        ignore_index=True,
    )


def write_octree_review_sidecar(
    octree_review: pd.DataFrame,
    *,
    sidecar_output_dir: Path,
    healpix_order: int,
) -> int:
    if octree_review.empty:
        return 0
    hp = shards._build_healpix(healpix_order)
    work = octree_review.copy()
    work["_shard_ra_deg"] = pd.to_numeric(work["ra_deg"], errors="coerce")
    work["_shard_dec_deg"] = pd.to_numeric(work["dec_deg"], errors="coerce")
    work = work.loc[
        np.isfinite(work["_shard_ra_deg"]) & np.isfinite(work["_shard_dec_deg"])
    ]
    return shards._write_sidecar_shards(
        work,
        hp=hp,
        sidecar_root=Path(sidecar_output_dir),
        sidecar_name="octree_review",
        phase_tag="audit",
        output_cols=OCTREE_REVIEW_COLS,
        seq_by_key={},
    )


def _distance_diagnostics_frame(evidence: pd.DataFrame) -> pd.DataFrame:
    work = evidence.copy()
    for col in [
        "distance_frac_diff",
        "gaia_r_pc",
        "hip_r_pc",
        "separation_arcsec",
        "gaia_astrometry_quality",
        "hip_astrometry_quality",
    ]:
        if col not in work:
            work[col] = np.nan
        work[col] = pd.to_numeric(work[col], errors="coerce")
    for col in [
        "official_conflict",
        "overridden",
        "one_to_one",
        "within_auto_thresholds",
    ]:
        if col not in work:
            work[col] = False
        work[col] = work[col].fillna(False).astype(bool)

    work["distance_pct_diff"] = work["distance_frac_diff"] * 100.0
    work["distance_abs_diff_pc"] = (work["gaia_r_pc"] - work["hip_r_pc"]).abs()
    work["worst_astrometry_quality"] = work[
        ["gaia_astrometry_quality", "hip_astrometry_quality"]
    ].max(axis=1)
    work["best_astrometry_quality"] = work[
        ["gaia_astrometry_quality", "hip_astrometry_quality"]
    ].min(axis=1)
    work["astrometry_quality_ratio"] = (
        work["worst_astrometry_quality"] / work["best_astrometry_quality"]
    )
    theta = np.deg2rad(work["separation_arcsec"] / 3600.0)
    work["separation_3d_pc"] = np.sqrt(
        np.maximum(
            0.0,
            work["gaia_r_pc"] ** 2
            + work["hip_r_pc"] ** 2
            - 2.0 * work["gaia_r_pc"] * work["hip_r_pc"] * np.cos(theta),
        )
    )
    return work


def _distance_quality_summary(clean: pd.DataFrame) -> pd.DataFrame:
    bins = [0, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, np.inf]
    rows = []
    for start, end in zip(bins[:-1], bins[1:], strict=True):
        if np.isinf(end):
            mask = clean["worst_astrometry_quality"].ge(start)
            label = f">={start:g}"
        else:
            mask = clean["worst_astrometry_quality"].ge(start) & clean[
                "worst_astrometry_quality"
            ].lt(end)
            label = f"{start:g}-{end:g}"
        subset = clean.loc[mask]
        rows.append(
            {
                "worst_quality_bin": label,
                "rows": int(len(subset)),
                "distance_pct_le_10": int(subset["distance_frac_diff"].le(0.10).sum()),
                "distance_pct_10_to_25": int(
                    (
                        subset["distance_frac_diff"].gt(0.10)
                        & subset["distance_frac_diff"].le(0.25)
                    ).sum()
                ),
                "distance_pct_gt_25": int(subset["distance_frac_diff"].gt(0.25).sum()),
                "median_distance_pct": _finite_median(
                    subset["distance_frac_diff"] * 100.0
                ),
                "median_gaia_quality": _finite_median(
                    subset["gaia_astrometry_quality"]
                ),
                "median_hip_quality": _finite_median(subset["hip_astrometry_quality"]),
            }
        )
    return pd.DataFrame(rows)


def _distance_histogram_bins(
    finite: pd.DataFrame,
    clean: pd.DataFrame,
) -> pd.DataFrame:
    clean_counts, edges = np.histogram(
        clean["distance_pct_diff"],
        bins=DISTANCE_HISTOGRAM_BINS,
    )
    all_counts, _ = np.histogram(
        finite["distance_pct_diff"],
        bins=DISTANCE_HISTOGRAM_BINS,
    )
    rows = []
    for start, end, clean_count, all_count in zip(
        edges[:-1],
        edges[1:],
        clean_counts,
        all_counts,
        strict=True,
    ):
        rows.append(
            {
                "bin_start_pct": float(start),
                "bin_end_pct": float(end),
                "clean_auto_eligible_count": int(clean_count),
                "all_candidate_count": int(all_count),
            }
        )
    return pd.DataFrame(rows)


def _quantiles(series: pd.Series) -> dict[str, float | None]:
    values = pd.to_numeric(series, errors="coerce")
    values = values[np.isfinite(values)]
    quantiles = [0, 0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99, 1.0]
    if values.empty:
        return {str(q): None for q in quantiles}
    return {str(q): float(values.quantile(q)) for q in quantiles}


def _finite_median(series: pd.Series) -> float | None:
    values = pd.to_numeric(series, errors="coerce")
    values = values[np.isfinite(values)]
    if values.empty:
        return None
    return float(values.median())


def _write_distance_histogram_plot(
    *,
    finite: pd.DataFrame,
    clean: pd.DataFrame,
    summary: pd.DataFrame,
    auto_distance_frac_diff: float,
    png_path: Path,
    svg_path: Path,
) -> bool:
    try:
        import matplotlib
    except ModuleNotFoundError:
        return False

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import PercentFormatter

    plt.style.use("seaborn-v0_8-whitegrid")
    fig = plt.figure(figsize=(14, 9), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, height_ratios=[3.0, 1.25], width_ratios=[2.4, 1.0])
    ax = fig.add_subplot(gs[0, 0])
    ax_cdf = fig.add_subplot(gs[1, 0])
    ax_table = fig.add_subplot(gs[:, 1])

    ax.hist(
        finite["distance_pct_diff"],
        bins=DISTANCE_HISTOGRAM_BINS,
        color="#c9d3d8",
        edgecolor="white",
        label=f"all broad evidence ({len(finite):,})",
    )
    ax.hist(
        clean["distance_pct_diff"],
        bins=DISTANCE_HISTOGRAM_BINS,
        color="#28785f",
        alpha=0.88,
        edgecolor="white",
        label=f"clean one-to-one eligible ({len(clean):,})",
    )
    threshold_pct = auto_distance_frac_diff * 100.0
    for x, color, label in [
        (threshold_pct, "#b0415a", f"{threshold_pct:.0f}% old veto"),
        (25.0, "#7048a8", "25% reference"),
    ]:
        ax.axvline(x, color=color, lw=2.2, ls="--")
        ymax = ax.get_ylim()[1]
        ax.text(x + 0.6, ymax * 0.93, label, color=color, weight="bold", fontsize=11)

    ax.set_title(
        "Gaia/HIP close-pair distance disagreement",
        fontsize=16,
        weight="bold",
        loc="left",
    )
    ax.set_xlabel("fractional distance disagreement (%)")
    ax.set_ylabel("candidate count")
    ax.legend(frameon=True, loc="upper right")
    ax.set_xlim(0, 100)
    ax.text(
        0.01,
        0.98,
        "distance = abs(Gaia r_pc - HIP r_pc) / max(r_pc) * 100",
        transform=ax.transAxes,
        va="top",
        fontsize=10,
        color="#555555",
    )

    xs = np.sort(clean["distance_pct_diff"].to_numpy(dtype=float))
    if len(xs):
        ys = np.arange(1, len(xs) + 1) / len(xs)
        ax_cdf.plot(xs, ys, color="#28785f", lw=2)
    for x, color in [(threshold_pct, "#b0415a"), (25.0, "#7048a8")]:
        ax_cdf.axvline(x, color=color, lw=1.8, ls="--")
    ax_cdf.set_xlim(0, 100)
    ax_cdf.set_ylim(0, 1)
    ax_cdf.yaxis.set_major_formatter(PercentFormatter(1.0))
    ax_cdf.set_xlabel("fractional distance disagreement (%)")
    ax_cdf.set_ylabel("cumulative share")
    ax_cdf.set_title("Clean eligible cumulative distribution", fontsize=12, loc="left")

    ax_table.axis("off")
    ax_table.set_title("Policy comparison", fontsize=14, weight="bold", loc="left")
    lines = [
        f"Clean eligible candidates: {len(clean):,}",
        "",
    ]
    for row in summary.itertuples(index=False):
        delta = int(row.delta_vs_broad_scan_policy)
        delta_text = (
            "current" if row.policy == "broad clean one-to-one" else f"{delta:+,}"
        )
        lines.append(str(row.policy))
        lines.append(f"  matched: {int(row.matched_clean_count):,}")
        lines.append(f"  delta vs broad: {delta_text}")
        lines.append(f"  non-tight added: {int(row.non_tight_added):,}")
        lines.append("")
    lines.extend(
        [
            "Key read:",
            "distance disagreement follows",
            "astrometry quality, so it is",
            "diagnostic evidence, not a veto.",
        ]
    )
    ax_table.text(
        0.0,
        1.0,
        "\n".join(lines),
        transform=ax_table.transAxes,
        va="top",
        ha="left",
        family="DejaVu Sans Mono",
        fontsize=10.5,
        linespacing=1.35,
    )

    fig.suptitle(
        "Bright-star audit: distance threshold shape",
        fontsize=18,
        weight="bold",
        x=0.03,
        ha="left",
    )
    fig.savefig(png_path, dpi=180, bbox_inches="tight")
    fig.savefig(svg_path, bbox_inches="tight")
    plt.close(fig)
    return True


def _write_distance_quality_plot(
    *,
    clean: pd.DataFrame,
    quality_summary: pd.DataFrame,
    auto_distance_frac_diff: float,
    png_path: Path,
    svg_path: Path,
) -> bool:
    try:
        import matplotlib
    except ModuleNotFoundError:
        return False

    plot = clean.loc[
        np.isfinite(clean["distance_pct_diff"])
        & clean["distance_pct_diff"].gt(0)
        & np.isfinite(clean["worst_astrometry_quality"])
        & clean["worst_astrometry_quality"].gt(0)
    ].copy()
    if plot.empty:
        return False

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    old_threshold = auto_distance_frac_diff * 100.0
    tight = plot["within_auto_thresholds"].astype(bool)
    pct_old_threshold = plot["distance_pct_diff"].le(old_threshold)
    pct25 = plot["distance_pct_diff"].le(25.0)

    categories = [
        (
            "tight sky/mag auto",
            tight,
            "#28785f",
            22,
            0.75,
        ),
        (
            f"non-tight <= {old_threshold:.0f}% distance",
            ~tight & pct_old_threshold,
            "#3b82b7",
            18,
            0.55,
        ),
        (
            f"non-tight {old_threshold:.0f}-25% distance",
            ~tight & ~pct_old_threshold & pct25,
            "#7048a8",
            18,
            0.55,
        ),
        (
            "non-tight >25% distance",
            ~tight & ~pct25,
            "#b26b3d",
            16,
            0.40,
        ),
    ]

    plt.style.use("seaborn-v0_8-whitegrid")
    fig = plt.figure(figsize=(14, 8.5))
    gs = fig.add_gridspec(2, 2, height_ratios=[2.5, 1.2], width_ratios=[2.2, 1.0])
    ax = fig.add_subplot(gs[:, 0])
    ax_summary = fig.add_subplot(gs[0, 1])
    ax_note = fig.add_subplot(gs[1, 1])

    for label, mask, color, size, alpha in categories:
        subset = plot.loc[mask]
        if subset.empty:
            continue
        ax.scatter(
            subset["worst_astrometry_quality"],
            subset["distance_pct_diff"],
            s=size,
            alpha=alpha,
            color=color,
            edgecolors="none",
            label=f"{label} ({len(subset):,})",
        )

    for y, color, label in [
        (old_threshold, "#b0415a", f"{old_threshold:.0f}% old veto"),
        (25.0, "#7048a8", "25% reference"),
    ]:
        ax.axhline(y, color=color, lw=2.0, ls="--")
        ax.text(
            plot["worst_astrometry_quality"].min() * 1.2,
            y * 1.06,
            label,
            color=color,
            weight="bold",
            fontsize=11,
        )
    for x, label in [(0.1, "10% quality"), (0.25, "25% quality"), (1.0, "100%")]:
        ax.axvline(x, color="#555555", lw=1.2, ls=":", alpha=0.85)
        ax.text(x * 1.05, 0.0018, label, rotation=90, fontsize=9, color="#444444")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(
        max(plot["worst_astrometry_quality"].min() * 0.75, 1e-4),
        min(plot["worst_astrometry_quality"].max() * 1.35, 1e3),
    )
    ax.set_ylim(
        max(plot["distance_pct_diff"].min() * 0.75, 1e-3),
        min(max(plot["distance_pct_diff"].max() * 1.15, 120.0), 200.0),
    )
    ax.set_title(
        "Distance disagreement vs worst astrometry quality",
        fontsize=16,
        weight="bold",
        loc="left",
    )
    ax.set_xlabel("worst Gaia/HIP astrometry quality (fractional uncertainty proxy)")
    ax.set_ylabel("fractional distance disagreement (%)")
    ax.legend(loc="upper left", frameon=True, fontsize=9)

    ax_summary.axis("off")
    rows = []
    for rec in quality_summary.itertuples(index=False):
        if int(rec.rows) == 0:
            continue
        rows.append(
            [
                rec.worst_quality_bin,
                f"{int(rec.rows):,}",
                f"{int(rec.distance_pct_le_10):,}",
                f"{int(rec.distance_pct_10_to_25):,}",
                f"{int(rec.distance_pct_gt_25):,}",
            ]
        )
    table = ax_summary.table(
        cellText=rows,
        colLabels=["worst q", "rows", "<=10", "10-25", ">25"],
        loc="center",
        cellLoc="right",
        colLoc="right",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8.5)
    table.scale(1.0, 1.25)
    ax_summary.set_title("Quality-bin counts", fontsize=13, weight="bold", loc="left")

    log_x = np.log10(plot["worst_astrometry_quality"].to_numpy(dtype=float))
    log_y = np.log10(plot["distance_pct_diff"].to_numpy(dtype=float))
    corr = float(np.corrcoef(log_x, log_y)[0, 1]) if len(plot) > 1 else float("nan")
    ax_note.axis("off")
    ax_note.text(
        0.0,
        1.0,
        "\n".join(
            [
                "Interpretation",
                "",
                "Lower quality values are better.",
                "HIP quality often dominates the",
                "worst-pair score in this sample.",
                "Distance disagreement is recorded",
                "but no longer vetoes clean links.",
                "",
                f"log-log correlation: {corr:.2f}",
            ]
        ),
        va="top",
        ha="left",
        fontsize=11,
    )

    fig.suptitle(
        "Bright-star audit: parallax-quality relationship",
        fontsize=18,
        weight="bold",
        x=0.03,
        ha="left",
    )
    fig.subplots_adjust(left=0.07, right=0.97, top=0.90, bottom=0.10, wspace=0.28)
    fig.savefig(png_path, dpi=180, bbox_inches="tight")
    fig.savefig(svg_path, bbox_inches="tight")
    plt.close(fig)
    return True


def _candidate_record(
    *,
    gaia_rec: pd.Series | None,
    hip_rec: pd.Series | None,
    gaia_source_id: str | None = None,
    hip_source_id: str | None = None,
    sep_arcsec: float,
    local_scan_pair: bool,
    h2bn_gaia_to_hip: dict[str, str],
    h2bn_hip_to_gaia: dict[str, str],
    h2bn_pairs: set[tuple[str, str]],
    h2bn_metadata: dict[tuple[str, str], tuple[int, float]],
) -> dict[str, Any]:
    gaia_id = gaia_source_id or str(gaia_rec["source_id"])
    hip_id = hip_source_id or str(hip_rec["source_id"])
    gaia_h2bn_hip = h2bn_gaia_to_hip.get(gaia_id)
    hip_h2bn_gaia = h2bn_hip_to_gaia.get(hip_id)
    gaia_has_map = gaia_h2bn_hip is not None
    hip_has_map = hip_h2bn_gaia is not None
    h2bn_pair = (gaia_id, hip_id) in h2bn_pairs
    h2bn_conflict = (
        (gaia_has_map and gaia_h2bn_hip != hip_id)
        or (hip_has_map and hip_h2bn_gaia != gaia_id)
    )
    gaia_r = _safe_float(_record_get(gaia_rec, "r_pc"))
    hip_r = _safe_float(_record_get(hip_rec, "r_pc"))
    radial_gap = (
        abs(gaia_r - hip_r)
        if math.isfinite(gaia_r) and math.isfinite(hip_r)
        else math.nan
    )
    gaia_quality = _safe_float(_record_get(gaia_rec, "astrometry_quality"))
    hip_quality = _safe_float(_record_get(hip_rec, "astrometry_quality"))
    combined_sigma = (
        math.sqrt((gaia_r * gaia_quality) ** 2 + (hip_r * hip_quality) ** 2)
        if all(
            math.isfinite(value)
            for value in (gaia_r, hip_r, gaia_quality, hip_quality)
        )
        else math.nan
    )
    radial_gap_sigma = (
        radial_gap / combined_sigma
        if math.isfinite(radial_gap)
        and math.isfinite(combined_sigma)
        and combined_sigma > 0
        else math.nan
    )
    separation_3d = _separation_3d_pc(gaia_r, hip_r, sep_arcsec)
    gaia_g = _safe_float(_record_get(gaia_rec, "phot_g_mean_mag"))
    hip_hp = _safe_float(_record_get(hip_rec, "Hpmag"))
    signed_mag_difference = (
        gaia_g - hip_hp
        if math.isfinite(gaia_g) and math.isfinite(hip_hp)
        else math.nan
    )
    h2bn_neighbours, h2bn_angular_distance = h2bn_metadata.get(
        (gaia_id, hip_id), (pd.NA, math.nan)
    )
    return {
        "gaia_source_id": int(gaia_id),
        "hip_source_id": int(hip_id),
        "h2bn_pair": h2bn_pair,
        "local_scan_pair": local_scan_pair,
        "separation_arcsec": sep_arcsec,
        "gaia_ra_deg": _safe_float(_record_get(gaia_rec, "ra_deg")),
        "gaia_dec_deg": _safe_float(_record_get(gaia_rec, "dec_deg")),
        "hip_ra_deg": _safe_float(_record_get(hip_rec, "ra_deg")),
        "hip_dec_deg": _safe_float(_record_get(hip_rec, "dec_deg")),
        "gaia_g_mag": gaia_g,
        "hip_hp_mag": hip_hp,
        "gaia_g_minus_hip_hp_mag": signed_mag_difference,
        "abs_gaia_g_minus_hip_hp_mag": abs(signed_mag_difference),
        "gaia_r_pc": gaia_r,
        "hip_r_pc": hip_r,
        "radial_gap_pc": radial_gap,
        "combined_distance_sigma_pc": combined_sigma,
        "radial_gap_sigma": radial_gap_sigma,
        "parallax_3d_separation_pc": separation_3d,
        "gaia_plx_mas": _safe_float(_record_get(gaia_rec, "parallax")),
        "gaia_e_plx_mas": _safe_float(_record_get(gaia_rec, "parallax_error")),
        "hip_plx_mas": _safe_float(_record_get(hip_rec, "Plx")),
        "hip_e_plx_mas": _safe_float(_record_get(hip_rec, "e_Plx")),
        "gaia_astrometry_quality": gaia_quality,
        "hip_astrometry_quality": hip_quality,
        "gaia_photometry_quality": _safe_float(
            _record_get(gaia_rec, "photometry_quality")
        ),
        "hip_photometry_quality": _safe_float(
            _record_get(hip_rec, "photometry_quality")
        ),
        "gaia_ruwe": _safe_float(_record_get(gaia_rec, "ruwe")),
        "gaia_phot_g_mean_mag": gaia_g,
        "hip_solution_type": _safe_float(_record_get(hip_rec, "Sn")),
        "hip_hpmag": hip_hp,
        "gaia_has_h2bn_map": gaia_has_map,
        "hip_has_h2bn_map": hip_has_map,
        "h2bn_conflict": h2bn_conflict,
        "gaia_h2bn_hip_source_id": (
            int(gaia_h2bn_hip) if gaia_h2bn_hip is not None else pd.NA
        ),
        "hip_h2bn_gaia_source_id": (
            int(hip_h2bn_gaia) if hip_h2bn_gaia is not None else pd.NA
        ),
        "h2bn_number_of_neighbours": h2bn_neighbours,
        "h2bn_angular_distance": h2bn_angular_distance,
        "gaia_candidate_count": 1 if local_scan_pair else pd.NA,
        "hip_candidate_count": 1 if local_scan_pair else pd.NA,
        "one_to_one_candidate": True if local_scan_pair else pd.NA,
    }


def _load_processed_candidates(paths: Iterable[Path], source_name: str) -> pd.DataFrame:
    columns = [
        "source",
        "source_id",
        "ra_deg",
        "dec_deg",
        "r_pc",
        "astrometry_quality",
        "photometry_quality",
        "ruwe",
        "phot_g_mean_mag",
        "parallax",
        "parallax_error",
        "Sn",
        "Hpmag",
        "Plx",
        "e_Plx",
    ]
    chunks: list[pd.DataFrame] = []
    for batch in _iter_parquet_batches(paths, columns):
        source = batch["source"].fillna(source_name).astype(str)
        mask = source.eq(source_name)
        numeric = batch.copy()
        for col in [
            "ra_deg",
            "dec_deg",
            "r_pc",
            "astrometry_quality",
            "photometry_quality",
            "ruwe",
            "phot_g_mean_mag",
            "parallax",
            "parallax_error",
            "Sn",
            "Hpmag",
            "Plx",
            "e_Plx",
        ]:
            numeric[col] = pd.to_numeric(numeric[col], errors="coerce")
        source_ids = pd.to_numeric(batch["source_id"], errors="coerce")
        valid_id = source_ids.notna() & source_ids.gt(0)
        out = numeric.loc[mask & valid_id].copy()
        if out.empty:
            continue
        out["source"] = source.loc[out.index].to_numpy()
        out["source_id"] = (
            pd.to_numeric(batch.loc[out.index, "source_id"], errors="raise")
            .astype("uint64")
            .astype(str)
            .to_numpy()
        )
        chunks.append(out[columns])
    if not chunks:
        return pd.DataFrame(
            columns=[
                "source",
                "source_id",
                "ra_deg",
                "dec_deg",
                "r_pc",
                "astrometry_quality",
                "photometry_quality",
                "ruwe",
                "phot_g_mean_mag",
                "parallax",
                "parallax_error",
                "Sn",
                "Hpmag",
                "Plx",
                "e_Plx",
            ]
        )
    return pd.concat(chunks, ignore_index=True)


def _read_crossmatch(path: Path) -> pd.DataFrame:
    return _normalize_crossmatch_frame(pq.read_table(path).to_pandas())


def _normalize_crossmatch_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return empty_gaia_hip_mapping()
    out = df.copy()
    if "mapping_source" not in out:
        out["mapping_source"] = MAPPING_SOURCE_HIPPARCOS2_BEST_NEIGHBOUR
    if "number_of_neighbours" not in out:
        out["number_of_neighbours"] = np.int16(0)
    if "angular_distance" not in out:
        out["angular_distance"] = np.float32(np.nan)
    out["gaia_source_id"] = _parse_uint_series(out["gaia_source_id"]).astype("uint64")
    out["hip_source_id"] = _parse_uint_series(out["hip_source_id"]).astype("uint64")
    out["mapping_source"] = out["mapping_source"].fillna("").astype(str)
    out["number_of_neighbours"] = (
        pd.to_numeric(out["number_of_neighbours"], errors="coerce")
        .fillna(0)
        .astype(np.int16)
    )
    out["angular_distance"] = pd.to_numeric(
        out["angular_distance"], errors="coerce"
    ).astype(np.float32)
    return out[GAIA_HIP_MAP_COLS].drop_duplicates(
        ["gaia_source_id", "hip_source_id"]
    ).sort_values(
        ["gaia_source_id", "hip_source_id"],
        kind="mergesort",
        ignore_index=True,
    )


def _iter_parquet_batches(paths: Iterable[Path], columns: list[str]):
    for path in paths:
        parquet = pq.ParquetFile(path)
        present = [c for c in columns if c in parquet.schema_arrow.names]
        if not present:
            continue
        for batch in parquet.iter_batches(columns=present, batch_size=BATCH_SIZE):
            df = batch.to_pandas()
            for col in columns:
                if col not in df:
                    df[col] = pd.NA
            yield df[columns]


def _load_override_keys(path: Path) -> set[tuple[str, str]]:
    df = pq.read_table(path, columns=["source", "source_id", "action"]).to_pandas()
    if df.empty:
        return set()
    return {
        (str(rec.source), str(rec.source_id))
        for rec in df.itertuples(index=False)
        if str(rec.action) in {"replace", "drop", "add"}
    }


def _unit_vectors(ra_deg: pd.Series, dec_deg: pd.Series) -> np.ndarray:
    ra = np.radians(pd.to_numeric(ra_deg, errors="coerce").to_numpy(dtype=float))
    dec = np.radians(pd.to_numeric(dec_deg, errors="coerce").to_numpy(dtype=float))
    cos_dec = np.cos(dec)
    return np.column_stack(
        [
            cos_dec * np.cos(ra),
            cos_dec * np.sin(ra),
            np.sin(dec),
        ]
    )


def _require_ckdtree():
    try:
        from scipy.spatial import cKDTree
    except ImportError as exc:
        raise RuntimeError(
            "Audit matching requires the optional audit dependency group. "
            "Install or run with `uv sync --group audit` or "
            "`uv run --group audit ...`."
        ) from exc
    return cKDTree


def _parse_uint_series(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    values = numeric.to_numpy(dtype=float, na_value=np.nan, copy=False)
    if np.any(~np.isfinite(values)):
        raise ValueError("crossmatch contains non-finite IDs")
    if np.any(values <= 0) or np.any(np.floor(values) != values):
        raise ValueError("crossmatch contains non-positive or non-integer IDs")
    return numeric.astype("uint64")


def _safe_float(value: Any) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return math.nan
    return out if math.isfinite(out) else math.nan


def _mapping_dict(mapping: pd.DataFrame, key_col: str) -> dict[str, str]:
    value_col = "hip_source_id" if key_col == "gaia_source_id" else "gaia_source_id"
    return {
        str(int(getattr(rec, key_col))): str(int(getattr(rec, value_col)))
        for rec in mapping[[key_col, value_col]].itertuples(index=False)
    }


def _record_get(record: pd.Series | None, key: str) -> Any:
    if record is None:
        return None
    return record.get(key)


def _processed_angular_separation_arcsec(
    gaia_rec: pd.Series | None,
    hip_rec: pd.Series | None,
) -> float:
    values = (
        _safe_float(_record_get(gaia_rec, "ra_deg")),
        _safe_float(_record_get(gaia_rec, "dec_deg")),
        _safe_float(_record_get(hip_rec, "ra_deg")),
        _safe_float(_record_get(hip_rec, "dec_deg")),
    )
    if not all(math.isfinite(value) for value in values):
        return math.nan
    gaia_xyz = _unit_vectors(pd.Series([values[0]]), pd.Series([values[1]]))[0]
    hip_xyz = _unit_vectors(pd.Series([values[2]]), pd.Series([values[3]]))[0]
    dot = float(np.clip(gaia_xyz @ hip_xyz, -1.0, 1.0))
    return math.degrees(math.acos(dot)) * 3600.0


def _separation_3d_pc(
    gaia_r_pc: float,
    hip_r_pc: float,
    separation_arcsec: float,
) -> float:
    if not all(
        math.isfinite(value)
        for value in (gaia_r_pc, hip_r_pc, separation_arcsec)
    ):
        return math.nan
    separation_rad = math.radians(separation_arcsec / 3600.0)
    squared = (
        gaia_r_pc**2
        + hip_r_pc**2
        - 2.0 * gaia_r_pc * hip_r_pc * math.cos(separation_rad)
    )
    return math.sqrt(max(squared, 0.0))


def _descriptive_bins(
    values: pd.Series,
    *,
    edges: tuple[float, ...],
    labels: tuple[str, ...],
) -> dict[str, int]:
    numeric = pd.to_numeric(values, errors="coerce")
    finite = numeric[np.isfinite(numeric)]
    if len(labels) != len(edges) + 1:
        raise ValueError("Descriptive bin labels must be one longer than edges")
    counts: dict[str, int] = {}
    lower = -math.inf
    for edge, label in zip(edges, labels[:-1], strict=True):
        counts[label] = int(((finite > lower) & (finite <= edge)).sum())
        lower = edge
    counts[labels[-1]] = int((finite > lower).sum())
    counts["missing"] = int(numeric.isna().sum())
    return counts


def _staged_pairing_context_counts(evidence: pd.DataFrame) -> dict[str, int]:
    counts = {
        column: int(evidence[column].fillna(False).astype(bool).sum())
        for column in (
            "one_to_one_candidate",
            "gaia_has_h2bn_map",
            "hip_has_h2bn_map",
            "h2bn_conflict",
        )
    }
    local = evidence["local_scan_pair"].fillna(False).astype(bool)
    h2bn = evidence["h2bn_pair"].fillna(False).astype(bool)
    one_to_one = evidence["one_to_one_candidate"].fillna(False).astype(bool)
    counts["ambiguous_local_pair"] = int((local & ~one_to_one).sum())
    counts["ambiguous_h2bn_local_pair"] = int(
        (h2bn & local & ~one_to_one).sum()
    )
    return counts


def _empty_match_evidence() -> pd.DataFrame:
    return pd.DataFrame(columns=MATCH_EVIDENCE_COLS)


def _octree_record(**kwargs: Any) -> dict[str, Any]:
    rec = dict.fromkeys(OCTREE_REVIEW_COLS, pd.NA)
    rec.update(kwargs)
    rec["source"] = str(rec["source"])
    rec["source_id"] = str(rec["source_id"])
    if not pd.isna(rec["linked_source"]):
        rec["linked_source"] = str(rec["linked_source"])
    if not pd.isna(rec["linked_source_id"]):
        rec["linked_source_id"] = str(rec["linked_source_id"])
    return rec


def _manual_record(**kwargs: Any) -> dict[str, Any]:
    rec = dict.fromkeys(MANUAL_CANDIDATE_COLS, pd.NA)
    rec.update(kwargs)
    if not pd.isna(rec["source"]):
        rec["source"] = str(rec["source"])
    if not pd.isna(rec["source_id"]):
        rec["source_id"] = str(rec["source_id"])
    return rec


def _prepare_output_dir(path: Path, *, force: bool) -> None:
    if path.exists():
        if any(path.iterdir()) and not force:
            raise FileExistsError(str(path))
        if force:
            shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _prepare_report_outputs(
    audit_dir: Path,
    sidecar_output_dir: Path,
    *,
    force: bool,
) -> None:
    audit_dir.mkdir(parents=True, exist_ok=True)
    for path in [
        audit_dir / OCTREE_REVIEW_FILENAME,
        audit_dir / MANUAL_CANDIDATES_FILENAME,
        audit_dir / MANUAL_CANDIDATES_CSV_FILENAME,
        audit_dir / AUDIT_REPORT_FILENAME,
    ]:
        if path.exists():
            if not force:
                raise FileExistsError(str(path))
            path.unlink()
    sidecar_root = sidecar_output_dir / "octree_review"
    if sidecar_root.exists():
        if any(sidecar_root.iterdir()) and not force:
            raise FileExistsError(str(sidecar_root))
        if force:
            shutil.rmtree(sidecar_root)


def _write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(table, str(path), compression="zstd")


def _write_json(data: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        json.dump(data, fp, indent=2, sort_keys=True)


def _value_counts(df: pd.DataFrame, column: str) -> dict[str, int]:
    if df.empty or column not in df:
        return {}
    return {str(key): int(value) for key, value in df[column].value_counts().items()}
