#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

EVENTS = ROOT / "data" / "registries" / "historical_geography_events.csv"
HISTORICAL_SOURCES = ROOT / "data" / "registries" / "historical_source_inventory.csv"
HISTORICAL_POPULATION = ROOT / "data" / "processed" / "bps" / "historical_population_source_native.csv"
BPS_OBSERVATIONS = ROOT / "data" / "processed" / "bps" / "panel" / "bps-canonical-observations.csv"
BPS_MANIFEST = ROOT / "data" / "processed" / "bps" / "panel" / "bps-canonical-panel.manifest.json"
CHIRPS_OBSERVATIONS = ROOT / "data" / "processed" / "climate" / "rainfall" / "chirps-annual-rainfall-observations.csv"
CHIRPS_MANIFEST = ROOT / "data" / "processed" / "climate" / "rainfall" / "chirps-rainfall-materialization.manifest.json"
GEOGRAPHIES = ROOT / "data" / "registries" / "geographies.csv"

DEFAULT_OUTPUT = ROOT / "data" / "analysis" / "historical"
DEFAULT_MANIFEST = ROOT / "data" / "manifests" / "milestone6_historical_eda.json"

MODERN_INDICATORS = {
    "poverty_rate": {"trend_qualified": True, "expected_start": 2018, "unit": "percent"},
    "real_grdp_growth": {"trend_qualified": True, "expected_start": 2018, "unit": "percent"},
    "mean_years_schooling": {"trend_qualified": True, "expected_start": 2018, "unit": "years"},
    "expected_years_schooling": {"trend_qualified": True, "expected_start": 2018, "unit": "years"},
    "life_expectancy": {"trend_qualified": True, "expected_start": 2020, "unit": "years"},
    "labor_force_participation": {"trend_qualified": False, "expected_start": 2018, "unit": "percent"},
    "unemployment_rate": {"trend_qualified": False, "expected_start": 2018, "unit": "percent"},
}

EXPECTED_HISTORICAL_EVENTS = {
    "sumatra_autonomy_1947",
    "sumatra_three_provinces_1948",
    "sumatera_tengah_1950",
    "sumbar_jambi_riau_1957",
    "sumbar_confirmation_1958",
    "census_boundary_warning_1961",
}
EXPECTED_GAPS = {"archive_gap_1945_1946", "archive_gap_1951_1960"}


class Milestone6Error(RuntimeError):
    pass


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def year_from_date(value: str) -> int:
    try:
        return int(value[:4])
    except (ValueError, TypeError) as exc:
        raise Milestone6Error(f"invalid date/year value {value!r}") from exc


def parse_number(value: str, label: str) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise Milestone6Error(f"non-numeric {label}: {value!r}") from exc
    if not math.isfinite(number):
        raise Milestone6Error(f"non-finite {label}: {value!r}")
    return number


def format_number(value: float) -> str:
    return format(value, ".12g")


