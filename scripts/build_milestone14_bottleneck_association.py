#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
M10 = ROOT / "data/analysis/engine/panel_v1/m10-panel-wide.csv"
M13 = ROOT / "data/analysis/engine/gap_decomposition_v1/m13-gap-panel.csv"
OUT_DIR = ROOT / "data/analysis/engine/bottleneck_association_v1"
SCREEN = OUT_DIR / "m14-association-screen.csv"
GEO_LOO = OUT_DIR / "m14-geography-loo.csv"
YEAR_LOO = OUT_DIR / "m14-year-loo.csv"
FAV = OUT_DIR / "m14-favorable-peer-sensitivity.csv"
ADJ = OUT_DIR / "m14-outcome-adjacent-sensitivity.csv"
MANIFEST = ROOT / "data/manifests/milestone14_bottleneck_association.json"

SEED = 140014
PERMUTATIONS = 4999

CANDIDATE_META: dict[str, dict[str, str]] = {
    "expected_years_schooling": {
        "candidate_domain": "human_capital_forward_looking",
        "claim_type": "observed",
        "screen_type": "core",
    },
    "underemployment_rate": {
        "candidate_domain": "labor_utilization_stress",
        "claim_type": "observed",
        "screen_type": "core",
    },
    "annual_rainfall": {
        "candidate_domain": "hydroclimate_context",
        "claim_type": "model_estimate",
        "screen_type": "core",
    },
    "life_expectancy": {
        "candidate_domain": "health_capability",
        "claim_type": "observed",
        "screen_type": "health_extension",
    },
}

PRIMARY_PAIRS: tuple[tuple[str, str], ...] = (
    ("poverty_rate", "expected_years_schooling"),
    ("poverty_rate", "underemployment_rate"),
    ("poverty_rate", "annual_rainfall"),
    ("unemployment_rate", "expected_years_schooling"),
    ("unemployment_rate", "annual_rainfall"),
    ("real_grdp_growth", "expected_years_schooling"),
    ("real_grdp_growth", "underemployment_rate"),
    ("real_grdp_growth", "annual_rainfall"),
    ("poverty_rate", "life_expectancy"),
    ("unemployment_rate", "life_expectancy"),
    ("real_grdp_growth", "life_expectancy"),
)

OUTCOME_ADJACENT_PAIR = ("unemployment_rate", "underemployment_rate")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes"}


