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
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
M10 = ROOT / "data/analysis/engine/panel_v1/m10-panel-wide.csv"
M13 = ROOT / "data/analysis/engine/gap_decomposition_v1/m13-gap-panel.csv"
OUT = ROOT / "data/analysis/engine/bottleneck_association_v1"
SCREEN = OUT / "m14-association-screen.csv"
GEO_LOO = OUT / "m14-geography-loo.csv"
YEAR_LOO = OUT / "m14-year-loo.csv"
FAV = OUT / "m14-favorable-peer-sensitivity.csv"
ADJ = OUT / "m14-outcome-adjacent-sensitivity.csv"
MANIFEST = ROOT / "data/manifests/milestone14_bottleneck_association.json"
SEED = 140014
PERMUTATIONS = 4999

META = {
    "expected_years_schooling": ("human_capital_forward_looking", "observed", "core"),
    "underemployment_rate": ("labor_utilization_stress", "observed", "core"),
    "annual_rainfall": ("hydroclimate_context", "model_estimate", "core"),
    "life_expectancy": ("health_capability", "observed", "health_extension"),
}
PAIRS = [
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
]
ADJ_PAIR = ("unemployment_rate", "underemployment_rate")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(f)]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def truth(value: str) -> bool:
    return value.lower() in {"1", "true", "yes"}


def avg_ranks(values: list[float]) -> list[float]:
    ordered = sorted(enumerate(values), key=lambda x: x[1])
    out = [0.0] * len(values)
    i = 0
    while i < len(ordered):
        j = i + 1
        while j < len(ordered) and ordered[j][1] == ordered[i][1]:
            j += 1
        rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            out[ordered[k][0]] = rank
        i = j
    return out


def pearson(x: list[float], y: list[float]) -> float:
    if len(x) < 3 or len(x) != len(y):
        return float("nan")
    mx, my = statistics.fmean(x), statistics.fmean(y)
    dx, dy = [v - mx for v in x], [v - my for v in y]
    sx, sy = math.sqrt(sum(v*v for v in dx)), math.sqrt(sum(v*v for v in dy))
    if sx == 0 or sy == 0:
        return float("nan")
    return sum(a*b for a, b in zip(dx, dy)) / (sx * sy)


def within_year_assoc(rows: list[dict[str, Any]], candidate: str, gap: str, *, ranked: bool) -> float:
    xx: list[float] = []
    yy: list[float] = []
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[int(row["target_year"])].append(row)
    for group in grouped.values():
        xv = [float(row[candidate]) for row in group]
        yv = [float(row[gap]) for row in group]
        if ranked:
            xv, yv = avg_ranks(xv), avg_ranks(yv)
        mx, my = statistics.fmean(xv), statistics.fmean(yv)
        xx.extend(v - mx for v in xv)
        yy.extend(v - my for v in yv)
    return pearson(xx, yy)


def sign(value: float) -> int:
    return 0 if not math.isfinite(value) or value == 0 else (1 if value > 0 else -1)


def joined_rows() -> list[dict[str, Any]]:
    panel = {(r["geography_id"], int(r["analysis_year"])): r for r in read_csv(M10)}
    out: list[dict[str, Any]] = []
    for gap in read_csv(M13):
        if not truth(gap["m11_benchmark_qualified"]):
            continue
        year = int(gap["target_year"])
        src = panel[(gap["geography_id"], year - 1)]
        row: dict[str, Any] = dict(gap)
        row.update({
            "target_year": year,
            "predictor_year": year - 1,
            "m11_support_warning_bool": truth(gap["m11_support_warning"]),
            "gap_interpretation_authorized_bool": truth(gap["gap_interpretation_authorized"]),
            "expected_gap_rmse_units": float(gap["expected_gap_rmse_units"]),
            "favorable_peer_gap_rmse_units": float(gap["favorable_peer_gap_rmse_units"]),
        })
        for candidate in META:
            value = src.get(candidate, "")
            row[candidate] = None if value == "" else float(value)
        out.append(row)
    return out


def select(rows: list[dict[str, Any]], target: str, candidate: str, *, support_clean: bool, favorable: bool = False) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        if row["target_id"] != target or row[candidate] is None:
            continue
        if support_clean and row["m11_support_warning_bool"]:
            continue
        if favorable and not row["gap_interpretation_authorized_bool"]:
            continue
        out.append(row)
    return out