def build_timeline() -> list[dict[str, Any]]:
    events = read_csv(EVENTS)
    by_id = {row["event_id"]: row for row in events}
    missing = EXPECTED_HISTORICAL_EVENTS - set(by_id)
    if missing:
        raise Milestone6Error("missing historical events: " + ", ".join(sorted(missing)))

    rows: list[dict[str, Any]] = []
    for event_id in sorted(EXPECTED_HISTORICAL_EVENTS, key=lambda item: (by_id[item]["event_date"][:4], item)):
        row = by_id[event_id]
        if row["evidence_status"] != "qualified":
            raise Milestone6Error(f"historical event {event_id} is not qualified")
        year = year_from_date(row["event_date"])
        rows.append(
            {
                "record_id": event_id,
                "record_type": "qualified_event",
                "reference_start": year,
                "reference_end": year,
                "date_or_range": row["event_date"],
                "date_precision": row["event_date_precision"],
                "subject": row["subject_name"],
                "evidence_state": "qualified",
                "claim_class": "qualitative_evidence",
                "analytical_implication": row["implication"],
                "source_id": row["source_id"],
                "source_locator": row["official_url"],
                "causal_claim": "false",
            }
        )

    source_rows = read_csv(HISTORICAL_SOURCES)
    source_by_id = {row["source_record_id"]: row for row in source_rows}
    for gap_id in sorted(EXPECTED_GAPS, key=lambda item: int(source_by_id.get(item, {}).get("reference_start", "9999"))):
        gap = source_by_id.get(gap_id)
        if not gap or gap["status"] != "gap":
            raise Milestone6Error(f"required historical gap {gap_id} is missing or not marked gap")
        rows.append(
            {
                "record_id": gap_id,
                "record_type": "explicit_gap",
                "reference_start": int(gap["reference_start"]),
                "reference_end": int(gap["reference_end"]),
                "date_or_range": f"{gap['reference_start']}-{gap['reference_end']}",
                "date_precision": "range",
                "subject": gap["title"],
                "evidence_state": "gap",
                "claim_class": "qualitative_evidence",
                "analytical_implication": gap["notes"],
                "source_id": gap["source_id"],
                "source_locator": "",
                "causal_claim": "false",
            }
        )
    rows.sort(key=lambda row: (int(row["reference_start"]), 0 if row["record_type"] == "explicit_gap" else 1, row["record_id"]))
    return rows


def build_historical_population_anchor() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = read_csv(HISTORICAL_POPULATION)
    target = [row for row in rows if row["bps_th_label"] == "1971" and row["bps_turvar_id"] == "34"]
    province = [
        row
        for row in target
        if row["canonical_geography_id"] == "idn.13.h1958"
        and row["mapping_status"] == "qualified_source_era"
    ]
    if len(province) != 1:
        raise Milestone6Error(f"expected one qualified 1971 source-era province anchor; got {len(province)}")
    province_row = province[0]
    province_value = parse_number(province_row["value"], "1971 province population")
    local = [row for row in target if row["mapping_status"] == "historical_geography_pending"]
    local_sum = sum(parse_number(row["value"], f"1971 local population {row['bps_vervar_id']}") for row in local)
    if len(local) != 14:
        raise Milestone6Error(f"expected 14 source-era local 1971 rows; got {len(local)}")
    if not math.isclose(local_sum, province_value, rel_tol=0.0, abs_tol=0.5):
        raise Milestone6Error(f"1971 local sum {local_sum} does not equal province total {province_value}")
    if any(row.get("canonical_geography_id") == "idn.13" for row in target):
        raise Milestone6Error("1971 source-era population must not be mapped to current idn.13")

    output = [
        {
            "indicator_id": "historical_population",
            "reference_year": 1971,
            "source_geography_id": "idn.13.h1958",
            "source_geography_label": province_row["bps_vervar_label"],
            "value_numeric": format_number(province_value),
            "unit": province_row["unit"],
            "claim_class": "observed_data",
            "reconstruction_state": province_row["reconstruction_state"],
            "mapping_status": province_row["mapping_status"],
            "local_source_row_count": len(local),
            "local_source_rows_sum": format_number(local_sum),
            "current_geography_bridge_allowed": "false",
            "source_snapshot": province_row["snapshot_path"],
            "source_snapshot_sha256": province_row["snapshot_sha256"],
            "notes": "Source-era province aggregate only; no automatic continuity or growth calculation to current idn.13.",
        }
    ]
    diagnostics = {
        "province_value": province_value,
        "local_count": len(local),
        "local_sum": local_sum,
        "source_snapshot_sha256": province_row["snapshot_sha256"],
    }
    return output, diagnostics


