#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
M10_WIDE = ROOT / "data/analysis/engine/panel_v1/m10-panel-wide.csv"
M10_MANIFEST = ROOT / "data/manifests/milestone10_analytical_panel.json"
M13_GAP = ROOT / "data/analysis/engine/gap_decomposition_v1/m13-gap-panel.csv"
M13_MANIFEST = ROOT / "data/manifests/milestone13_development_gap_decomposition.json"
GATE = ROOT / "data/manifests/milestone14_design_gate.json"
SPEC = ROOT / "research/MILESTONE14_BOTTLENECK_ASSOCIATION_SPEC.md"
OUT_DIR = ROOT / "data/analysis/engine/bottleneck_association_v1"
FRAME_OUT = OUT_DIR / "m14-association-frame.csv"
ASSOC_OUT = OUT_DIR / "m14-feature-associations.csv"
YEAR_OUT = OUT_DIR / "m14-year-specific-correlations.csv"
LOO_OUT = OUT_DIR / "m14-leave-one-geography-out.csv"
STABLE_OUT = OUT_DIR / "m14-stable-association-candidates.csv"
MANIFEST_OUT = ROOT / "data/manifests/milestone14_bottleneck_association.json"

TARGETS = ["poverty_rate", "unemployment_rate", "real_grdp_growth"]
DIMENSIONS = {
    "poverty_rate": "living_standards_inclusion",
    "unemployment_rate": "labor_market",
    "real_grdp_growth": "economic_dynamism",
}
CANDIDATES = [
    "expected_years_schooling",
    "life_expectancy",
    "underemployment_rate",
    "annual_rainfall",
]
TARGET_YEARS = [2021, 2022, 2023, 2024]
FEATURE_YEARS = [2020, 2021, 2022, 2023]
ABS_SPEARMAN_THRESHOLD = 0.25
MIN_SAME_SIGN_ANNUAL = 3
MIN_SUPPORT_SAFE_ROWS = 40