def permutation_p(primary: list[dict[str, Any]], pool: list[dict[str, Any]], candidate: str, gap: str) -> tuple[float, float]:
    observed = within_year_assoc(primary, candidate, gap, ranked=True)
    geos = sorted({row["geography_id"] for row in pool})
    lookup = {(row["geography_id"], int(row["target_year"])): float(row[candidate]) for row in pool}
    required_years = {int(row["target_year"]) for row in primary}
    complete_geos = [g for g in geos if all((g, y) in lookup for y in required_years)]
    if set(complete_geos) != set(geos):
        raise RuntimeError(f"candidate pool incomplete for {candidate}: {len(complete_geos)}/{len(geos)} complete geographies")
    rng = random.Random(SEED + sum(map(ord, f"{primary[0]['target_id']}:{candidate}:{gap}")))
    extreme = 0
    for _ in range(PERMUTATIONS):
        shuffled = geos[:]
        rng.shuffle(shuffled)
        mapping = dict(zip(geos, shuffled))
        synthetic = []
        for row in primary:
            copy = dict(row)
            copy[candidate] = lookup[(mapping[row["geography_id"]], int(row["target_year"]))]
            synthetic.append(copy)
        value = within_year_assoc(synthetic, candidate, gap, ranked=True)
        if math.isfinite(value) and abs(value) >= abs(observed) - 1e-15:
            extreme += 1
    return observed, (extreme + 1) / (PERMUTATIONS + 1)


def loo(primary: list[dict[str, Any]], candidate: str, gap: str, key: str) -> tuple[list[dict[str, Any]], dict[str, float]]:
    full = within_year_assoc(primary, candidate, gap, ranked=True)
    full_sign = sign(full)
    values = sorted({row[key] for row in primary}, key=lambda x: str(x))
    output = []
    coeffs = []
    retained = 0
    for value in values:
        subset = [row for row in primary if row[key] != value]
        assoc = within_year_assoc(subset, candidate, gap, ranked=True)
        coeffs.append(assoc)
        same = full_sign != 0 and sign(assoc) == full_sign
        retained += int(same)
        output.append({
            "target_id": primary[0]["target_id"],
            "candidate_id": candidate,
            "gap_object": gap,
            f"excluded_{key}": value,
            "remaining_row_count": len(subset),
            "within_year_rank_association": assoc,
            "full_sample_sign_retained": same,
            "claim_scope": "association_stability_not_causal",
        })
    clean = sorted(v for v in coeffs if math.isfinite(v))
    return output, {
        "min": clean[0], "max": clean[-1], "median": statistics.median(clean),
        "sign_retention": retained / len(values), "count": len(values),
    }


def primary_record(rows: list[dict[str, Any]], target: str, candidate: str) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    primary = select(rows, target, candidate, support_clean=True)
    pool = select(rows, target, candidate, support_clean=False)
    rank_assoc, p = permutation_p(primary, pool, candidate, "expected_gap_rmse_units")
    geo_rows, geo = loo(primary, candidate, "expected_gap_rmse_units", "geography_id")
    year_rows, years = loo(primary, candidate, "expected_gap_rmse_units", "target_year")
    target_years = sorted({int(r["target_year"]) for r in primary})
    stable = (
        len(primary) >= 60 and len(target_years) >= 4 and abs(rank_assoc) >= 0.20 and p <= 0.10
        and geo["sign_retention"] >= 0.90 and years["sign_retention"] >= 0.80
    )
    domain, claim, screen_type = META[candidate]
    record = {
        "target_id": target, "candidate_id": candidate, "candidate_domain": domain,
        "candidate_claim_type": claim, "screen_type": screen_type, "candidate_lag_years": 1,
        "primary_row_count": len(primary), "primary_target_year_count": len(target_years),
        "primary_target_years": "|".join(map(str, target_years)),
        "primary_geography_count": len({r["geography_id"] for r in primary}),
        "within_year_pearson": within_year_assoc(primary, candidate, "expected_gap_rmse_units", ranked=False),
        "within_year_rank_association": rank_assoc,
        "geography_block_permutation_p_two_sided": p,
        "permutation_count": PERMUTATIONS, "permutation_seed": SEED,
        "geo_loo_min": geo["min"], "geo_loo_max": geo["max"], "geo_loo_median": geo["median"],
        "geo_loo_sign_retention": geo["sign_retention"],
        "year_loo_min": years["min"], "year_loo_max": years["max"], "year_loo_median": years["median"],
        "year_loo_sign_retention": years["sign_retention"],
        "all_benchmark_row_count": len(pool),
        "all_rows_within_year_rank_association": within_year_assoc(pool, candidate, "expected_gap_rmse_units", ranked=True),
        "stable_association_signal": stable,
        "association_direction": "higher_candidate_larger_adverse_gap" if rank_assoc > 0 else "higher_candidate_smaller_adverse_gap" if rank_assoc < 0 else "zero_or_undefined",
        "causal_claim": False, "policy_priority_claim": False, "monetary_wasted_potential_claim": False,
    }
    return record, geo_rows, year_rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise RuntimeError(f"empty output: {path}")
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader(); writer.writerows(rows)