def build_modern_trajectory() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    rows = read_csv(BPS_OBSERVATIONS)
    selected = [
        row
        for row in rows
        if row["geography_id"] == "idn.13" and row["indicator_id"] in MODERN_INDICATORS
    ]
    by_indicator: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in selected:
        by_indicator[row["indicator_id"]].append(row)

    long_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    for indicator_id, contract in MODERN_INDICATORS.items():
        source = sorted(by_indicator.get(indicator_id, []), key=lambda row: row["time_start"])
        if not source:
            raise Milestone6Error(f"missing province-level modern series {indicator_id}")
        seen_years: set[int] = set()
        values: list[tuple[int, float, dict[str, str]]] = []
        for row in source:
            year = year_from_date(row["time_start"])
            if year in seen_years:
                raise Milestone6Error(f"duplicate {indicator_id} province observation for {year}")
            seen_years.add(year)
            value = parse_number(row["value_numeric"], f"{indicator_id} {year}")
            if row["unit"] != contract["unit"]:
                raise Milestone6Error(f"unit drift for {indicator_id} {year}: {row['unit']!r}")
            if contract["trend_qualified"] and row.get("comparable") != "true":
                raise Milestone6Error(
                    f"trend-qualified series {indicator_id} {year} is not source-marked comparable"
                )
            values.append((year, value, row))
            long_rows.append(
                {
                    "indicator_id": indicator_id,
                    "year": year,
                    "time_start": row["time_start"],
                    "time_end": row["time_end"],
                    "value_numeric": format_number(value),
                    "unit": row["unit"],
                    "claim_class": "observed_data",
                    "source_claim_type": row["claim_type"],
                    "source_comparable": row["comparable"],
                    "trend_qualified": str(bool(contract["trend_qualified"])).lower(),
                    "methodology_version": row["methodology_version"],
                    "price_basis": row["price_basis"],
                    "source_observation_id": row["observation_id"],
                    "source_provenance_id": row["provenance_id"],
                    "boundary_regime": "current_sumatera_barat_bps",
                    "causal_claim": "false",
                }
            )
        values.sort(key=lambda item: item[0])
        start_year, start_value, _ = values[0]
        end_year, end_value, _ = values[-1]
        minimum = min(values, key=lambda item: item[1])
        maximum = max(values, key=lambda item: item[1])
        expected_start = int(contract["expected_start"])
        if start_year != expected_start or end_year != 2025:
            raise Milestone6Error(
                f"{indicator_id} modern window drift: expected {expected_start}-2025, got {start_year}-{end_year}"
            )
        expected_count = 2025 - expected_start + 1
        if len(values) != expected_count:
            raise Milestone6Error(f"{indicator_id} expected {expected_count} annual rows; got {len(values)}")
        change_unit = "percentage_points" if contract["unit"] == "percent" else contract["unit"]
        summary_rows.append(
            {
                "indicator_id": indicator_id,
                "start_year": start_year,
                "end_year": end_year,
                "observation_count": len(values),
                "start_value": format_number(start_value),
                "end_value": format_number(end_value),
                "absolute_change": format_number(end_value - start_value),
                "absolute_change_unit": change_unit,
                "unit": contract["unit"],
                "minimum_year": minimum[0],
                "minimum_value": format_number(minimum[1]),
                "maximum_year": maximum[0],
                "maximum_value": format_number(maximum[1]),
                "endpoint_direction": "increase" if end_value > start_value else ("decrease" if end_value < start_value else "flat"),
                "trend_qualified": str(bool(contract["trend_qualified"])).lower(),
                "interpretation_rule": (
                    "descriptive endpoint/min/max only; no causal interpretation"
                    if contract["trend_qualified"]
                    else "context only; source cross-regime comparability remains unresolved"
                ),
            }
        )

    long_rows.sort(key=lambda row: (row["year"], row["indicator_id"]))
    summary_rows.sort(key=lambda row: row["indicator_id"])
    qualified = [row for row in summary_rows if row["trend_qualified"] == "true"]
    if len(qualified) < 5 or any(int(row["observation_count"]) < 6 for row in qualified):
        raise Milestone6Error("fewer than five modern trend-qualified series have at least six annual observations")

    diagnostic = {
        "series_count": len(summary_rows),
        "trend_qualified_count": len(qualified),
        "observation_count": len(long_rows),
    }
    return long_rows, summary_rows, diagnostic


