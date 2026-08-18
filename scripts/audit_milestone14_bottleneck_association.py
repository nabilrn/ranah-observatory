#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "research/MILESTONE14_BOTTLENECK_ASSOCIATION_SPEC.md"
GATE = ROOT / "data/manifests/milestone14_design_gate.json"
MANIFEST = ROOT / "data/manifests/milestone14_bottleneck_association.json"
M10_MANIFEST = ROOT / "data/manifests/milestone10_analytical_panel.json"
M13_MANIFEST = ROOT / "data/manifests/milestone13_development_gap_decomposition.json"
FRAME = ROOT / "data/analysis/engine/bottleneck_association_v1/m14-association-frame.csv"
ASSOCIATIONS = ROOT / "data/analysis/engine/bottleneck_association_v1/m14-feature-associations.csv"
YEAR = ROOT / "data/analysis/engine/bottleneck_association_v1/m14-year-specific-correlations.csv"
LOO = ROOT / "data/analysis/engine/bottleneck_association_v1/m14-leave-one-geography-out.csv"
STABLE = ROOT / "data/analysis/engine/bottleneck_association_v1/m14-stable-association-candidates.csv"

TARGETS = ["poverty_rate", "unemployment_rate", "real_grdp_growth"]
CANDIDATES = ["expected_years_schooling", "life_expectancy", "underemployment_rate", "annual_rainfall"]
TARGET_YEARS = [2021, 2022, 2023, 2024]
FEATURE_YEARS = [2020, 2021, 2022, 2023]
ABS_THRESHOLD = 0.25
MIN_ANNUAL_SIGN = 3
MIN_SUPPORT_ROWS = 40


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def num(row: dict[str, str], key: str) -> float:
    try:
        value = float(row[key])
    except (KeyError, ValueError) as exc:
        raise ValueError(f"invalid numeric field {key}") from exc
    if not math.isfinite(value):
        raise ValueError(f"non-finite numeric field {key}")
    return value


def mean(values: list[float]) -> float:
    if not values:
        raise ValueError("mean requires values")
    return sum(values) / len(values)


def median(values: list[float]) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("median requires values")
    n = len(ordered)
    return ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2.0


def pearson(x: list[float], y: list[float]) -> float:
    if len(x) != len(y) or len(x) < 3:
        raise ValueError("pearson requires >=3 paired values")
    mx, my = mean(x), mean(y)
    sx = sum((v - mx) ** 2 for v in x)
    sy = sum((v - my) ** 2 for v in y)
    if sx <= 1e-18 or sy <= 1e-18:
        raise ValueError("constant vector")
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / math.sqrt(sx * sy)


