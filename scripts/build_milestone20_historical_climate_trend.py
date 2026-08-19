#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
OBS = ROOT / "data/processed/climate/rainfall/chirps-annual-rainfall-observations.csv"
SOURCE_MANIFEST = ROOT / "data/processed/climate/rainfall/chirps-rainfall-materialization.manifest.json"
GEO_REGISTRY = ROOT / "data/registries/geographies.csv"
DESIGN_GATE = ROOT / "data/manifests/milestone20_design_gate.json"
SPEC = ROOT / "research/MILESTONE20_HISTORICAL_CLIMATE_TREND_SPEC.md"
OUT_DIR = ROOT / "data/analysis/engine/historical_climate_trend_v1"
GEO_TRENDS_OUT = OUT_DIR / "m20-geography-trends.csv"
LOO_OUT = OUT_DIR / "m20-leave-one-year-out.csv"
REGIONAL_ANNUAL_OUT = OUT_DIR / "m20-regional-annual-mean.csv"
REGIONAL_TREND_OUT = OUT_DIR / "m20-regional-trend.csv"
MANIFEST_OUT = ROOT / "data/manifests/milestone20_historical_climate_trend.json"

FIRST_YEAR = 1981
LAST_YEAR = 2025
YEARS = list(range(FIRST_YEAR, LAST_YEAR + 1))
EARLY_YEARS = set(range(1981, 2003))
LATE_YEARS = set(range(2003, 2026))
ALPHA = 0.05
LOO_RETENTION_THRESHOLD = 0.90
SPATIAL_FRAME = "fixed_current_boundary_june_2026"
METHODOLOGY_VERSION = "chirps_v3_final_monthly_big_june_2026_fixed_boundary_v1"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normal_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def normal_ppf(p: float) -> float:
    # Peter J. Acklam's inverse-normal approximation; sufficient for deterministic CI ranks.
    if not 0.0 < p < 1.0:
        raise ValueError("normal_ppf requires 0 < p < 1")
    a = [
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    ]
    b = [
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    ]
    c = [
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    ]
    d = [
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    ]
    plow = 0.02425
    phigh = 1.0 - plow
    if p < plow:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q) + 1.0
        )
    if p > phigh:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q) + 1.0
        )
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (
        (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r) + 1.0
    )


def sign(value: float) -> int:
    return 1 if value > 0.0 else (-1 if value < 0.0 else 0)


