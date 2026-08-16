#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REFERENCE_PERIODS = ROOT / "data" / "registries" / "bps_population_reference_periods.csv"
DEFAULT_ANCHOR_QUALIFICATION = ROOT / "data" / "registries" / "bps_population_anchor_qualification.csv"
DEFAULT_CANONICAL = ROOT / "data" / "processed" / "bps" / "expansion" / "bps-expansion-canonical-observations.csv"
EXPECTED_YEARS = (2010, 2015, 2020)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def parse_date(value: str, label: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"invalid {label} date {value!r}") from exc


def require_bps_url(value: str, label: str) -> None:
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not (host == "bps.go.id" or host.endswith(".bps.go.id")):
        raise ValueError(f"{label} must be an official HTTPS BPS URL: {value!r}")


def validate_reference_periods(rows: list[dict[str, str]]) -> dict[str, Any]:
    if len(rows) != len(EXPECTED_YEARS):
        raise ValueError(f"expected {len(EXPECTED_YEARS)} reference-period rows; got {len(rows)}")
    by_year: dict[int, dict[str, str]] = {}
    for row in rows:
        year = int(row["year"])
        if year in by_year:
            raise ValueError(f"duplicate reference-period row for {year}")
        by_year[year] = row
        fieldwork_start = parse_date(row["fieldwork_start"], "fieldwork_start")
        fieldwork_end = parse_date(row["fieldwork_end"], "fieldwork_end")
        reference_start = parse_date(row["reference_start"], "reference_start")
        reference_end = parse_date(row["reference_end"], "reference_end")
        if fieldwork_start > fieldwork_end:
            raise ValueError(f"reversed fieldwork window for {year}")
        if reference_start > reference_end:
            raise ValueError(f"reversed reference window for {year}")
        if not (fieldwork_start <= reference_start <= reference_end <= fieldwork_end):
            raise ValueError(f"reference semantics fall outside fieldwork window for {year}")
        require_bps_url(row["official_source_url"], "official_source_url")
        if row["supporting_source_url"]:
            require_bps_url(row["supporting_source_url"], "supporting_source_url")
        if not row["population_growth_use_status"].startswith("blocked"):
            raise ValueError(f"custom derived population growth must remain blocked for {year}")

    if tuple(sorted(by_year)) != EXPECTED_YEARS:
        raise ValueError(f"unexpected reference-period years: {sorted(by_year)}")

    y2010 = by_year[2010]
    if y2010["source_type"] != "census" or y2010["reference_semantics"] != "census_day":
        raise ValueError("2010 must retain census-day semantics")
    if y2010["point_reference_date"] != "2010-05-15":
        raise ValueError("2010 Hari Sensus must remain 2010-05-15")
    if y2010["reference_start"] != "2010-05-15" or y2010["reference_end"] != "2010-05-15":
        raise ValueError("2010 reference window must collapse to Hari Sensus")
    if y2010["qualification_status"] != "qualified_point_reference":
        raise ValueError("2010 point-reference qualification drifted")

    y2015 = by_year[2015]
    if y2015["source_type"] != "supas" or y2015["reference_semantics"] != "fieldwork_window":
        raise ValueError("2015 must retain SUPAS fieldwork-window semantics")
    if y2015["point_reference_date"]:
        raise ValueError("2015 must not invent a point reference date")
    if (y2015["reference_start"], y2015["reference_end"]) != ("2015-05-01", "2015-05-31"):
        raise ValueError("2015 qualified window drifted")
    if y2015["qualification_status"] != "qualified_window_only":
        raise ValueError("2015 qualification must remain window-only")

    y2020 = by_year[2020]
    if y2020["source_type"] != "census" or y2020["reference_semantics"] != "result_month_window":
        raise ValueError("2020 must retain September result-month semantics")
    if y2020["point_reference_date"]:
        raise ValueError("2020 registry must not invent a point reference date")
    if (y2020["reference_start"], y2020["reference_end"]) != ("2020-09-01", "2020-09-30"):
        raise ValueError("2020 September result window drifted")
    if y2020["qualification_status"] != "qualified_month_window":
        raise ValueError("2020 qualification must remain month-window")

    return {
        "year_count": 3,
        "qualified_point_reference_years": [2010],
        "qualified_window_only_years": [2015, 2020],
        "custom_population_growth_ready": False,
    }


def validate_anchor_registry(reference_rows: list[dict[str, str]], anchor_rows: list[dict[str, str]]) -> dict[str, Any]:
    references = {int(row["year"]): row for row in reference_rows}
    anchors = {int(row["year"]): row for row in anchor_rows}
    expected = {
        2010: "qualified_census_day_2010-05-15",
        2015: "qualified_fieldwork_window_2015-05-01_2015-05-31_point_date_unqualified",
        2020: "qualified_september_2020",
    }
    for year, decision in expected.items():
        if anchors.get(year, {}).get("reference_date_decision") != decision:
            raise ValueError(f"anchor/reference-period registry mismatch for {year}")
        if not anchors[year]["population_growth_derivation"].startswith("blocked"):
            raise ValueError(f"growth status unexpectedly unblocked for {year}")
    return {"anchor_rows_crosschecked": 3, "growth_still_blocked": True}


def validate_existing_sp2020(reference_rows: list[dict[str, str]], canonical_rows: list[dict[str, str]]) -> dict[str, Any]:
    reference = {int(row["year"]): row for row in reference_rows}[2020]
    population = [row for row in canonical_rows if row["indicator_id"] == "population_total"]
    if len(population) != 20:
        raise ValueError(f"expected 20 canonical SP2020 population rows; got {len(population)}")
    expected_start = reference["reference_start"]
    expected_end = reference["reference_end"]
    mismatches = [
        row["observation_id"]
        for row in population
        if row["time_start"] != expected_start or row["time_end"] != expected_end
    ]
    if mismatches:
        raise ValueError(f"canonical SP2020 reference bounds differ from qualified September window: {mismatches[:5]}")
    return {
        "canonical_population_rows": 20,
        "canonical_time_start": expected_start,
        "canonical_time_end": expected_end,
        "matches_qualified_reference_window": True,
    }


def build_report(reference_path: Path, anchor_path: Path, canonical_path: Path) -> dict[str, Any]:
    reference_rows = read_csv(reference_path)
    result = validate_reference_periods(reference_rows)
    anchor_crosscheck = validate_anchor_registry(reference_rows, read_csv(anchor_path))
    sp2020_crosscheck = validate_existing_sp2020(reference_rows, read_csv(canonical_path))
    return {
        "schema": "ranah-observatory/bps-population-reference-periods/v1",
        "reference_periods": result,
        "anchor_registry_crosscheck": anchor_crosscheck,
        "sp2020_canonical_crosscheck": sp2020_crosscheck,
        "growth_decision": {
            "custom_derived_growth_rows_ready": 0,
            "status": "blocked_pending_boundary_pair_qualification_and_interval_rule",
            "official_bps_growth_lane": "separate_future_qualification",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate BPS 2010/2015/2020 population reference-period qualification")
    parser.add_argument("--reference-periods", type=Path, default=DEFAULT_REFERENCE_PERIODS)
    parser.add_argument("--anchor-qualification", type=Path, default=DEFAULT_ANCHOR_QUALIFICATION)
    parser.add_argument("--canonical", type=Path, default=DEFAULT_CANONICAL)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = build_report(args.reference_periods, args.anchor_qualification, args.canonical)
    except (OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}")
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
