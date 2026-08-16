#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OBSERVATIONS = ROOT / "data" / "processed" / "climate" / "rainfall" / "chirps-annual-rainfall-observations.csv"
DEFAULT_GEOGRAPHIES = ROOT / "data" / "registries" / "geographies.csv"
EXPECTED_METHOD = "chirps_v3_final_monthly_big_june_2026_fixed_boundary_v1"
EXPECTED_ROWS = 855
EXPECTED_GEOGRAPHIES = 19
EXPECTED_YEARS = set(range(1981, 2026))
COVERAGE_GATE = 0.995
YOY_REVIEW_THRESHOLD_PCT = 50.0
FOCUS_GEOGRAPHIES = ("idn.13.1377", "idn.13.1306", "idn.13.1371")
COVERAGE_RE = re.compile(r"(?:^|; )min_valid_area_fraction=([0-9.]+)(?:;|$)")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def percentile(values: list[float], q: float) -> float:
    if not values:
        raise ValueError("percentile requires at least one value")
    if not 0.0 <= q <= 1.0:
        raise ValueError("q must be in [0, 1]")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * q
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return ordered[low]
    fraction = position - low
    return ordered[low] * (1.0 - fraction) + ordered[high] * fraction


def current_sumbar_geographies(rows: list[dict[str, str]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in rows:
        if row.get("parent_geography_id") != "idn.13" or row.get("status") != "current":
            continue
        if row.get("geography_level") not in {"regency", "city"}:
            continue
        result[row["geography_id"]] = row["canonical_name"]
    if len(result) != EXPECTED_GEOGRAPHIES:
        raise ValueError(f"expected {EXPECTED_GEOGRAPHIES} current Sumbar geographies; got {len(result)}")
    return result


def parse_observations(rows: list[dict[str, str]], names: dict[str, str]) -> list[dict[str, Any]]:
    if len(rows) != EXPECTED_ROWS:
        raise ValueError(f"expected {EXPECTED_ROWS} frozen observations; got {len(rows)}")
    parsed: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for row in rows:
        if row.get("indicator_id") != "annual_rainfall":
            raise ValueError("non-rainfall row present in frozen rainfall baseline")
        if row.get("claim_type") != "model_estimate":
            raise ValueError("frozen CHIRPS rainfall must remain model_estimate")
        if row.get("methodology_version") != EXPECTED_METHOD:
            raise ValueError("unexpected frozen rainfall methodology version")
        gid = row["geography_id"]
        if gid not in names:
            raise ValueError(f"unexpected geography in rainfall baseline: {gid}")
        year = int(row["time_start"][:4])
        key = (gid, year)
        if key in seen:
            raise ValueError(f"duplicate frozen rainfall geography-year: {key}")
        seen.add(key)
        value = float(row["value_numeric"])
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"invalid rainfall value for {key}: {value}")
        match = COVERAGE_RE.search(row.get("notes", ""))
        if not match:
            raise ValueError(f"missing minimum coverage note for {key}")
        coverage = float(match.group(1))
        if not math.isfinite(coverage) or not 0.0 <= coverage <= 1.0:
            raise ValueError(f"invalid minimum coverage for {key}: {coverage}")
        parsed.append({
            "geography_id": gid,
            "geography_name": names[gid],
            "year": year,
            "rainfall_mm": value,
            "min_valid_area_fraction": coverage,
        })
    if {item["year"] for item in parsed} != EXPECTED_YEARS:
        raise ValueError("frozen rainfall year footprint is incomplete")
    if {item["geography_id"] for item in parsed} != set(names):
        raise ValueError("frozen rainfall geography footprint is incomplete")
    return parsed


def spatial_iqr_diagnostics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_year: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_year[row["year"]].append(row)
    flags: list[dict[str, Any]] = []
    for year in sorted(by_year):
        year_rows = by_year[year]
        values = [row["rainfall_mm"] for row in year_rows]
        q1 = percentile(values, 0.25)
        q3 = percentile(values, 0.75)
        iqr = q3 - q1
        low = q1 - 1.5 * iqr
        high = q3 + 1.5 * iqr
        for row in year_rows:
            if row["rainfall_mm"] < low or row["rainfall_mm"] > high:
                flags.append({
                    "year": year,
                    "geography_id": row["geography_id"],
                    "geography_name": row["geography_name"],
                    "rainfall_mm": round(row["rainfall_mm"], 6),
                    "lower_fence_mm": round(low, 6),
                    "upper_fence_mm": round(high, 6),
                })
    counts = Counter(flag["geography_id"] for flag in flags)
    return {
        "method": "Tukey IQR across 19 geographies within each year; descriptive review flag only",
        "flag_count": len(flags),
        "counts_by_geography": {
            gid: {"name": next(flag["geography_name"] for flag in flags if flag["geography_id"] == gid), "count": counts[gid]}
            for gid in sorted(counts)
        },
        "flags": flags,
    }


def yoy_diagnostics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_geo: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_geo[row["geography_id"]].append(row)
    all_changes: list[dict[str, Any]] = []
    maxima: list[dict[str, Any]] = []
    for gid, items in sorted(by_geo.items()):
        ordered = sorted(items, key=lambda item: item["year"])
        geo_changes: list[dict[str, Any]] = []
        for previous, current in zip(ordered, ordered[1:]):
            pct = (current["rainfall_mm"] / previous["rainfall_mm"] - 1.0) * 100.0
            record = {
                "geography_id": gid,
                "geography_name": current["geography_name"],
                "from_year": previous["year"],
                "to_year": current["year"],
                "from_mm": round(previous["rainfall_mm"], 6),
                "to_mm": round(current["rainfall_mm"], 6),
                "change_pct": round(pct, 6),
            }
            geo_changes.append(record)
            if abs(pct) >= YOY_REVIEW_THRESHOLD_PCT:
                all_changes.append(record)
        maxima.append(max(geo_changes, key=lambda item: abs(item["change_pct"])))
    transition_counts = Counter(f"{item['from_year']}->{item['to_year']}" for item in maxima)
    return {
        "review_threshold_pct": YOY_REVIEW_THRESHOLD_PCT,
        "flag_count": len(all_changes),
        "max_abs_change_by_geography": maxima,
        "max_transition_counts": dict(sorted(transition_counts.items())),
        "flags": all_changes,
    }


def transition_1997_1998(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_key = {(row["geography_id"], row["year"]): row for row in rows}
    changes: list[dict[str, Any]] = []
    for gid in sorted({row["geography_id"] for row in rows}):
        previous = by_key[(gid, 1997)]
        current = by_key[(gid, 1998)]
        pct = (current["rainfall_mm"] / previous["rainfall_mm"] - 1.0) * 100.0
        changes.append({
            "geography_id": gid,
            "geography_name": current["geography_name"],
            "rainfall_1997_mm": round(previous["rainfall_mm"], 6),
            "rainfall_1998_mm": round(current["rainfall_mm"], 6),
            "change_pct": round(pct, 6),
        })
    positive = [item for item in changes if item["change_pct"] > 0]
    values = [item["change_pct"] for item in changes]
    min_coverage = min(
        row["min_valid_area_fraction"] for row in rows if row["year"] in {1997, 1998}
    )
    directional_synchrony = len(positive) >= 18
    classification = (
        "plausible_regional_climate_signal_pending_independent_station_validation"
        if directional_synchrony and min_coverage >= COVERAGE_GATE
        else "unresolved_regional_transition"
    )
    return {
        "positive_geography_count": len(positive),
        "geography_count": len(changes),
        "positive_share": round(len(positive) / len(changes), 6),
        "minimum_change_pct": round(min(values), 6),
        "median_change_pct": round(percentile(values, 0.5), 6),
        "maximum_change_pct": round(max(values), 6),
        "minimum_coverage_1997_1998": min_coverage,
        "directionally_synchronous": directional_synchrony,
        "classification": classification,
        "classification_scope": "sanity review only; not causal attribution and not station validation",
        "changes": changes,
    }


def build_report(observation_rows: list[dict[str, str]], geography_rows: list[dict[str, str]]) -> dict[str, Any]:
    names = current_sumbar_geographies(geography_rows)
    parsed = parse_observations(observation_rows, names)
    spatial = spatial_iqr_diagnostics(parsed)
    yoy = yoy_diagnostics(parsed)
    transition = transition_1997_1998(parsed)
    coverage_min = min(row["min_valid_area_fraction"] for row in parsed)
    values = [row["rainfall_mm"] for row in parsed]
    focus_reviews = []
    for gid in FOCUS_GEOGRAPHIES:
        count = spatial["counts_by_geography"].get(gid, {}).get("count", 0)
        focus_reviews.append({
            "geography_id": gid,
            "geography_name": names[gid],
            "spatial_iqr_flag_count": count,
            "classification": (
                "unresolved_local_magnitude_pending_independent_station_validation"
                if count > 0 else "no_spatial_iqr_flag_in_frozen_series"
            ),
            "internal_processing_concern_detected": False,
        })
    return {
        "schema": "ranah-observatory/chirps-rainfall-sanity/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "baseline": {
            "claim_type": "model_estimate",
            "spatial_frame": "fixed_current_boundary_june_2026",
            "observation_count": len(parsed),
            "geography_count": len(names),
            "first_year": min(row["year"] for row in parsed),
            "last_year": max(row["year"] for row in parsed),
            "minimum_valid_area_fraction": coverage_min,
            "annual_rainfall_min_mm": round(min(values), 6),
            "annual_rainfall_max_mm": round(max(values), 6),
        },
        "diagnostics": {
            "spatial_iqr": spatial,
            "year_over_year": yoy,
            "transition_1997_1998": transition,
        },
        "review_classifications": {
            "regional_1997_1998": transition["classification"],
            "focus_local_magnitudes": focus_reviews,
            "independent_station_validation": "pending",
            "safe_to_upgrade_claim_type_to_observed": False,
        },
        "gates": {
            "frozen_footprint_complete": len(parsed) == EXPECTED_ROWS,
            "coverage_above_production_gate": coverage_min >= COVERAGE_GATE,
            "regional_1997_1998_directionally_synchronous": transition["directionally_synchronous"],
            "claim_type_remains_model_estimate": True,
            "station_validation_still_pending": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run bounded sanity diagnostics on the frozen CHIRPS rainfall baseline")
    parser.add_argument("--observations", type=Path, default=DEFAULT_OBSERVATIONS)
    parser.add_argument("--geographies", type=Path, default=DEFAULT_GEOGRAPHIES)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = build_report(read_csv(args.observations), read_csv(args.geographies))
    except (OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}")
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