def average_ranks(values: list[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda pair: (pair[1], pair[0]))
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i + 1
        while j < len(indexed) and indexed[j][1] == indexed[i][1]:
            j += 1
        average_rank = ((i + 1) + j) / 2.0
        for k in range(i, j):
            ranks[indexed[k][0]] = average_rank
        i = j
    return ranks


def mann_kendall(values: list[float]) -> dict[str, float]:
    n = len(values)
    if n < 3:
        raise ValueError("Mann-Kendall requires at least 3 observations")
    s = 0
    for i in range(n - 1):
        for j in range(i + 1, n):
            s += sign(values[j] - values[i])
    tie_counts = Counter(values)
    tie_term = sum(t * (t - 1) * (2 * t + 5) for t in tie_counts.values() if t > 1)
    var_s = (n * (n - 1) * (2 * n + 5) - tie_term) / 18.0
    if var_s <= 0.0:
        raise ValueError("non-positive Mann-Kendall variance")
    if s > 0:
        z = (s - 1.0) / math.sqrt(var_s)
    elif s < 0:
        z = (s + 1.0) / math.sqrt(var_s)
    else:
        z = 0.0
    p = min(1.0, max(0.0, 2.0 * (1.0 - normal_cdf(abs(z)))))
    tau = s / (0.5 * n * (n - 1))
    return {"s": float(s), "var_s": var_s, "z": z, "p": p, "tau": tau}


def pairwise_slopes(years: list[int], values: list[float]) -> list[float]:
    slopes: list[float] = []
    for i in range(len(values) - 1):
        for j in range(i + 1, len(values)):
            dx = years[j] - years[i]
            if dx <= 0:
                raise ValueError("years must be strictly increasing")
            slopes.append((values[j] - values[i]) / dx)
    slopes.sort()
    return slopes


def theil_sen(years: list[int], values: list[float], alpha: float = ALPHA) -> dict[str, float]:
    if len(years) != len(values) or len(values) < 3:
        raise ValueError("invalid Theil-Sen input")
    slopes = pairwise_slopes(years, values)
    slope = statistics.median(slopes)
    mk = mann_kendall(values)
    sigma = math.sqrt(mk["var_s"])
    z = normal_ppf(alpha / 2.0)  # negative
    nt = len(slopes)
    lower_index = max(int(round((nt + z * sigma) / 2.0)) - 1, 0)
    upper_index = min(int(round((nt - z * sigma) / 2.0)), nt - 1)
    low = slopes[lower_index]
    high = slopes[upper_index]
    intercept = statistics.median(values) - slope * statistics.median(years)
    return {"slope": slope, "intercept": intercept, "low": low, "high": high}


def autocorrelation(values: list[float], lag: int) -> float:
    n = len(values)
    if not 1 <= lag < n:
        raise ValueError("invalid autocorrelation lag")
    center = statistics.mean(values)
    denominator = sum((v - center) ** 2 for v in values)
    if denominator <= 1e-18:
        return 0.0
    numerator = sum((values[i] - center) * (values[i + lag] - center) for i in range(n - lag))
    return numerator / denominator


def hamed_rao_adjusted_mk(years: list[int], values: list[float], sen_slope: float) -> dict[str, Any]:
    mk = mann_kendall(values)
    detrended = [value - sen_slope * year for year, value in zip(years, values)]
    ranks = average_ranks(detrended)
    n = len(ranks)
    threshold = 1.96 / math.sqrt(n)
    lag_acf: dict[int, float] = {lag: autocorrelation(ranks, lag) for lag in range(1, n)}
    significant = {lag: rho for lag, rho in lag_acf.items() if abs(rho) > threshold}
    correction_sum = sum(
        (n - lag) * (n - lag - 1) * (n - lag - 2) * rho
        for lag, rho in significant.items()
    )
    variance_factor_raw = 1.0 + (2.0 / (n * (n - 1) * (n - 2))) * correction_sum
    variance_factor = max(variance_factor_raw, 1e-6)
    adjusted_var = mk["var_s"] * variance_factor
    s = mk["s"]
    if s > 0:
        z = (s - 1.0) / math.sqrt(adjusted_var)
    elif s < 0:
        z = (s + 1.0) / math.sqrt(adjusted_var)
    else:
        z = 0.0
    p = min(1.0, max(0.0, 2.0 * (1.0 - normal_cdf(abs(z)))))
    return {
        "s": s,
        "tau": mk["tau"],
        "classical_var_s": mk["var_s"],
        "classical_z": mk["z"],
        "classical_p": mk["p"],
        "variance_factor_raw": variance_factor_raw,
        "variance_factor": variance_factor,
        "significant_acf_lag_count": len(significant),
        "lag1_rank_acf": lag_acf.get(1, 0.0),
        "adjusted_var_s": adjusted_var,
        "adjusted_z": z,
        "adjusted_p": p,
    }


def holm_adjust(pairs: list[tuple[str, float]]) -> dict[str, float]:
    ordered = sorted(pairs, key=lambda item: (item[1], item[0]))
    m = len(ordered)
    adjusted: dict[str, float] = {}
    running = 0.0
    for i, (key, p) in enumerate(ordered):
        candidate = min(1.0, (m - i) * p)
        running = max(running, candidate)
        adjusted[key] = running
    return adjusted


def same_nonzero_direction(reference: float, candidate: float) -> bool:
    return sign(reference) != 0 and sign(candidate) == sign(reference)


def classify_trend(
    slope: float,
    ci_low: float,
    ci_high: float,
    adjusted_p: float,
    early_slope: float,
    late_slope: float,
    loo_retention: float,
) -> tuple[str, bool, bool, bool]:
    direction = sign(slope)
    ci_consistent = (ci_low > 0.0 and direction > 0) or (ci_high < 0.0 and direction < 0)
    split_consistent = same_nonzero_direction(slope, early_slope) and same_nonzero_direction(slope, late_slope)
    stable = loo_retention >= LOO_RETENTION_THRESHOLD
    authorized = adjusted_p < ALPHA and ci_consistent and split_consistent and stable
    if authorized and direction > 0:
        return "robust_monotonic_increase", True, ci_consistent, split_consistent
    if authorized and direction < 0:
        return "robust_monotonic_decrease", True, ci_consistent, split_consistent
    return "no_robust_monotonic_trend", False, ci_consistent, split_consistent


def validate_contract() -> tuple[dict[str, Any], dict[str, Any]]:
    source = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    gate = json.loads(DESIGN_GATE.read_text(encoding="utf-8"))
    expected_source = {
        "schema": "ranah-observatory/chirps-annual-rainfall/v1",
        "source_id": "chirps_v3",
        "indicator_id": "annual_rainfall",
        "claim_type": "model_estimate",
        "first_year": FIRST_YEAR,
        "last_year": LAST_YEAR,
        "geography_count": 19,
        "observation_count": 855,
        "methodology_version": METHODOLOGY_VERSION,
        "spatial_frame": SPATIAL_FRAME,
        "historical_boundary_continuity_claimed": False,
        "eligible_as_observed_station_data": False,
    }
    for key, expected in expected_source.items():
        if source.get(key) != expected:
            raise ValueError(f"M20 source contract drift: {key}={source.get(key)!r}, expected {expected!r}")
    if sha256(OBS) != source.get("observations_sha256"):
        raise ValueError("M20 CHIRPS observations sha256 drift")
    expected_gate = {
        "schema": "ranah-observatory/milestone20-design-gate/v1",
        "design_locked_before_model_fit": True,
        "first_year": FIRST_YEAR,
        "last_year": LAST_YEAR,
        "year_count": 45,
        "geography_count": 19,
        "observation_count": 855,
        "primary_slope_estimator": "theil_sen_median_pairwise_slope",
        "primary_trend_test": "hamed_rao_adjusted_mann_kendall",
        "multiple_testing_method": "holm_familywise",
        "multiple_testing_alpha": ALPHA,
        "leave_one_year_out_direction_retention_threshold": LOO_RETENTION_THRESHOLD,
        "posthoc_method_search_authorized": False,
    }
    for key, expected in expected_gate.items():
        if gate.get(key) != expected:
            raise ValueError(f"M20 design gate drift: {key}={gate.get(key)!r}, expected {expected!r}")
    return source, gate


def load_geography_names() -> dict[str, str]:
    rows = read_csv(GEO_REGISTRY)
    return {
        row["geography_id"]: row["canonical_name"]
        for row in rows
        if row.get("geography_id", "").startswith("idn.13.13") or row.get("geography_id", "").startswith("idn.13.137")
    }


def load_series() -> dict[str, list[tuple[int, float]]]:
    rows = read_csv(OBS)
    if len(rows) != 855:
        raise ValueError(f"M20 requires 855 rainfall observations, got {len(rows)}")
    series: dict[str, list[tuple[int, float]]] = defaultdict(list)
    seen: set[tuple[str, int]] = set()
    for row in rows:
        if row.get("indicator_id") != "annual_rainfall":
            raise ValueError("unexpected indicator in M20 source")
        if row.get("frequency") != "annual" or row.get("unit") != "millimetres":
            raise ValueError("unexpected frequency/unit in M20 source")
        if row.get("claim_type") != "model_estimate":
            raise ValueError("unexpected claim type in M20 source")
        if row.get("suppressed") != "false" or row.get("comparable") != "true":
            raise ValueError("M20 source contains suppressed/non-comparable row")
        if row.get("methodology_version") != METHODOLOGY_VERSION:
            raise ValueError("M20 methodology version drift")
        year = int(row["time_start"][:4])
        if row.get("time_start") != f"{year}-01-01" or row.get("time_end") != f"{year}-12-31":
            raise ValueError("M20 annual reference-period drift")
        geography_id = row["geography_id"]
        key = (geography_id, year)
        if key in seen:
            raise ValueError(f"duplicate M20 geography-year {key}")
        seen.add(key)
        value = float(row["value_numeric"])
        if not math.isfinite(value) or value <= 0.0:
            raise ValueError(f"invalid rainfall value for {key}: {value}")
        series[geography_id].append((year, value))
    if len(series) != 19:
        raise ValueError(f"M20 expects 19 geographies, got {len(series)}")
    for geography_id, points in series.items():
        points.sort()
        if [year for year, _ in points] != YEARS:
            raise ValueError(f"M20 incomplete 1981-2025 series for {geography_id}")
    return dict(sorted(series.items()))


def analyze_one(years: list[int], values: list[float]) -> dict[str, Any]:
    sen = theil_sen(years, values)
    mk = hamed_rao_adjusted_mk(years, values, sen["slope"])
    return {**sen, **mk}


def build_outputs() -> dict[str, Any]:
    source_manifest, gate = validate_contract()
    names = load_geography_names()
    series = load_series()

    prelim: list[dict[str, Any]] = []
    loo_rows: list[dict[str, Any]] = []
    for geography_id, points in series.items():
        years = [year for year, _ in points]
        values = [value for _, value in points]
        full = analyze_one(years, values)
        early_points = [(year, value) for year, value in points if year in EARLY_YEARS]
        late_points = [(year, value) for year, value in points if year in LATE_YEARS]
        early = theil_sen([y for y, _ in early_points], [v for _, v in early_points])
        late = theil_sen([y for y, _ in late_points], [v for _, v in late_points])
        reference_sign = sign(full["slope"])
        loo_slopes: list[float] = []
        same_count = 0
        for omitted_year in years:
            retained = [(year, value) for year, value in points if year != omitted_year]
            loo = theil_sen([y for y, _ in retained], [v for _, v in retained])
            loo_slope = loo["slope"]
            loo_slopes.append(loo_slope)
            same_direction = reference_sign != 0 and sign(loo_slope) == reference_sign
            same_count += int(same_direction)
            loo_rows.append(
                {
                    "geography_id": geography_id,
                    "geography_name": names.get(geography_id, geography_id),
                    "omitted_year": omitted_year,
                    "full_period_slope_mm_per_year": full["slope"],
                    "leave_one_year_out_slope_mm_per_year": loo_slope,
                    "same_direction_as_full": same_direction,
                }
            )
        loo_retention = same_count / len(years)
        prelim.append(
            {
                "geography_id": geography_id,
                "geography_name": names.get(geography_id, geography_id),
                "n_years": len(years),
                "start_year": years[0],
                "end_year": years[-1],
                "mean_rainfall_mm": statistics.mean(values),
                "median_rainfall_mm": statistics.median(values),
                "sen_slope_mm_per_year": full["slope"],
                "sen_slope_mm_per_decade": full["slope"] * 10.0,
                "sen_ci95_low_mm_per_year": full["low"],
                "sen_ci95_high_mm_per_year": full["high"],
                "mk_s": full["s"],
                "mk_tau": full["tau"],
                "mk_classical_z": full["classical_z"],
                "mk_classical_p": full["classical_p"],
                "hr_variance_factor_raw": full["variance_factor_raw"],
                "hr_variance_factor": full["variance_factor"],
                "hr_significant_acf_lag_count": full["significant_acf_lag_count"],
                "hr_lag1_rank_acf": full["lag1_rank_acf"],
                "hr_z": full["adjusted_z"],
                "hr_p": full["adjusted_p"],
                "early_sen_slope_mm_per_year": early["slope"],
                "late_sen_slope_mm_per_year": late["slope"],
                "loo_min_slope_mm_per_year": min(loo_slopes),
                "loo_max_slope_mm_per_year": max(loo_slopes),
                "loo_same_direction_retention": loo_retention,
            }
        )

    adjusted = holm_adjust([(row["geography_id"], float(row["hr_p"])) for row in prelim])
    geo_rows: list[dict[str, Any]] = []
    for row in prelim:
        holm_p = adjusted[row["geography_id"]]
        classification, authorized, ci_consistent, split_consistent = classify_trend(
            float(row["sen_slope_mm_per_year"]),
            float(row["sen_ci95_low_mm_per_year"]),
            float(row["sen_ci95_high_mm_per_year"]),
            holm_p,
            float(row["early_sen_slope_mm_per_year"]),
            float(row["late_sen_slope_mm_per_year"]),
            float(row["loo_same_direction_retention"]),
        )
        geo_rows.append(
            {
                **row,
                "hr_p_holm": holm_p,
                "ci_excludes_zero_same_direction": ci_consistent,
                "split_direction_consistent": split_consistent,
                "loo_stability_pass": float(row["loo_same_direction_retention"]) >= LOO_RETENTION_THRESHOLD,
                "robust_monotonic_classification": classification,
                "public_claim_authorized": authorized,
                "claim_type": "model_estimate",
                "station_observation_equivalence": False,
                "historical_boundary_continuity_claimed": False,
                "spatial_frame": SPATIAL_FRAME,
            }
        )

    regional_rows: list[dict[str, Any]] = []
    for year in YEARS:
        values = [dict(points)[year] for points in series.values()]
        regional_rows.append(
            {
                "analysis_year": year,
                "geography_count": len(values),
                "unweighted_mean_rainfall_mm": statistics.mean(values),
                "min_geography_rainfall_mm": min(values),
                "max_geography_rainfall_mm": max(values),
                "claim_type": "model_estimate_spatial_mean",
                "spatial_frame": SPATIAL_FRAME,
            }
        )
    regional_years = [int(row["analysis_year"]) for row in regional_rows]
    regional_values = [float(row["unweighted_mean_rainfall_mm"]) for row in regional_rows]
    regional_full = analyze_one(regional_years, regional_values)
    regional_early = theil_sen(
        [y for y in regional_years if y in EARLY_YEARS],
        [v for y, v in zip(regional_years, regional_values) if y in EARLY_YEARS],
    )
    regional_late = theil_sen(
        [y for y in regional_years if y in LATE_YEARS],
        [v for y, v in zip(regional_years, regional_values) if y in LATE_YEARS],
    )
    regional_loo_slopes: list[float] = []
    regional_same = 0
    for omitted in regional_years:
        yy = [y for y in regional_years if y != omitted]
        vv = [v for y, v in zip(regional_years, regional_values) if y != omitted]
        slope = theil_sen(yy, vv)["slope"]
        regional_loo_slopes.append(slope)
        regional_same += int(same_nonzero_direction(regional_full["slope"], slope))
    regional_retention = regional_same / len(regional_years)
    regional_classification, regional_authorized, regional_ci, regional_split = classify_trend(
        regional_full["slope"],
        regional_full["low"],
        regional_full["high"],
        regional_full["adjusted_p"],
        regional_early["slope"],
        regional_late["slope"],
        regional_retention,
    )
    regional_trend_rows = [
        {
            "series_id": "sumbar_current_boundary_unweighted_mean_rainfall",
            "n_years": 45,
            "start_year": FIRST_YEAR,
            "end_year": LAST_YEAR,
            "mean_rainfall_mm": statistics.mean(regional_values),
            "median_rainfall_mm": statistics.median(regional_values),
            "sen_slope_mm_per_year": regional_full["slope"],
            "sen_slope_mm_per_decade": regional_full["slope"] * 10.0,
            "sen_ci95_low_mm_per_year": regional_full["low"],
            "sen_ci95_high_mm_per_year": regional_full["high"],
            "mk_s": regional_full["s"],
            "mk_tau": regional_full["tau"],
            "mk_classical_z": regional_full["classical_z"],
            "mk_classical_p": regional_full["classical_p"],
            "hr_variance_factor_raw": regional_full["variance_factor_raw"],
            "hr_variance_factor": regional_full["variance_factor"],
            "hr_significant_acf_lag_count": regional_full["significant_acf_lag_count"],
            "hr_lag1_rank_acf": regional_full["lag1_rank_acf"],
            "hr_z": regional_full["adjusted_z"],
            "hr_p": regional_full["adjusted_p"],
            "early_sen_slope_mm_per_year": regional_early["slope"],
            "late_sen_slope_mm_per_year": regional_late["slope"],
            "loo_min_slope_mm_per_year": min(regional_loo_slopes),
            "loo_max_slope_mm_per_year": max(regional_loo_slopes),
            "loo_same_direction_retention": regional_retention,
            "ci_excludes_zero_same_direction": regional_ci,
            "split_direction_consistent": regional_split,
            "loo_stability_pass": regional_retention >= LOO_RETENTION_THRESHOLD,
            "robust_monotonic_classification": regional_classification,
            "public_claim_authorized": regional_authorized,
            "multiple_testing_correction": "not_applicable_single_regional_series",
            "claim_type": "model_estimate_spatial_mean",
            "station_observation_equivalence": False,
            "historical_boundary_continuity_claimed": False,
            "spatial_frame": SPATIAL_FRAME,
        }
    ]

    geo_fields = [
        "geography_id", "geography_name", "n_years", "start_year", "end_year",
        "mean_rainfall_mm", "median_rainfall_mm", "sen_slope_mm_per_year", "sen_slope_mm_per_decade",
        "sen_ci95_low_mm_per_year", "sen_ci95_high_mm_per_year", "mk_s", "mk_tau",
        "mk_classical_z", "mk_classical_p", "hr_variance_factor_raw", "hr_variance_factor",
        "hr_significant_acf_lag_count", "hr_lag1_rank_acf", "hr_z", "hr_p", "hr_p_holm",
        "early_sen_slope_mm_per_year", "late_sen_slope_mm_per_year", "loo_min_slope_mm_per_year",
        "loo_max_slope_mm_per_year", "loo_same_direction_retention", "ci_excludes_zero_same_direction",
        "split_direction_consistent", "loo_stability_pass", "robust_monotonic_classification",
        "public_claim_authorized", "claim_type", "station_observation_equivalence",
        "historical_boundary_continuity_claimed", "spatial_frame",
    ]
    loo_fields = [
        "geography_id", "geography_name", "omitted_year", "full_period_slope_mm_per_year",
        "leave_one_year_out_slope_mm_per_year", "same_direction_as_full",
    ]
    regional_annual_fields = [
        "analysis_year", "geography_count", "unweighted_mean_rainfall_mm", "min_geography_rainfall_mm",
        "max_geography_rainfall_mm", "claim_type", "spatial_frame",
    ]
    regional_trend_fields = list(regional_trend_rows[0].keys())

    write_csv(GEO_TRENDS_OUT, geo_fields, geo_rows)
    write_csv(LOO_OUT, loo_fields, loo_rows)
    write_csv(REGIONAL_ANNUAL_OUT, regional_annual_fields, regional_rows)
    write_csv(REGIONAL_TREND_OUT, regional_trend_fields, regional_trend_rows)

    robust_rows = [row for row in geo_rows if row["public_claim_authorized"]]
    manifest = {
        "schema": "ranah-observatory/milestone20-historical-climate-trend/v1",
        "milestone": 20,
        "phase": "post_phase2_historical_climate_evidence_expansion",
        "criterion": "robust long-run monotonic rainfall trend evidence with serial-dependence and multiplicity guardrails",
        "milestone20_complete": True,
        "source_observation_count": 855,
        "geography_count": 19,
        "year_count": 45,
        "first_year": FIRST_YEAR,
        "last_year": LAST_YEAR,
        "analysis_row_count": len(geo_rows),
        "leave_one_year_out_row_count": len(loo_rows),
        "robust_monotonic_geography_count": len(robust_rows),
        "robust_monotonic_geography_ids": [row["geography_id"] for row in robust_rows],
        "robust_monotonic_increase_count": sum(row["robust_monotonic_classification"] == "robust_monotonic_increase" for row in geo_rows),
        "robust_monotonic_decrease_count": sum(row["robust_monotonic_classification"] == "robust_monotonic_decrease" for row in geo_rows),
        "regional_robust_monotonic_classification": regional_classification,
        "regional_public_claim_authorized": regional_authorized,
        "primary_slope_estimator": "theil_sen_median_pairwise_slope",
        "primary_trend_test": "hamed_rao_adjusted_mann_kendall",
        "multiple_testing_method": "holm_familywise",
        "multiple_testing_alpha": ALPHA,
        "leave_one_year_out_direction_retention_threshold": LOO_RETENTION_THRESHOLD,
        "classical_mann_kendall_primary_for_claims": False,
        "climate_change_attribution_performed": False,
        "causal_analysis_performed": False,
        "station_observation_equivalence": False,
        "historical_boundary_continuity_claimed": False,
        "posthoc_method_search_performed": False,
        "inputs": {
            "observations": {"path": str(OBS.relative_to(ROOT)), "sha256": sha256(OBS)},
            "source_manifest": {"path": str(SOURCE_MANIFEST.relative_to(ROOT)), "sha256": sha256(SOURCE_MANIFEST)},
            "design_gate": {"path": str(DESIGN_GATE.relative_to(ROOT)), "sha256": sha256(DESIGN_GATE)},
            "spec": {"path": str(SPEC.relative_to(ROOT)), "sha256": sha256(SPEC)},
        },
        "outputs": {
            "geography_trends": {"path": str(GEO_TRENDS_OUT.relative_to(ROOT)), "sha256": sha256(GEO_TRENDS_OUT)},
            "leave_one_year_out": {"path": str(LOO_OUT.relative_to(ROOT)), "sha256": sha256(LOO_OUT)},
            "regional_annual_mean": {"path": str(REGIONAL_ANNUAL_OUT.relative_to(ROOT)), "sha256": sha256(REGIONAL_ANNUAL_OUT)},
            "regional_trend": {"path": str(REGIONAL_TREND_OUT.relative_to(ROOT)), "sha256": sha256(REGIONAL_TREND_OUT)},
        },
        "source_contract": {
            "source_id": source_manifest["source_id"],
            "claim_type": source_manifest["claim_type"],
            "methodology_version": source_manifest["methodology_version"],
            "spatial_frame": source_manifest["spatial_frame"],
            "independent_station_validation": source_manifest["independent_station_validation"],
        },
        "design_gate_schema": gate["schema"],
    }
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    manifest = build_outputs()
    print(json.dumps({
        "milestone20_complete": manifest["milestone20_complete"],
        "robust_monotonic_geography_count": manifest["robust_monotonic_geography_count"],
        "regional_robust_monotonic_classification": manifest["regional_robust_monotonic_classification"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