def rank_average(values: list[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    pos = 0
    while pos < len(indexed):
        end = pos + 1
        while end < len(indexed) and indexed[end][1] == indexed[pos][1]:
            end += 1
        avg = (pos + 1 + end) / 2.0
        for cursor in range(pos, end):
            ranks[indexed[cursor][0]] = avg
        pos = end
    return ranks


def pearson(xs: list[float], ys: list[float]) -> float:
    if len(xs) != len(ys) or len(xs) < 3:
        return float("nan")
    mx = statistics.fmean(xs)
    my = statistics.fmean(ys)
    dx = [x - mx for x in xs]
    dy = [y - my for y in ys]
    sx = math.sqrt(sum(v * v for v in dx))
    sy = math.sqrt(sum(v * v for v in dy))
    if sx == 0.0 or sy == 0.0:
        return float("nan")
    return sum(a * b for a, b in zip(dx, dy)) / (sx * sy)


def within_year_pearson(rows: list[dict[str, Any]], candidate_key: str, gap_key: str) -> float:
    xs: list[float] = []
    ys: list[float] = []
    by_year: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_year[int(row["target_year"])].append(row)
    for year_rows in by_year.values():
        cx = statistics.fmean(float(row[candidate_key]) for row in year_rows)
        gy = statistics.fmean(float(row[gap_key]) for row in year_rows)
        xs.extend(float(row[candidate_key]) - cx for row in year_rows)
        ys.extend(float(row[gap_key]) - gy for row in year_rows)
    return pearson(xs, ys)


def within_year_rank_association(rows: list[dict[str, Any]], candidate_key: str, gap_key: str) -> float:
    xs: list[float] = []
    ys: list[float] = []
    by_year: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_year[int(row["target_year"])].append(row)
    for year_rows in by_year.values():
        candidate_ranks = rank_average([float(row[candidate_key]) for row in year_rows])
        gap_ranks = rank_average([float(row[gap_key]) for row in year_rows])
        mean_candidate_rank = statistics.fmean(candidate_ranks)
        mean_gap_rank = statistics.fmean(gap_ranks)
        xs.extend(value - mean_candidate_rank for value in candidate_ranks)
        ys.extend(value - mean_gap_rank for value in gap_ranks)
    return pearson(xs, ys)


def sign(value: float) -> int:
    if not math.isfinite(value) or value == 0.0:
        return 0
    return 1 if value > 0 else -1


def finite_summary(values: Iterable[float]) -> tuple[float, float, float]:
    clean = sorted(v for v in values if math.isfinite(v))
    if not clean:
        return float("nan"), float("nan"), float("nan")
    return clean[0], clean[-1], statistics.median(clean)


def build_joined_rows() -> list[dict[str, Any]]:
    panel_rows = read_csv(M10)
    panel: dict[tuple[str, int], dict[str, str]] = {
        (row["geography_id"], int(row["analysis_year"])): row for row in panel_rows
    }
    joined: list[dict[str, Any]] = []
    for gap in read_csv(M13):
        if not truthy(gap["m11_benchmark_qualified"]):
            continue
        target_year = int(gap["target_year"])
        predictor_year = target_year - 1
        source = panel.get((gap["geography_id"], predictor_year))
        if source is None:
            raise RuntimeError(f"missing M10 lag row for {gap['geography_id']} {predictor_year}")
        row: dict[str, Any] = dict(gap)
        row["target_year"] = target_year
        row["predictor_year"] = predictor_year
        row["m11_support_warning_bool"] = truthy(gap["m11_support_warning"])
        row["gap_interpretation_authorized_bool"] = truthy(gap["gap_interpretation_authorized"])
        row["expected_gap_rmse_units"] = float(gap["expected_gap_rmse_units"])
        row["favorable_peer_gap_rmse_units"] = float(gap["favorable_peer_gap_rmse_units"])
        for candidate in CANDIDATE_META:
            value = source.get(candidate, "")
            row[candidate] = None if value == "" else float(value)
        joined.append(row)
    return joined


def eligible_rows(joined: list[dict[str, Any]], target: str, candidate: str, *, support_clean: bool, gap_key: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in joined:
        if row["target_id"] != target:
            continue
        if support_clean and row["m11_support_warning_bool"]:
            continue
        if gap_key == "favorable_peer_gap_rmse_units" and not row["gap_interpretation_authorized_bool"]:
            continue
        if row[candidate] is None:
            continue
        rows.append(row)
    return rows


def permuted_rank_pvalue(rows: list[dict[str, Any]], candidate: str, gap_key: str) -> tuple[float, float]:
    observed = within_year_rank_association(rows, candidate, gap_key)
    if not math.isfinite(observed):
        return observed, float("nan")
    geographies = sorted({row["geography_id"] for row in rows})
    candidate_by_geo_year = {
        (row["geography_id"], int(row["target_year"])): float(row[candidate]) for row in rows
    }
    rng = random.Random(SEED + sum(ord(ch) for ch in f"{rows[0]['target_id']}:{candidate}:{gap_key}"))
    extreme = 0
    for _ in range(PERMUTATIONS):
        shuffled = geographies[:]
        rng.shuffle(shuffled)
        mapping = dict(zip(geographies, shuffled))
        synthetic: list[dict[str, Any]] = []
        valid = True
        for row in rows:
            key = (mapping[row["geography_id"]], int(row["target_year"]))
            candidate_value = candidate_by_geo_year.get(key)
            if candidate_value is None:
                valid = False
                break
            replacement = dict(row)
            replacement[candidate] = candidate_value
            synthetic.append(replacement)
        if not valid:
            continue
        value = within_year_rank_association(synthetic, candidate, gap_key)
        if math.isfinite(value) and abs(value) >= abs(observed) - 1e-15:
            extreme += 1
    return observed, (extreme + 1.0) / (PERMUTATIONS + 1.0)


def loo_diagnostics(rows: list[dict[str, Any]], candidate: str, gap_key: str, dimension: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    full = within_year_rank_association(rows, candidate, gap_key)
    full_sign = sign(full)
    keys = sorted({row[dimension] if dimension == "geography_id" else int(row[dimension]) for row in rows})
    out: list[dict[str, Any]] = []
    values: list[float] = []
    retained = 0
    for key in keys:
        subset = [row for row in rows if (row[dimension] if dimension == "geography_id" else int(row[dimension])) != key]
        value = within_year_rank_association(subset, candidate, gap_key)
        values.append(value)
        same_sign = sign(value) == full_sign and full_sign != 0
        retained += int(same_sign)
        out.append(
            {
                "target_id": rows[0]["target_id"],
                "candidate_id": candidate,
                "gap_object": gap_key,
                f"excluded_{dimension}": key,
                "remaining_row_count": len(subset),
                "within_year_rank_association": value,
                "full_sample_sign_retained": same_sign,
                "claim_scope": "association_stability_not_causal",
            }
        )
    minimum, maximum, median = finite_summary(values)
    return out, {
        "min": minimum,
        "max": maximum,
        "median": median,
        "sign_retention": retained / len(keys) if keys else float("nan"),
        "exclusion_count": len(keys),
    }


def association_record(joined: list[dict[str, Any]], target: str, candidate: str) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    primary = eligible_rows(joined, target, candidate, support_clean=True, gap_key="expected_gap_rmse_units")
    all_rows = eligible_rows(joined, target, candidate, support_clean=False, gap_key="expected_gap_rmse_units")
    if not primary:
        raise RuntimeError(f"no primary rows for {target} x {candidate}")
    observed_rank, permutation_p = permuted_rank_pvalue(primary, candidate, "expected_gap_rmse_units")
    geo_rows, geo_summary = loo_diagnostics(primary, candidate, "expected_gap_rmse_units", "geography_id")
    year_rows, year_summary = loo_diagnostics(primary, candidate, "expected_gap_rmse_units", "target_year")
    primary_years = sorted({int(row["target_year"]) for row in primary})
    stable = (
        len(primary) >= 60
        and len(primary_years) >= 4
        and math.isfinite(observed_rank)
        and abs(observed_rank) >= 0.20
        and math.isfinite(permutation_p)
        and permutation_p <= 0.10
        and geo_summary["sign_retention"] >= 0.90
        and year_summary["sign_retention"] >= 0.80
    )
    meta = CANDIDATE_META[candidate]
    return (
        {
            "target_id": target,
            "candidate_id": candidate,
            "candidate_domain": meta["candidate_domain"],
            "candidate_claim_type": meta["claim_type"],
            "screen_type": meta["screen_type"],
            "candidate_lag_years": 1,
            "primary_row_count": len(primary),
            "primary_target_year_count": len(primary_years),
            "primary_target_years": "|".join(str(year) for year in primary_years),
            "primary_geography_count": len({row["geography_id"] for row in primary}),
            "within_year_pearson": within_year_pearson(primary, candidate, "expected_gap_rmse_units"),
            "within_year_rank_association": observed_rank,
            "geography_block_permutation_p_two_sided": permutation_p,
            "permutation_count": PERMUTATIONS,
            "permutation_seed": SEED,
            "geo_loo_min": geo_summary["min"],
            "geo_loo_max": geo_summary["max"],
            "geo_loo_median": geo_summary["median"],
            "geo_loo_sign_retention": geo_summary["sign_retention"],
            "year_loo_min": year_summary["min"],
            "year_loo_max": year_summary["max"],
            "year_loo_median": year_summary["median"],
            "year_loo_sign_retention": year_summary["sign_retention"],
            "all_benchmark_row_count": len(all_rows),
            "all_rows_within_year_rank_association": within_year_rank_association(all_rows, candidate, "expected_gap_rmse_units"),
            "stable_association_signal": stable,
            "association_direction": "higher_candidate_larger_adverse_gap" if observed_rank > 0 else "higher_candidate_smaller_adverse_gap" if observed_rank < 0 else "zero_or_undefined",
            "causal_claim": False,
            "policy_priority_claim": False,
            "monetary_wasted_potential_claim": False,
        },
        geo_rows,
        year_rows,
    )


def favorable_record(joined: list[dict[str, Any]], target: str, candidate: str) -> dict[str, Any]:
    rows = eligible_rows(joined, target, candidate, support_clean=True, gap_key="favorable_peer_gap_rmse_units")
    value = within_year_rank_association(rows, candidate, "favorable_peer_gap_rmse_units") if rows else float("nan")
    return {
        "target_id": target,
        "candidate_id": candidate,
        "row_count": len(rows),
        "target_year_count": len({row["target_year"] for row in rows}),
        "within_year_rank_association": value,
        "reference_type": "m12_ambitious_favorable_peer_reference",
        "can_replace_primary_expected_gap_screen": False,
        "causal_claim": False,
    }


def adjacent_record(joined: list[dict[str, Any]]) -> dict[str, Any]:
    target, candidate = OUTCOME_ADJACENT_PAIR
    rows = eligible_rows(joined, target, candidate, support_clean=True, gap_key="expected_gap_rmse_units")
    value, pvalue = permuted_rank_pvalue(rows, candidate, "expected_gap_rmse_units")
    return {
        "target_id": target,
        "candidate_id": candidate,
        "row_count": len(rows),
        "within_year_rank_association": value,
        "geography_block_permutation_p_two_sided": pvalue,
        "outcome_adjacent": True,
        "stable_association_signal_authorized": False,
        "reason": "underemployment is a closely related labor-market outcome and is excluded from the primary unemployment-gap screen",
        "causal_claim": False,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise RuntimeError(f"refusing to write empty output {path}")
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    joined = build_joined_rows()
    screen_rows: list[dict[str, Any]] = []
    geo_rows: list[dict[str, Any]] = []
    year_rows: list[dict[str, Any]] = []
    favorable_rows: list[dict[str, Any]] = []
    for target, candidate in PRIMARY_PAIRS:
        record, geo, years = association_record(joined, target, candidate)
        screen_rows.append(record)
        geo_rows.extend(geo)
        year_rows.extend(years)
        favorable_rows.append(favorable_record(joined, target, candidate))

    screen_rows.sort(key=lambda row: (row["target_id"], row["screen_type"], row["candidate_id"]))
    geo_rows.sort(key=lambda row: (row["target_id"], row["candidate_id"], str(row["excluded_geography_id"])))
    year_rows.sort(key=lambda row: (row["target_id"], row["candidate_id"], int(row["excluded_target_year"])))
    favorable_rows.sort(key=lambda row: (row["target_id"], row["candidate_id"]))
    adjacent_rows = [adjacent_record(joined)]

    write_csv(SCREEN, screen_rows)
    write_csv(GEO_LOO, geo_rows)
    write_csv(YEAR_LOO, year_rows)
    write_csv(FAV, favorable_rows)
    write_csv(ADJ, adjacent_rows)

    stable_rows = [row for row in screen_rows if row["stable_association_signal"]]
    manifest = {
        "schema": "ranah-observatory/milestone14-bottleneck-association/v1",
        "phase": "final_analytical_research_engine",
        "milestone": 14,
        "criterion": "identify stable associations between structural/capability variables and development-gap signals without causal interpretation",
        "input_regime": "sumbar_current_kabkota_lagged_structural_2019_2024_v1",
        "gap_object_primary": "m13_expected_gap_rmse_units",
        "positive_gap_semantics": "observed performance less favorable than M11 conditional expectation",
        "primary_pair_count": len(PRIMARY_PAIRS),
        "core_pair_count": sum(1 for row in screen_rows if row["screen_type"] == "core"),
        "health_extension_pair_count": sum(1 for row in screen_rows if row["screen_type"] == "health_extension"),
        "stable_association_signal_count": len(stable_rows),
        "stable_association_signals": [
            {
                "target_id": row["target_id"],
                "candidate_id": row["candidate_id"],
                "within_year_rank_association": row["within_year_rank_association"],
                "permutation_p": row["geography_block_permutation_p_two_sided"],
                "association_direction": row["association_direction"],
            }
            for row in stable_rows
        ],
        "permutation_seed": SEED,
        "permutation_count": PERMUTATIONS,
        "classification_thresholds": {
            "abs_rank_association_min": 0.20,
            "permutation_p_max": 0.10,
            "geo_loo_sign_retention_min": 0.90,
            "year_loo_sign_retention_min": 0.80,
            "target_year_count_min": 4,
            "row_count_min": 60,
        },
        "m11_primary_feature_reuse_in_primary_screen": False,
        "outcome_adjacent_underemployment_unemployment_primary_authorized": False,
        "shap_or_black_box_feature_importance_performed": False,
        "causal_analysis_performed": False,
        "policy_priority_claim_authorized": False,
        "technical_efficiency_claim_authorized": False,
        "monetary_wasted_potential_estimated": False,
        "outputs": {
            "association_screen": {"path": str(SCREEN.relative_to(ROOT)), "sha256": sha256(SCREEN)},
            "geography_loo": {"path": str(GEO_LOO.relative_to(ROOT)), "sha256": sha256(GEO_LOO)},
            "year_loo": {"path": str(YEAR_LOO.relative_to(ROOT)), "sha256": sha256(YEAR_LOO)},
            "favorable_peer_sensitivity": {"path": str(FAV.relative_to(ROOT)), "sha256": sha256(FAV)},
            "outcome_adjacent_sensitivity": {"path": str(ADJ.relative_to(ROOT)), "sha256": sha256(ADJ)},
        },
        "inputs": {
            "m10_panel": {"path": str(M10.relative_to(ROOT)), "sha256": sha256(M10)},
            "m13_gap_panel": {"path": str(M13.relative_to(ROOT)), "sha256": sha256(M13)},
        },
        "milestone14_complete": True,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