def main() -> int:
    rows = joined_rows()
    screen: list[dict[str, Any]] = []
    geo_all: list[dict[str, Any]] = []
    year_all: list[dict[str, Any]] = []
    favorable = []
    for target, candidate in PAIRS:
        record, geo, years = primary_record(rows, target, candidate)
        screen.append(record); geo_all.extend(geo); year_all.extend(years)
        fav_rows = select(rows, target, candidate, support_clean=True, favorable=True)
        favorable.append({
            "target_id": target, "candidate_id": candidate, "row_count": len(fav_rows),
            "target_year_count": len({r["target_year"] for r in fav_rows}),
            "within_year_rank_association": within_year_assoc(fav_rows, candidate, "favorable_peer_gap_rmse_units", ranked=True) if fav_rows else float("nan"),
            "reference_type": "m12_ambitious_favorable_peer_reference",
            "can_replace_primary_expected_gap_screen": False, "causal_claim": False,
        })
    adj_target, adj_candidate = ADJ_PAIR
    adj_rows = select(rows, adj_target, adj_candidate, support_clean=True)
    adj_pool = select(rows, adj_target, adj_candidate, support_clean=False)
    adj_assoc, adj_p = permutation_p(adj_rows, adj_pool, adj_candidate, "expected_gap_rmse_units")
    adjacent = [{
        "target_id": adj_target, "candidate_id": adj_candidate, "row_count": len(adj_rows),
        "within_year_rank_association": adj_assoc, "geography_block_permutation_p_two_sided": adj_p,
        "outcome_adjacent": True, "stable_association_signal_authorized": False,
        "reason": "underemployment is a closely related labor-market outcome and excluded from the primary unemployment-gap screen",
        "causal_claim": False,
    }]

    screen.sort(key=lambda r: (r["target_id"], r["screen_type"], r["candidate_id"]))
    geo_all.sort(key=lambda r: (r["target_id"], r["candidate_id"], r["excluded_geography_id"]))
    year_all.sort(key=lambda r: (r["target_id"], r["candidate_id"], int(r["excluded_target_year"])))
    favorable.sort(key=lambda r: (r["target_id"], r["candidate_id"]))
    write_csv(SCREEN, screen); write_csv(GEO_LOO, geo_all); write_csv(YEAR_LOO, year_all); write_csv(FAV, favorable); write_csv(ADJ, adjacent)

    stable = [r for r in screen if r["stable_association_signal"]]
    manifest = {
        "schema": "ranah-observatory/milestone14-bottleneck-association/v1",
        "phase": "final_analytical_research_engine", "milestone": 14,
        "criterion": "stable association screening between lagged non-M11-primary candidates and M13 adverse expected-gap signals",
        "gap_object_primary": "m13_expected_gap_rmse_units",
        "positive_gap_semantics": "observed performance less favorable than M11 conditional expectation",
        "primary_pair_count": len(PAIRS), "core_pair_count": sum(r["screen_type"] == "core" for r in screen),
        "health_extension_pair_count": sum(r["screen_type"] == "health_extension" for r in screen),
        "stable_association_signal_count": len(stable),
        "stable_association_signals": [{k: r[k] for k in ("target_id", "candidate_id", "within_year_rank_association", "geography_block_permutation_p_two_sided", "association_direction")} for r in stable],
        "permutation_seed": SEED, "permutation_count": PERMUTATIONS,
        "classification_thresholds": {"abs_rank_association_min": 0.20, "permutation_p_max": 0.10, "geo_loo_sign_retention_min": 0.90, "year_loo_sign_retention_min": 0.80, "target_year_count_min": 4, "row_count_min": 60},
        "m11_primary_feature_reuse_in_primary_screen": False,
        "outcome_adjacent_underemployment_unemployment_primary_authorized": False,
        "shap_or_black_box_feature_importance_performed": False,
        "causal_analysis_performed": False, "policy_priority_claim_authorized": False,
        "technical_efficiency_claim_authorized": False, "monetary_wasted_potential_estimated": False,
        "inputs": {"m10_panel": {"path": str(M10.relative_to(ROOT)), "sha256": sha256(M10)}, "m13_gap_panel": {"path": str(M13.relative_to(ROOT)), "sha256": sha256(M13)}},
        "outputs": {
            "association_screen": {"path": str(SCREEN.relative_to(ROOT)), "sha256": sha256(SCREEN)},
            "geography_loo": {"path": str(GEO_LOO.relative_to(ROOT)), "sha256": sha256(GEO_LOO)},
            "year_loo": {"path": str(YEAR_LOO.relative_to(ROOT)), "sha256": sha256(YEAR_LOO)},
            "favorable_peer_sensitivity": {"path": str(FAV.relative_to(ROOT)), "sha256": sha256(FAV)},
            "outcome_adjacent_sensitivity": {"path": str(ADJ.relative_to(ROOT)), "sha256": sha256(ADJ)},
        },
        "milestone14_complete": True,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