def build_climate_diagnostics() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    manifest = json.loads(CHIRPS_MANIFEST.read_text(encoding="utf-8"))
    expected = {
        "claim_type": "model_estimate",
        "first_year": 1981,
        "last_year": 2025,
        "geography_count": 19,
        "observation_count": 855,
        "spatial_frame": "fixed_current_boundary_june_2026",
        "historical_boundary_continuity_claimed": False,
        "independent_station_validation": "pending",
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise Milestone6Error(f"CHIRPS manifest drift for {key}: {manifest.get(key)!r} != {value!r}")

    geo_rows = read_csv(GEOGRAPHIES)
    geo_names = {row["geography_id"]: row["canonical_name"] for row in geo_rows}
    observations = read_csv(CHIRPS_OBSERVATIONS)
    by_year: dict[int, list[tuple[str, float]]] = defaultdict(list)
    by_geo: dict[str, list[tuple[int, float]]] = defaultdict(list)
    for row in observations:
        if row["indicator_id"] != "annual_rainfall":
            raise Milestone6Error("unexpected indicator in frozen CHIRPS rainfall observations")
        if row["claim_type"] != "model_estimate":
            raise Milestone6Error("CHIRPS observation masquerades as non-model estimate")
        year = year_from_date(row["time_start"])
        value = parse_number(row["value_numeric"], f"rainfall {row['geography_id']} {year}")
        by_year[year].append((row["geography_id"], value))
        by_geo[row["geography_id"]].append((year, value))

    expected_years = set(range(1981, 2026))
    if set(by_year) != expected_years:
        raise Milestone6Error("CHIRPS year footprint is not exactly 1981-2025")
    if len(by_geo) != 19:
        raise Milestone6Error(f"expected 19 CHIRPS geographies; got {len(by_geo)}")

    yearly_rows: list[dict[str, Any]] = []
    for year in range(1981, 2026):
        items = by_year[year]
        if len(items) != 19 or len({geo for geo, _ in items}) != 19:
            raise Milestone6Error(f"CHIRPS {year} does not contain exactly 19 unique geographies")
        values = [value for _, value in items]
        yearly_rows.append(
            {
                "year": year,
                "geography_count": len(values),
                "mean_annual_rainfall_mm": format_number(statistics.fmean(values)),
                "median_annual_rainfall_mm": format_number(statistics.median(values)),
                "minimum_annual_rainfall_mm": format_number(min(values)),
                "maximum_annual_rainfall_mm": format_number(max(values)),
                "claim_class": "model_estimate",
                "spatial_frame": manifest["spatial_frame"],
                "historical_boundary_continuity_claimed": "false",
                "independent_station_validation": manifest["independent_station_validation"],
                "causal_claim": "false",
            }
        )

    signal_rows: list[dict[str, Any]] = []
    transition_counter: Counter[str] = Counter()
    pct_changes_1997_1998: list[float] = []
    for geography_id in sorted(by_geo):
        values = sorted(by_geo[geography_id])
        if [year for year, _ in values] != list(range(1981, 2026)):
            raise Milestone6Error(f"incomplete CHIRPS trajectory for {geography_id}")
        value_by_year = dict(values)
        pct_9798 = (value_by_year[1998] / value_by_year[1997] - 1.0) * 100.0
        pct_changes_1997_1998.append(pct_9798)
        yoy: list[tuple[float, int, int, float]] = []
        for (prior_year, prior), (year, value) in zip(values, values[1:]):
            pct = (value / prior - 1.0) * 100.0
            yoy.append((abs(pct), prior_year, year, pct))
        _, prior_year, year, max_pct = max(yoy, key=lambda item: item[0])
        transition = f"{prior_year}->{year}"
        transition_counter[transition] += 1
        signal_rows.append(
            {
                "geography_id": geography_id,
                "geography_name": geo_names.get(geography_id, geography_id),
                "rainfall_1997_mm": format_number(value_by_year[1997]),
                "rainfall_1998_mm": format_number(value_by_year[1998]),
                "change_1997_to_1998_percent": format_number(pct_9798),
                "wetter_in_1998": str(pct_9798 > 0).lower(),
                "maximum_absolute_yoy_transition": transition,
                "maximum_yoy_change_percent": format_number(max_pct),
                "claim_class": "model_estimate",
                "spatial_frame": manifest["spatial_frame"],
                "historical_boundary_continuity_claimed": "false",
                "independent_station_validation": manifest["independent_station_validation"],
                "causal_claim": "false",
            }
        )

    all_wetter = all(value > 0 for value in pct_changes_1997_1998)
    if not all_wetter:
        raise Milestone6Error("expected frozen CHIRPS sanity signal: not all 19 geographies are wetter in 1998 than 1997")

    diagnostic = {
        "year_count": len(yearly_rows),
        "geography_count": len(signal_rows),
        "all_19_wetter_1998_vs_1997": all_wetter,
        "change_1997_to_1998_percent_min": min(pct_changes_1997_1998),
        "change_1997_to_1998_percent_max": max(pct_changes_1997_1998),
        "dominant_max_yoy_transition": transition_counter.most_common(1)[0][0],
        "dominant_max_yoy_transition_geography_count": transition_counter.most_common(1)[0][1],
    }
    return yearly_rows, signal_rows, diagnostic


def build_findings(
    timeline: list[dict[str, Any]],
    historical_population: list[dict[str, Any]],
    modern_summary: list[dict[str, Any]],
    climate_diagnostic: dict[str, Any],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    event_1957 = next(row for row in timeline if row["record_id"] == "sumbar_jambi_riau_1957")
    findings.append(
        {
            "finding_id": "m6_boundary_discontinuity_1957",
            "finding_type": "boundary_constraint",
            "claim_class": "qualitative_evidence",
            "statement": "The 1957 Sumatera Tengah reorganization is an analytical boundary break; earlier Sumatera Tengah observations cannot be concatenated directly with later Sumatera Barat.",
            "source_paths": "data/registries/historical_geography_events.csv",
            "boundary_regime": "source_era",
            "causal_claim": "false",
            "status": "qualified_constraint",
        }
    )
    if event_1957["evidence_state"] != "qualified":
        raise Milestone6Error("1957 boundary finding lacks qualified evidence")

    pop = historical_population[0]
    findings.append(
        {
            "finding_id": "m6_population_1971_anchor",
            "finding_type": "historical_anchor",
            "claim_class": "observed_data",
            "statement": f"The qualified 1971 source-era Sumatera Barat population anchor is {int(float(pop['value_numeric'])):,} persons; its 14 local source-era rows sum exactly to the province total.",
            "source_paths": "data/processed/bps/historical_population_source_native.csv",
            "boundary_regime": "idn.13.h1958_source_era",
            "causal_claim": "false",
            "status": "qualified_anchor",
        }
    )

    findings.append(
        {
            "finding_id": "m6_climate_1997_1998_signal",
            "finding_type": "climate_diagnostic",
            "claim_class": "model_estimate",
            "statement": (
                "Within the fixed June 2026 current-boundary CHIRPS frame, all 19 kabupaten/kota are wetter in 1998 than 1997; "
                f"the geography-level increase ranges from {climate_diagnostic['change_1997_to_1998_percent_min']:.2f}% "
                f"to {climate_diagnostic['change_1997_to_1998_percent_max']:.2f}%. This is a descriptive regional signal, not a station observation or causal ENSO estimate."
            ),
            "source_paths": "data/processed/climate/rainfall/chirps-annual-rainfall-observations.csv|data/processed/climate/rainfall/chirps-rainfall-materialization.manifest.json",
            "boundary_regime": "fixed_current_boundary_june_2026",
            "causal_claim": "false",
            "status": "descriptive_signal_pending_station_validation",
        }
    )

    for row in modern_summary:
        if row["trend_qualified"] != "true":
            continue
        findings.append(
            {
                "finding_id": f"m6_modern_{row['indicator_id']}_endpoint",
                "finding_type": "modern_descriptive_trend",
                "claim_class": "derived_statistic",
                "statement": (
                    f"{row['indicator_id']} changes from {row['start_value']} {row['unit']} in {row['start_year']} "
                    f"to {row['end_value']} {row['unit']} in {row['end_year']} "
                    f"({row['endpoint_direction']}; absolute change {row['absolute_change']} {row['absolute_change_unit'].replace('_', ' ')})."
                ),
                "source_paths": "data/processed/bps/panel/bps-canonical-observations.csv",
                "boundary_regime": "current_sumatera_barat_bps",
                "causal_claim": "false",
                "status": "descriptive_only",
            }
        )

    grdp = next(row for row in modern_summary if row["indicator_id"] == "real_grdp_growth")
    if int(grdp["minimum_year"]) == 2020 and float(grdp["minimum_value"]) < 0:
        findings.append(
            {
                "finding_id": "m6_grdp_2020_contraction",
                "finding_type": "turning_point",
                "claim_class": "derived_statistic",
                "statement": (
                    f"Within the 2018-2025 BPS ADHK 2010 series, 2020 is the minimum annual real GRDP growth observation at {grdp['minimum_value']} percent. "
                    "The EDA records the timing and magnitude only and does not assign a cause."
                ),
                "source_paths": "data/processed/bps/panel/bps-canonical-observations.csv",
                "boundary_regime": "current_sumatera_barat_bps",
                "causal_claim": "false",
                "status": "descriptive_turning_point",
            }
        )
    return findings


def build(output_dir: Path, manifest_path: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)

    timeline = build_timeline()
    historical_population, population_diag = build_historical_population_anchor()
    modern_long, modern_summary, modern_diag = build_modern_trajectory()
    climate_yearly, climate_signals, climate_diag = build_climate_diagnostics()
    findings = build_findings(timeline, historical_population, modern_summary, climate_diag)

    files = {
        "timeline": output_dir / "west-sumatra-source-era-timeline.csv",
        "historical_population_anchor": output_dir / "west-sumatra-1971-population-anchor.csv",
        "modern_trajectory": output_dir / "west-sumatra-modern-trajectory-2018-2025.csv",
        "modern_summary": output_dir / "west-sumatra-modern-trend-summary.csv",
        "climate_yearly": output_dir / "west-sumatra-chirps-regional-year-summary.csv",
        "climate_signals": output_dir / "west-sumatra-chirps-geography-signals.csv",
        "findings": output_dir / "west-sumatra-exploratory-findings.csv",
    }

    write_csv(
        files["timeline"],
        [
            "record_id", "record_type", "reference_start", "reference_end", "date_or_range", "date_precision",
            "subject", "evidence_state", "claim_class", "analytical_implication", "source_id", "source_locator", "causal_claim",
        ],
        timeline,
    )
    write_csv(
        files["historical_population_anchor"],
        [
            "indicator_id", "reference_year", "source_geography_id", "source_geography_label", "value_numeric", "unit",
            "claim_class", "reconstruction_state", "mapping_status", "local_source_row_count", "local_source_rows_sum",
            "current_geography_bridge_allowed", "source_snapshot", "source_snapshot_sha256", "notes",
        ],
        historical_population,
    )
    write_csv(
        files["modern_trajectory"],
        [
            "indicator_id", "year", "time_start", "time_end", "value_numeric", "unit", "claim_class",
            "source_claim_type", "source_comparable", "trend_qualified", "methodology_version", "price_basis",
            "source_observation_id", "source_provenance_id", "boundary_regime", "causal_claim",
        ],
        modern_long,
    )
    write_csv(
        files["modern_summary"],
        [
            "indicator_id", "start_year", "end_year", "observation_count", "start_value", "end_value",
            "absolute_change", "absolute_change_unit", "unit", "minimum_year", "minimum_value", "maximum_year", "maximum_value",
            "endpoint_direction", "trend_qualified", "interpretation_rule",
        ],
        modern_summary,
    )
    write_csv(
        files["climate_yearly"],
        [
            "year", "geography_count", "mean_annual_rainfall_mm", "median_annual_rainfall_mm",
            "minimum_annual_rainfall_mm", "maximum_annual_rainfall_mm", "claim_class", "spatial_frame",
            "historical_boundary_continuity_claimed", "independent_station_validation", "causal_claim",
        ],
        climate_yearly,
    )
    write_csv(
        files["climate_signals"],
        [
            "geography_id", "geography_name", "rainfall_1997_mm", "rainfall_1998_mm",
            "change_1997_to_1998_percent", "wetter_in_1998", "maximum_absolute_yoy_transition",
            "maximum_yoy_change_percent", "claim_class", "spatial_frame", "historical_boundary_continuity_claimed",
            "independent_station_validation", "causal_claim",
        ],
        climate_signals,
    )
    write_csv(
        files["findings"],
        [
            "finding_id", "finding_type", "claim_class", "statement", "source_paths", "boundary_regime",
            "causal_claim", "status",
        ],
        findings,
    )

    source_files = {
        "historical_geography_events": EVENTS,
        "historical_source_inventory": HISTORICAL_SOURCES,
        "historical_population_source_native": HISTORICAL_POPULATION,
        "bps_canonical_observations": BPS_OBSERVATIONS,
        "bps_canonical_manifest": BPS_MANIFEST,
        "chirps_observations": CHIRPS_OBSERVATIONS,
        "chirps_manifest": CHIRPS_MANIFEST,
        "geographies": GEOGRAPHIES,
    }
    manifest = {
        "schema": "ranah-observatory/milestone6-historical-eda/v1",
        "criterion": "exploratory historical analysis",
        "scope": "segmented_evidence_regimes_no_historical_boundary_harmonization",
        "milestone6_complete": True,
        "causal_analysis_performed": False,
        "frontier_or_expected_performance_model_performed": False,
        "historical_current_geography_bridge_performed": False,
        "timeline_row_count": len(timeline),
        "explicit_gap_count": sum(row["record_type"] == "explicit_gap" for row in timeline),
        "historical_population_anchor_count": len(historical_population),
        "historical_population_1971": population_diag,
        "modern": modern_diag,
        "climate": climate_diag,
        "finding_count": len(findings),
        "source_sha256": {name: sha256_file(path) for name, path in source_files.items()},
        "output_files": {name: path.relative_to(ROOT).as_posix() for name, path in files.items()},
        "output_sha256": {name: sha256_file(path) for name, path in files.items()},
        "methodological_constraints": [
            "Do not concatenate Sumatera Tengah, idn.13.h1958, and current idn.13 without an explicit reconstruction.",
            "Do not calculate 1971-to-current population growth from the source-era anchor.",
            "CHIRPS 1981-2025 is a model-estimate diagnostic on fixed June 2026 current boundaries, not historical boundary reconstruction.",
            "Modern BPS summaries are descriptive; labor-force series remain contextual where source cross-regime comparability is unresolved.",
            "No causal attribution, frontier modelling, or wasted-potential estimation is performed in Milestone 6.",
        ],
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the segmented Milestone 6 exploratory historical analysis.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    try:
        manifest = build(args.output_dir, args.manifest)
    except (Milestone6Error, OSError, csv.Error, json.JSONDecodeError, KeyError, ValueError) as exc:
        print(f"error: {exc}")
        return 2
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