CANDIDATE_DOMAINS = {
    "expected_years_schooling": "education_human_capital_aspiration",
    "life_expectancy": "health_human_development",
    "underemployment_rate": "labor_market_slack_quality",
    "annual_rainfall": "climate_context",
}
CANDIDATE_CLAIM_TYPES = {
    "expected_years_schooling": "observed",
    "life_expectancy": "observed",
    "underemployment_rate": "observed",
    "annual_rainfall": "model_estimate",
}


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def write_csv(path: Path, fieldnames: list[str], data: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in data:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def f(row: dict[str, Any], key: str) -> float:
    try:
        value = float(row[key])
    except (KeyError, TypeError, ValueError) as exc:
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
        raise ValueError("pearson requires at least three paired values")
    mx = mean(x)
    my = mean(y)
    sx = sum((value - mx) ** 2 for value in x)
    sy = sum((value - my) ** 2 for value in y)
    if sx <= 1e-18 or sy <= 1e-18:
        raise ValueError("pearson undefined for constant input")
    covariance = sum((a - mx) * (b - my) for a, b in zip(x, y))
    return covariance / math.sqrt(sx * sy)


def average_ranks(values: list[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda pair: pair[1])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i + 1
        while j < len(indexed) and indexed[j][1] == indexed[i][1]:
            j += 1
        rank = (i + 1 + j) / 2.0
        for position in range(i, j):
            ranks[indexed[position][0]] = rank
        i = j
    return ranks


def spearman(x: list[float], y: list[float]) -> float:
    return pearson(average_ranks(x), average_ranks(y))


def sign(value: float, eps: float = 1e-12) -> int:
    return 1 if value > eps else -1 if value < -eps else 0


def fmt(value: Any) -> Any:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, float):
        return f"{value:.12g}"
    return value


def validate_gate() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    m10 = json.loads(M10_MANIFEST.read_text(encoding="utf-8"))
    m13 = json.loads(M13_MANIFEST.read_text(encoding="utf-8"))
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    if m10.get("milestone10_complete") is not True or m13.get("milestone13_complete") is not True:
        raise ValueError("M14 requires complete M10 and M13")
    expected = {
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
        "stable_abs_spearman_threshold": ABS_SPEARMAN_THRESHOLD,
        "stable_min_same_sign_annual_count": MIN_SAME_SIGN_ANNUAL,
        "stable_require_all_loo_same_sign": True,
        "stable_min_support_safe_rows": MIN_SUPPORT_SAFE_ROWS,
        "stable_require_support_safe_same_sign": True,
        "p_value_selection_authorized": False,
        "candidate_selection_after_results_authorized": False,
        "association_results_computed": False,
        "association_results_inspected": False,
        "milestone14_complete": False,
    }
    for key, value in expected.items():
        if gate.get(key) != value:
            raise ValueError(f"M14 design-gate drift: {key}")
    return m10, m13, gate


def build_frame() -> tuple[list[dict[str, Any]], list[str]]:
    wide = rows(M10_WIDE)
    gap = rows(M13_GAP)
    wide_by = {(row["geography_id"], int(row["analysis_year"])): row for row in wide}
    geographies = sorted({row["geography_id"] for row in wide})
    if len(geographies) != 19:
        raise ValueError("M14 requires exact 19 M10 geographies")
    gap_by = {(row["target_id"], row["geography_id"], int(row["target_year"])): row for row in gap}

    output: list[dict[str, Any]] = []
    for target in TARGETS:
        for geography_id in geographies:
            for target_year in TARGET_YEARS:
                feature_year = target_year - 1
                gap_row = gap_by.get((target, geography_id, target_year))
                feature_row = wide_by.get((geography_id, feature_year))
                if gap_row is None or feature_row is None:
                    raise ValueError(f"M14 missing gap/feature row: {target}/{geography_id}/{target_year}")
                record: dict[str, Any] = {
                    "target_id": target,
                    "dimension_id": DIMENSIONS[target],
                    "geography_id": geography_id,
                    "geography_name": gap_row["geography_name"],
                    "target_year": target_year,
                    "feature_year": feature_year,
                    "expected_gap_rmse_units": f(gap_row, "expected_gap_rmse_units"),
                    "favorable_peer_gap_rmse_units": f(gap_row, "favorable_peer_gap_rmse_units"),
                    "m11_support_warning": gap_row["m11_support_warning"] == "true",
                    "gap_interpretation_authorized": gap_row["gap_interpretation_authorized"] == "true",
                    "expected_interval_classification": gap_row["expected_interval_classification"],
                }
                for candidate in CANDIDATES:
                    record[f"lag1_{candidate}"] = f(feature_row, candidate)
                output.append(record)
    if len(output) != 228:
        raise ValueError(f"M14 association frame must contain 228 rows, got {len(output)}")
    return output, geographies


def year_demeaned_pairs(data: list[dict[str, Any]], candidate: str, gap_field: str) -> tuple[list[float], list[float]]:
    by_year: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in data:
        by_year[int(row["target_year"])].append(row)
    xs: list[float] = []
    ys: list[float] = []
    for year in sorted(by_year):
        year_rows = by_year[year]
        candidate_values = [float(row[f"lag1_{candidate}"]) for row in year_rows]
        gap_values = [float(row[gap_field]) for row in year_rows]
        mx = mean(candidate_values)
        my = mean(gap_values)
        xs.extend(value - mx for value in candidate_values)
        ys.extend(value - my for value in gap_values)
    return xs, ys


def association(data: list[dict[str, Any]], candidate: str, gap_field: str) -> tuple[float, float]:
    x, y = year_demeaned_pairs(data, candidate, gap_field)
    return pearson(x, y), spearman(x, y)


def build_associations(frame: list[dict[str, Any]], geographies: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    associations: list[dict[str, Any]] = []
    annual_rows: list[dict[str, Any]] = []
    loo_rows: list[dict[str, Any]] = []
    stable_rows: list[dict[str, Any]] = []

    for target in TARGETS:
        target_rows = [row for row in frame if row["target_id"] == target]
        if len(target_rows) != 76:
            raise ValueError(f"M14 target frame must have 76 rows: {target}")
        for candidate in CANDIDATES:
            pooled_pearson, pooled_spearman = association(target_rows, candidate, "expected_gap_rmse_units")
            pooled_sign = sign(pooled_spearman)

            annual_spearman: list[float] = []
            annual_same_sign_count = 0
            for year in TARGET_YEARS:
                year_rows = [row for row in target_rows if int(row["target_year"]) == year]
                if len(year_rows) != 19:
                    raise ValueError("M14 annual association requires exact 19 geographies")
                xs = [float(row[f"lag1_{candidate}"]) for row in year_rows]
                ys = [float(row["expected_gap_rmse_units"]) for row in year_rows]
                year_pearson = pearson(xs, ys)
                year_spearman = spearman(xs, ys)
                annual_spearman.append(year_spearman)
                same_sign = pooled_sign != 0 and sign(year_spearman) == pooled_sign
                annual_same_sign_count += bool(same_sign)
                annual_rows.append({
                    "target_id": target,
                    "dimension_id": DIMENSIONS[target],
                    "candidate_id": candidate,
                    "candidate_domain": CANDIDATE_DOMAINS[candidate],
                    "target_year": year,
                    "feature_year": year - 1,
                    "row_count": len(year_rows),
                    "pearson": year_pearson,
                    "spearman": year_spearman,
                    "same_sign_as_primary_pooled_spearman": same_sign,
                    "claim_type": "derived_association_diagnostic",
                    "causal_claim": False,
                })

            loo_spearman: list[float] = []
            loo_same_sign_count = 0
            for excluded_geo in geographies:
                subset = [row for row in target_rows if row["geography_id"] != excluded_geo]
                if len(subset) != 72:
                    raise ValueError("M14 LOO subset must contain 72 rows")
                loo_pearson, loo_s = association(subset, candidate, "expected_gap_rmse_units")
                same_sign = pooled_sign != 0 and sign(loo_s) == pooled_sign
                loo_same_sign_count += bool(same_sign)
                loo_spearman.append(loo_s)
                loo_rows.append({
                    "target_id": target,
                    "dimension_id": DIMENSIONS[target],
                    "candidate_id": candidate,
                    "excluded_geography_id": excluded_geo,
                    "remaining_geography_count": 18,
                    "remaining_row_count": len(subset),
                    "year_demeaned_pearson": loo_pearson,
                    "year_demeaned_spearman": loo_s,
                    "same_sign_as_primary_pooled_spearman": same_sign,
                    "claim_type": "derived_association_diagnostic",
                    "causal_claim": False,
                })

            support_safe = [row for row in target_rows if not bool(row["m11_support_warning"])]
            support_safe_pearson, support_safe_spearman = association(support_safe, candidate, "expected_gap_rmse_units")
            support_same_sign = pooled_sign != 0 and sign(support_safe_spearman) == pooled_sign

            favorable_safe = [row for row in target_rows if bool(row["gap_interpretation_authorized"])]
            favorable_pearson, favorable_spearman = association(favorable_safe, candidate, "favorable_peer_gap_rmse_units")

            all_loo_same_sign = loo_same_sign_count == 19
            stable = (
                abs(pooled_spearman) >= ABS_SPEARMAN_THRESHOLD
                and annual_same_sign_count >= MIN_SAME_SIGN_ANNUAL
                and all_loo_same_sign
                and len(support_safe) >= MIN_SUPPORT_SAFE_ROWS
                and support_same_sign
            )
            direction = (
                "positive_association_with_adverse_gap"
                if pooled_sign > 0
                else "negative_association_with_adverse_gap"
                if pooled_sign < 0
                else "zero_direction"
            )
            association_row = {
                "target_id": target,
                "dimension_id": DIMENSIONS[target],
                "candidate_id": candidate,
                "candidate_domain": CANDIDATE_DOMAINS[candidate],
                "candidate_claim_type": CANDIDATE_CLAIM_TYPES[candidate],
                "primary_row_count": len(target_rows),
                "pooled_year_demeaned_pearson": pooled_pearson,
                "pooled_year_demeaned_spearman": pooled_spearman,
                "absolute_primary_spearman": abs(pooled_spearman),
                "association_direction": direction,
                "same_sign_annual_spearman_count": annual_same_sign_count,
                "annual_year_count": 4,
                "annual_spearman_min": min(annual_spearman),
                "annual_spearman_max": max(annual_spearman),
                "loo_spearman_min": min(loo_spearman),
                "loo_spearman_median": median(loo_spearman),
                "loo_spearman_max": max(loo_spearman),
                "loo_same_sign_count": loo_same_sign_count,
                "all_loo_same_sign": all_loo_same_sign,
                "support_safe_row_count": len(support_safe),
                "support_safe_year_demeaned_pearson": support_safe_pearson,
                "support_safe_year_demeaned_spearman": support_safe_spearman,
                "support_safe_same_sign": support_same_sign,
                "favorable_peer_sensitivity_row_count": len(favorable_safe),
                "favorable_peer_sensitivity_year_demeaned_pearson": favorable_pearson,
                "favorable_peer_sensitivity_year_demeaned_spearman": favorable_spearman,
                "stable_abs_spearman_threshold": ABS_SPEARMAN_THRESHOLD,
                "stable_min_same_sign_annual_count": MIN_SAME_SIGN_ANNUAL,
                "stable_require_all_loo_same_sign": True,
                "stable_min_support_safe_rows": MIN_SUPPORT_SAFE_ROWS,
                "stable_require_support_safe_same_sign": True,
                "stable_association_candidate": stable,
                "p_value_selection_used": False,
                "claim_type": "derived_association_diagnostic",
                "causal_claim": False,
                "bottleneck_causal_claim": False,
                "policy_effect_claim": False,
                "monetary_wasted_potential_claim": False,
            }
            associations.append(association_row)
            if stable:
                stable_rows.append({
                    "target_id": target,
                    "dimension_id": DIMENSIONS[target],
                    "candidate_id": candidate,
                    "candidate_domain": CANDIDATE_DOMAINS[candidate],
                    "candidate_claim_type": CANDIDATE_CLAIM_TYPES[candidate],
                    "association_direction": direction,
                    "pooled_year_demeaned_spearman": pooled_spearman,
                    "same_sign_annual_spearman_count": annual_same_sign_count,
                    "loo_spearman_min": min(loo_spearman),
                    "loo_spearman_max": max(loo_spearman),
                    "support_safe_row_count": len(support_safe),
                    "support_safe_year_demeaned_spearman": support_safe_spearman,
                    "favorable_peer_sensitivity_year_demeaned_spearman": favorable_spearman,
                    "stable_association_candidate": True,
                    "causal_bottleneck_interpretation_authorized": False,
                    "policy_priority_interpretation_authorized": False,
                    "claim_type": "derived_stable_association_candidate",
                })

    associations.sort(key=lambda row: (TARGETS.index(row["target_id"]), CANDIDATES.index(row["candidate_id"])))
    annual_rows.sort(key=lambda row: (TARGETS.index(row["target_id"]), CANDIDATES.index(row["candidate_id"]), int(row["target_year"])))
    loo_rows.sort(key=lambda row: (TARGETS.index(row["target_id"]), CANDIDATES.index(row["candidate_id"]), row["excluded_geography_id"]))
    stable_rows.sort(key=lambda row: (TARGETS.index(row["target_id"]), CANDIDATES.index(row["candidate_id"])))
    return associations, annual_rows, loo_rows, stable_rows


def build() -> dict[str, Any]:
    m10, m13, gate = validate_gate()
    frame, geographies = build_frame()
    associations, annual, loo, stable = build_associations(frame, geographies)

    frame_fields = [
        "target_id", "dimension_id", "geography_id", "geography_name", "target_year", "feature_year",
        "expected_gap_rmse_units", "favorable_peer_gap_rmse_units", "m11_support_warning",
        "gap_interpretation_authorized", "expected_interval_classification",
        *[f"lag1_{candidate}" for candidate in CANDIDATES],
    ]
    write_csv(FRAME_OUT, frame_fields, [{k: fmt(v) for k, v in row.items()} for row in frame])

    association_fields = [
        "target_id", "dimension_id", "candidate_id", "candidate_domain", "candidate_claim_type", "primary_row_count",
        "pooled_year_demeaned_pearson", "pooled_year_demeaned_spearman", "absolute_primary_spearman",
        "association_direction", "same_sign_annual_spearman_count", "annual_year_count", "annual_spearman_min",
        "annual_spearman_max", "loo_spearman_min", "loo_spearman_median", "loo_spearman_max", "loo_same_sign_count",
        "all_loo_same_sign", "support_safe_row_count", "support_safe_year_demeaned_pearson",
        "support_safe_year_demeaned_spearman", "support_safe_same_sign", "favorable_peer_sensitivity_row_count",
        "favorable_peer_sensitivity_year_demeaned_pearson", "favorable_peer_sensitivity_year_demeaned_spearman",
        "stable_abs_spearman_threshold", "stable_min_same_sign_annual_count", "stable_require_all_loo_same_sign",
        "stable_min_support_safe_rows", "stable_require_support_safe_same_sign", "stable_association_candidate",
        "p_value_selection_used", "claim_type", "causal_claim", "bottleneck_causal_claim", "policy_effect_claim",
        "monetary_wasted_potential_claim",
    ]
    write_csv(ASSOC_OUT, association_fields, [{k: fmt(v) for k, v in row.items()} for row in associations])

    annual_fields = [
        "target_id", "dimension_id", "candidate_id", "candidate_domain", "target_year", "feature_year", "row_count",
        "pearson", "spearman", "same_sign_as_primary_pooled_spearman", "claim_type", "causal_claim",
    ]
    write_csv(YEAR_OUT, annual_fields, [{k: fmt(v) for k, v in row.items()} for row in annual])

    loo_fields = [
        "target_id", "dimension_id", "candidate_id", "excluded_geography_id", "remaining_geography_count",
        "remaining_row_count", "year_demeaned_pearson", "year_demeaned_spearman",
        "same_sign_as_primary_pooled_spearman", "claim_type", "causal_claim",
    ]
    write_csv(LOO_OUT, loo_fields, [{k: fmt(v) for k, v in row.items()} for row in loo])

    stable_fields = [
        "target_id", "dimension_id", "candidate_id", "candidate_domain", "candidate_claim_type", "association_direction",
        "pooled_year_demeaned_spearman", "same_sign_annual_spearman_count", "loo_spearman_min", "loo_spearman_max",
        "support_safe_row_count", "support_safe_year_demeaned_spearman", "favorable_peer_sensitivity_year_demeaned_spearman",
        "stable_association_candidate", "causal_bottleneck_interpretation_authorized",
        "policy_priority_interpretation_authorized", "claim_type",
    ]
    write_csv(STABLE_OUT, stable_fields, [{k: fmt(v) for k, v in row.items()} for row in stable])

    stable_counts_by_target = Counter(row["target_id"] for row in stable)
    stable_counts_by_candidate = Counter(row["candidate_id"] for row in stable)
    manifest = {
        "schema": "ranah-observatory/milestone14-bottleneck-association/v1",
        "phase": "final_analytical_research_engine",
        "milestone": 14,
        "target_years": TARGET_YEARS,
        "feature_years": FEATURE_YEARS,
        "feature_lag_years": 1,
        "geography_count": 19,
        "target_ids": TARGETS,
        "candidate_ids": CANDIDATES,
        "association_frame_row_count": len(frame),
        "feature_association_row_count": len(associations),
        "annual_correlation_row_count": len(annual),
        "loo_correlation_row_count": len(loo),
        "stable_association_candidate_count": len(stable),
        "stable_association_counts_by_target": dict(sorted(stable_counts_by_target.items())),
        "stable_association_counts_by_candidate": dict(sorted(stable_counts_by_candidate.items())),
        "primary_gap_field": "expected_gap_rmse_units",
        "sensitivity_gap_field": "favorable_peer_gap_rmse_units",
        "primary_statistic": "pooled_year_demeaned_spearman",
        "secondary_statistic": "pooled_year_demeaned_pearson",
        "stable_abs_spearman_threshold": ABS_SPEARMAN_THRESHOLD,
        "stable_min_same_sign_annual_count": MIN_SAME_SIGN_ANNUAL,
        "stable_require_all_loo_same_sign": True,
        "stable_min_support_safe_rows": MIN_SUPPORT_SAFE_ROWS,
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
        "prefit_gate_preserved": (
            gate.get("association_results_computed") is False
            and gate.get("association_results_inspected") is False
        ),
        "source_inputs": {
            str(M10_WIDE.relative_to(ROOT)): sha256(M10_WIDE),
            str(M10_MANIFEST.relative_to(ROOT)): sha256(M10_MANIFEST),
            str(M13_GAP.relative_to(ROOT)): sha256(M13_GAP),
            str(M13_MANIFEST.relative_to(ROOT)): sha256(M13_MANIFEST),
            str(GATE.relative_to(ROOT)): sha256(GATE),
            str(SPEC.relative_to(ROOT)): sha256(SPEC),
        },
        "outputs": {
            "association_frame": {"path": str(FRAME_OUT.relative_to(ROOT)), "sha256": sha256(FRAME_OUT)},
            "feature_associations": {"path": str(ASSOC_OUT.relative_to(ROOT)), "sha256": sha256(ASSOC_OUT)},
            "year_specific_correlations": {"path": str(YEAR_OUT.relative_to(ROOT)), "sha256": sha256(YEAR_OUT)},
            "leave_one_geography_out": {"path": str(LOO_OUT.relative_to(ROOT)), "sha256": sha256(LOO_OUT)},
            "stable_association_candidates": {"path": str(STABLE_OUT.relative_to(ROOT)), "sha256": sha256(STABLE_OUT)},
        },
        "milestone14_complete": True,
    }
    MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return manifest


def main() -> int:
    build()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