def ranks(values: list[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda pair: pair[1])
    result = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i + 1
        while j < len(indexed) and indexed[j][1] == indexed[i][1]:
            j += 1
        rank = (i + 1 + j) / 2.0
        for pos in range(i, j):
            result[indexed[pos][0]] = rank
        i = j
    return result


def spearman(x: list[float], y: list[float]) -> float:
    return pearson(ranks(x), ranks(y))


def sign(value: float, eps: float = 1e-12) -> int:
    return 1 if value > eps else -1 if value < -eps else 0


def close(a: float, b: float, tol: float = 1e-8) -> bool:
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def year_demeaned_pairs(data: list[dict[str, str]], candidate: str, gap_field: str) -> tuple[list[float], list[float]]:
    by_year: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in data:
        by_year[int(row["target_year"])].append(row)
    xs: list[float] = []
    ys: list[float] = []
    for year in sorted(by_year):
        year_rows = by_year[year]
        candidate_values = [num(row, f"lag1_{candidate}") for row in year_rows]
        gap_values = [num(row, gap_field) for row in year_rows]
        mx, my = mean(candidate_values), mean(gap_values)
        xs.extend(value - mx for value in candidate_values)
        ys.extend(value - my for value in gap_values)
    return xs, ys


def pooled(data: list[dict[str, str]], candidate: str, gap_field: str) -> tuple[float, float]:
    x, y = year_demeaned_pairs(data, candidate, gap_field)
    return pearson(x, y), spearman(x, y)


def audit() -> dict[str, Any]:
    errors: list[str] = []
    required = [SPEC, GATE, MANIFEST, M10_MANIFEST, M13_MANIFEST, FRAME, ASSOCIATIONS, YEAR, LOO, STABLE]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        return {"schema": "ranah-observatory/milestone14-audit/v1", "milestone14_complete": False, "errors": [f"missing: {p}" for p in missing]}

    spec = SPEC.read_text(encoding="utf-8")
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    m10 = json.loads(M10_MANIFEST.read_text(encoding="utf-8"))
    m13 = json.loads(M13_MANIFEST.read_text(encoding="utf-8"))
    frame = rows(FRAME)
    associations = rows(ASSOCIATIONS)
    annual = rows(YEAR)
    loo = rows(LOO)
    stable = rows(STABLE)

    if m10.get("milestone10_complete") is not True or m13.get("milestone13_complete") is not True:
        errors.append("M14 requires complete M10 and M13")

    expected_gate = {
        "schema": "ranah-observatory/milestone14-design-gate/v1",
        "target_years": TARGET_YEARS,
        "feature_years": FEATURE_YEARS,
        "feature_lag_years": 1,
        "target_ids": TARGETS,
        "primary_gap_field": "expected_gap_rmse_units",
        "sensitivity_gap_field": "favorable_peer_gap_rmse_units",
        "candidate_ids": CANDIDATES,
        "primary_statistic": "pooled_year_demeaned_spearman",
        "secondary_statistic": "pooled_year_demeaned_pearson",
        "stable_abs_spearman_threshold": ABS_THRESHOLD,
        "stable_min_same_sign_annual_count": MIN_ANNUAL_SIGN,
        "stable_require_all_loo_same_sign": True,
        "stable_min_support_safe_rows": MIN_SUPPORT_ROWS,
        "stable_require_support_safe_same_sign": True,
        "p_value_selection_authorized": False,
        "candidate_selection_after_results_authorized": False,
        "association_results_computed": False,
        "association_results_inspected": False,
        "causal_claim_authorized": False,
        "bottleneck_causal_claim_authorized": False,
        "policy_effect_claim_authorized": False,
        "monetary_wasted_potential_claim_authorized": False,
        "milestone14_complete": False,
    }
    for key, expected in expected_gate.items():
        if gate.get(key) != expected:
            errors.append(f"M14 prefit gate drift: {key}")

    expected_manifest = {
        "schema": "ranah-observatory/milestone14-bottleneck-association/v1",
        "phase": "final_analytical_research_engine",
        "milestone": 14,
        "target_years": TARGET_YEARS,
        "feature_years": FEATURE_YEARS,
        "feature_lag_years": 1,
        "geography_count": 19,
        "target_ids": TARGETS,
        "candidate_ids": CANDIDATES,
        "association_frame_row_count": 228,
        "feature_association_row_count": 12,
        "annual_correlation_row_count": 48,
        "loo_correlation_row_count": 228,
        "primary_gap_field": "expected_gap_rmse_units",
        "sensitivity_gap_field": "favorable_peer_gap_rmse_units",
        "stable_abs_spearman_threshold": ABS_THRESHOLD,
        "stable_min_same_sign_annual_count": MIN_ANNUAL_SIGN,
        "stable_require_all_loo_same_sign": True,
        "stable_min_support_safe_rows": MIN_SUPPORT_ROWS,
        "stable_require_support_safe_same_sign": True,
        "no_imputation": True,
        "p_value_selection_used": False,
        "candidate_selection_after_results_performed": False,
        "m11_primary_feature_reuse_in_candidate_set": False,
        "causal_analysis_performed": False,
        "bottleneck_causal_claim": False,
        "policy_effect_claim": False,
        "monetary_wasted_potential_claim": False,
        "annual_rainfall_claim_type": "model_estimate",
        "annual_rainfall_station_equivalence_claim": False,
        "annual_rainfall_climate_change_attribution_claim": False,
        "prefit_gate_preserved": True,
        "milestone14_complete": True,
    }
    for key, expected in expected_manifest.items():
        if manifest.get(key) != expected:
            errors.append(f"M14 manifest drift: {key}")

    for path_string, digest in manifest.get("source_inputs", {}).items():
        path = ROOT / path_string
        if not path.exists() or sha256(path) != digest:
            errors.append(f"M14 source checksum drift: {path_string}")
    output_map = {
        "association_frame": FRAME,
        "feature_associations": ASSOCIATIONS,
        "year_specific_correlations": YEAR,
        "leave_one_geography_out": LOO,
        "stable_association_candidates": STABLE,
    }
    for key, path in output_map.items():
        record = manifest.get("outputs", {}).get(key, {})
        if record.get("path") != str(path.relative_to(ROOT)) or record.get("sha256") != sha256(path):
            errors.append(f"M14 output checksum/path drift: {key}")

    if len(frame) != 228:
        errors.append(f"M14 association frame must contain 228 rows, got {len(frame)}")
    frame_keys = {(row["target_id"], row["geography_id"], row["target_year"]) for row in frame}
    if len(frame_keys) != 228:
        errors.append("M14 association-frame keys are not unique")
    geographies = sorted({row["geography_id"] for row in frame})
    if len(geographies) != 19:
        errors.append("M14 must contain exact 19 geographies")
    for row in frame:
        target_year = int(row["target_year"])
        feature_year = int(row["feature_year"])
        if target_year not in TARGET_YEARS or feature_year != target_year - 1:
            errors.append("M14 feature-lag contract drift")
        for candidate in CANDIDATES:
            try:
                num(row, f"lag1_{candidate}")
            except ValueError as exc:
                errors.append(f"M14 candidate value error: {exc}")
        for field in ["expected_gap_rmse_units", "favorable_peer_gap_rmse_units"]:
            try:
                num(row, field)
            except ValueError as exc:
                errors.append(f"M14 gap value error: {exc}")

    assoc_by = {(row["target_id"], row["candidate_id"]): row for row in associations}
    if len(associations) != 12 or len(assoc_by) != 12:
        errors.append("M14 association summary must contain exact 12 target-candidate rows")
    annual_by: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in annual:
        annual_by[(row["target_id"], row["candidate_id"])].append(row)
    loo_by: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in loo:
        loo_by[(row["target_id"], row["candidate_id"])].append(row)
    if len(annual) != 48:
        errors.append("M14 annual table must contain 48 rows")
    if len(loo) != 228:
        errors.append("M14 LOO table must contain 228 rows")

    expected_stable_keys: set[tuple[str, str]] = set()
    for target in TARGETS:
        target_rows = [row for row in frame if row["target_id"] == target]
        if len(target_rows) != 76:
            errors.append(f"M14 target frame must contain 76 rows: {target}")
            continue
        for candidate in CANDIDATES:
            summary = assoc_by.get((target, candidate))
            if summary is None:
                continue
            p, s = pooled(target_rows, candidate, "expected_gap_rmse_units")
            if not close(num(summary, "pooled_year_demeaned_pearson"), p) or not close(num(summary, "pooled_year_demeaned_spearman"), s):
                errors.append(f"M14 primary association mismatch: {target}/{candidate}")
            primary_sign = sign(s)

            annual_rows = annual_by[(target, candidate)]
            if len(annual_rows) != 4 or {int(row["target_year"]) for row in annual_rows} != set(TARGET_YEARS):
                errors.append(f"M14 annual footprint mismatch: {target}/{candidate}")
            annual_same_sign = 0
            annual_s_values: list[float] = []
            for year in TARGET_YEARS:
                source = [row for row in target_rows if int(row["target_year"]) == year]
                x = [num(row, f"lag1_{candidate}") for row in source]
                y = [num(row, "expected_gap_rmse_units") for row in source]
                expected_p, expected_s = pearson(x, y), spearman(x, y)
                annual_row = next(row for row in annual_rows if int(row["target_year"]) == year)
                if not close(num(annual_row, "pearson"), expected_p) or not close(num(annual_row, "spearman"), expected_s):
                    errors.append(f"M14 annual correlation mismatch: {target}/{candidate}/{year}")
                same_sign = primary_sign != 0 and sign(expected_s) == primary_sign
                annual_same_sign += bool(same_sign)
                annual_s_values.append(expected_s)
                if (annual_row["same_sign_as_primary_pooled_spearman"] == "true") != same_sign:
                    errors.append(f"M14 annual sign flag mismatch: {target}/{candidate}/{year}")
            if int(summary["same_sign_annual_spearman_count"]) != annual_same_sign:
                errors.append(f"M14 annual sign count mismatch: {target}/{candidate}")
            if not close(num(summary, "annual_spearman_min"), min(annual_s_values)) or not close(num(summary, "annual_spearman_max"), max(annual_s_values)):
                errors.append(f"M14 annual range mismatch: {target}/{candidate}")

            loo_rows = loo_by[(target, candidate)]
            if len(loo_rows) != 19 or {row["excluded_geography_id"] for row in loo_rows} != set(geographies):
                errors.append(f"M14 LOO footprint mismatch: {target}/{candidate}")
            loo_values: list[float] = []
            loo_same_sign = 0
            for excluded in geographies:
                subset = [row for row in target_rows if row["geography_id"] != excluded]
                expected_p, expected_s = pooled(subset, candidate, "expected_gap_rmse_units")
                loo_row = next(row for row in loo_rows if row["excluded_geography_id"] == excluded)
                if not close(num(loo_row, "year_demeaned_pearson"), expected_p) or not close(num(loo_row, "year_demeaned_spearman"), expected_s):
                    errors.append(f"M14 LOO correlation mismatch: {target}/{candidate}/{excluded}")
                same_sign = primary_sign != 0 and sign(expected_s) == primary_sign
                loo_same_sign += bool(same_sign)
                loo_values.append(expected_s)
                if (loo_row["same_sign_as_primary_pooled_spearman"] == "true") != same_sign:
                    errors.append(f"M14 LOO sign flag mismatch: {target}/{candidate}/{excluded}")
            if int(summary["loo_same_sign_count"]) != loo_same_sign:
                errors.append(f"M14 LOO sign count mismatch: {target}/{candidate}")
            if not close(num(summary, "loo_spearman_min"), min(loo_values)) or not close(num(summary, "loo_spearman_median"), median(loo_values)) or not close(num(summary, "loo_spearman_max"), max(loo_values)):
                errors.append(f"M14 LOO range mismatch: {target}/{candidate}")

            support_safe = [row for row in target_rows if row["m11_support_warning"] == "false"]
            support_p, support_s = pooled(support_safe, candidate, "expected_gap_rmse_units")
            support_same_sign = primary_sign != 0 and sign(support_s) == primary_sign
            if int(summary["support_safe_row_count"]) != len(support_safe) or not close(num(summary, "support_safe_year_demeaned_pearson"), support_p) or not close(num(summary, "support_safe_year_demeaned_spearman"), support_s):
                errors.append(f"M14 support-safe association mismatch: {target}/{candidate}")
            if (summary["support_safe_same_sign"] == "true") != support_same_sign:
                errors.append(f"M14 support-safe sign mismatch: {target}/{candidate}")

            favorable_safe = [row for row in target_rows if row["gap_interpretation_authorized"] == "true"]
            favorable_p, favorable_s = pooled(favorable_safe, candidate, "favorable_peer_gap_rmse_units")
            if int(summary["favorable_peer_sensitivity_row_count"]) != len(favorable_safe) or not close(num(summary, "favorable_peer_sensitivity_year_demeaned_pearson"), favorable_p) or not close(num(summary, "favorable_peer_sensitivity_year_demeaned_spearman"), favorable_s):
                errors.append(f"M14 favorable-peer sensitivity mismatch: {target}/{candidate}")

            stable_flag = (
                abs(s) >= ABS_THRESHOLD
                and annual_same_sign >= MIN_ANNUAL_SIGN
                and loo_same_sign == 19
                and len(support_safe) >= MIN_SUPPORT_ROWS
                and support_same_sign
            )
            if (summary["stable_association_candidate"] == "true") != stable_flag:
                errors.append(f"M14 stable-candidate gate mismatch: {target}/{candidate}")
            if summary["p_value_selection_used"] != "false":
                errors.append(f"M14 p-value selection flag drift: {target}/{candidate}")
            for claim in ["causal_claim", "bottleneck_causal_claim", "policy_effect_claim", "monetary_wasted_potential_claim"]:
                if summary[claim] != "false":
                    errors.append(f"M14 forbidden association claim: {target}/{candidate}/{claim}")
            if stable_flag:
                expected_stable_keys.add((target, candidate))

    stable_keys = {(row["target_id"], row["candidate_id"]) for row in stable}
    if stable_keys != expected_stable_keys or len(stable) != len(expected_stable_keys):
        errors.append("M14 stable-candidate output does not exactly match locked gate")
    for row in stable:
        if row["stable_association_candidate"] != "true" or row["causal_bottleneck_interpretation_authorized"] != "false" or row["policy_priority_interpretation_authorized"] != "false":
            errors.append(f"M14 stable-candidate interpretation guardrail drift: {row['target_id']}/{row['candidate_id']}")

    if manifest.get("stable_association_candidate_count") != len(expected_stable_keys):
        errors.append("M14 stable-candidate manifest count drift")
    counts_target: dict[str, int] = {}
    counts_candidate: dict[str, int] = {}
    for target, candidate in expected_stable_keys:
        counts_target[target] = counts_target.get(target, 0) + 1
        counts_candidate[candidate] = counts_candidate.get(candidate, 0) + 1
    if manifest.get("stable_association_counts_by_target") != dict(sorted(counts_target.items())):
        errors.append("M14 stable target-count manifest drift")
    if manifest.get("stable_association_counts_by_candidate") != dict(sorted(counts_candidate.items())):
        errors.append("M14 stable candidate-count manifest drift")

    required_phrases = [
        "stable non-causal associations",
        "does not preregister a desired sign",
        "does not prove underemployment caused the gap",
        "do not establish event-day rainfall, flood causation, climate-change attribution, or station-observation equivalence",
        "does not automatically earn an M15 causal study",
    ]
    combined_text = spec + "\n" + (ROOT / "docs/MILESTONE14_BOTTLENECK_ASSOCIATION.md").read_text(encoding="utf-8") if (ROOT / "docs/MILESTONE14_BOTTLENECK_ASSOCIATION.md").exists() else spec
    for phrase in required_phrases:
        if phrase not in combined_text:
            errors.append(f"M14 guardrail text missing: {phrase}")

    return {
        "schema": "ranah-observatory/milestone14-audit/v1",
        "phase": "final_analytical_research_engine",
        "milestone": 14,
        "association_frame_row_count": len(frame),
        "feature_association_row_count": len(associations),
        "annual_correlation_row_count": len(annual),
        "loo_correlation_row_count": len(loo),
        "stable_association_candidate_count": len(stable),
        "stable_association_keys": [f"{target}:{candidate}" for target, candidate in sorted(expected_stable_keys)],
        "prefit_design_gate_preserved": gate.get("association_results_computed") is False and gate.get("association_results_inspected") is False,
        "m10_complete": m10.get("milestone10_complete") is True,
        "m13_complete": m13.get("milestone13_complete") is True,
        "causal_analysis_performed": manifest.get("causal_analysis_performed") is True,
        "bottleneck_causal_claim": manifest.get("bottleneck_causal_claim") is True,
        "policy_effect_claim": manifest.get("policy_effect_claim") is True,
        "milestone14_complete": manifest.get("milestone14_complete") is True and not errors,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Milestone 14 Bottleneck Association Engine")
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    report = audit()
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    print(text, end="")
    if report["errors"]:
        return 1
    if args.require_complete and report.get("milestone14_complete") is not True:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
