#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/manifests/milestone10_analytical_panel.json"
LONG = ROOT / "data/analysis/engine/panel_v1/m10-panel-long.csv"
WIDE = ROOT / "data/analysis/engine/panel_v1/m10-panel-wide.csv"
COVERAGE = ROOT / "data/analysis/engine/panel_v1/m10-indicator-coverage.csv"
METADATA = ROOT / "data/analysis/engine/panel_v1/m10-indicator-metadata.csv"
SPEC = ROOT / "research/MILESTONE10_ANALYTICAL_PANEL_SPEC.md"
FOUNDATION = ROOT / "data/manifests/research_foundation_complete.json"

EXPECTED_INDICATORS = [
    "expected_years_schooling",
    "mean_years_schooling",
    "life_expectancy",
    "labor_force_participation",
    "unemployment_rate",
    "poverty_rate",
    "real_grdp_growth",
    "agriculture_share_grdp",
    "manufacturing_share_grdp",
    "rice_yield",
    "underemployment_rate",
    "population_total",
    "annual_rainfall",
    "flood_events",
    "landslide_events",
]
EXPECTED_COMPLETE = {
    "expected_years_schooling",
    "mean_years_schooling",
    "labor_force_participation",
    "unemployment_rate",
    "poverty_rate",
    "real_grdp_growth",
    "rice_yield",
    "annual_rainfall",
}
EXPECTED_YEARS = list(range(2018, 2026))
EXPECTED_GEOGRAPHY_COUNT = 19


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def audit() -> dict[str, Any]:
    errors: list[str] = []
    for path in [MANIFEST, LONG, WIDE, COVERAGE, METADATA, SPEC, FOUNDATION]:
        if not path.exists():
            errors.append(f"missing required M10 file: {path.relative_to(ROOT)}")
    if errors:
        return {"schema": "ranah-observatory/milestone10-audit/v1", "errors": errors, "milestone10_complete": False}

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    foundation = json.loads(FOUNDATION.read_text(encoding="utf-8"))
    long_rows = read_csv(LONG)
    wide_rows = read_csv(WIDE)
    coverage_rows = read_csv(COVERAGE)
    metadata_rows = read_csv(METADATA)
    spec_text = SPEC.read_text(encoding="utf-8")

    if foundation.get("initial_research_foundation_complete") is not True or foundation.get("completed_criterion_count") != 9 or foundation.get("errors") != []:
        errors.append("Research Foundation must remain complete 9/9 before M10 can pass")

    locked_manifest = {
        "schema": "ranah-observatory/milestone10-analytical-panel/v1",
        "phase": "final_analytical_research_engine",
        "milestone": 10,
        "regime_id": "sumbar_current_kabkota_2018_2025_v1",
        "geography_count": 19,
        "start_year": 2018,
        "end_year": 2025,
        "year_count": 8,
        "indicator_count": 15,
        "wide_row_count": 152,
        "duplicate_key_count": 0,
        "imputation_performed": False,
        "forward_fill_performed": False,
        "backward_fill_performed": False,
        "zero_fill_missing_years_performed": False,
        "historical_boundary_harmonization_performed": False,
        "historical_continuity_claimed": False,
        "province_aggregate_included": False,
        "held_source_native_included": False,
        "claim_types_preserved": True,
        "reference_periods_preserved": True,
        "causal_analysis_performed": False,
        "expected_performance_model_performed": False,
        "frontier_model_performed": False,
        "monetary_wasted_potential_estimated": False,
        "milestone10_complete": True,
    }
    for key, expected in locked_manifest.items():
        if manifest.get(key) != expected:
            errors.append(f"M10 manifest contract drift: {key} expected={expected!r} got={manifest.get(key)!r}")

    if manifest.get("years") != EXPECTED_YEARS:
        errors.append("M10 year list drift")
    if manifest.get("indicator_ids") != EXPECTED_INDICATORS:
        errors.append("M10 preregistered indicator order/set drift")
    geography_ids = manifest.get("geography_ids")
    if not isinstance(geography_ids, list) or len(geography_ids) != 19 or len(set(geography_ids)) != 19 or any(not str(g).startswith("idn.13.") for g in geography_ids):
        errors.append("M10 exact 19 current Sumbar geography footprint drift")
    if set(manifest.get("complete_2018_2025_indicator_ids", [])) != EXPECTED_COMPLETE:
        errors.append("M10 complete-indicator coverage fingerprint drift")

    output_records = manifest.get("outputs", {})
    expected_outputs = {
        "long": LONG,
        "wide": WIDE,
        "coverage": COVERAGE,
        "metadata": METADATA,
    }
    for key, path in expected_outputs.items():
        record = output_records.get(key, {})
        if record.get("path") != str(path.relative_to(ROOT)):
            errors.append(f"M10 output path drift: {key}")
        if record.get("sha256") != sha256(path):
            errors.append(f"M10 output checksum drift: {key}")

    for path_string, expected_hash in manifest.get("source_files", {}).items():
        path = ROOT / path_string
        if not path.exists() or sha256(path) != expected_hash:
            errors.append(f"M10 source checksum drift: {path_string}")
    for path_string, expected_hash in manifest.get("registry_files", {}).items():
        path = ROOT / path_string
        if not path.exists() or sha256(path) != expected_hash:
            errors.append(f"M10 registry checksum drift: {path_string}")

    if len(wide_rows) != 152:
        errors.append(f"M10 wide row count must be 152, got {len(wide_rows)}")
    wide_keys = {(row.get("geography_id"), row.get("analysis_year")) for row in wide_rows}
    if len(wide_keys) != 152:
        errors.append("M10 wide geography-year keys are not unique/exact")
    for row in wide_rows:
        if row.get("regime_id") != "sumbar_current_kabkota_2018_2025_v1":
            errors.append("M10 wide row regime drift")
            break
        if row.get("analysis_year") not in {str(y) for y in EXPECTED_YEARS}:
            errors.append(f"M10 wide row year outside contract: {row.get('analysis_year')}")
            break

    long_keys: set[tuple[str, str, str]] = set()
    long_value_map: dict[tuple[str, str, str], str] = {}
    for row in long_rows:
        key = (row.get("geography_id", ""), row.get("analysis_year", ""), row.get("indicator_id", ""))
        if key in long_keys:
            errors.append(f"duplicate M10 long key: {key}")
        long_keys.add(key)
        long_value_map[key] = row.get("value_numeric", "")
        if row.get("indicator_id") not in EXPECTED_INDICATORS:
            errors.append(f"unexpected M10 long indicator: {row.get('indicator_id')}")
        if not row.get("observation_id") or not row.get("provenance_id"):
            errors.append(f"M10 long lineage missing: {key}")
        try:
            value = float(row.get("value_numeric", "nan"))
        except ValueError:
            errors.append(f"M10 long value invalid: {key}")
        else:
            if not math.isfinite(value):
                errors.append(f"M10 long value non-finite: {key}")
        if row.get("geography_id") == "idn.13" or not row.get("geography_id", "").startswith("idn.13."):
            errors.append(f"province/non-Sumbar geography leaked into M10: {row.get('geography_id')}")

    if len(long_rows) != manifest.get("long_observation_count"):
        errors.append("M10 long row count differs from manifest")
    total_possible = 19 * 8 * 15
    if manifest.get("total_possible_indicator_cells") != total_possible:
        errors.append("M10 total possible cell count drift")
    if manifest.get("missing_indicator_cells") != total_possible - len(long_rows):
        errors.append("M10 missing-cell arithmetic drift")

    for row in wide_rows:
        geography_id = row["geography_id"]
        year = row["analysis_year"]
        for indicator in EXPECTED_INDICATORS:
            wide_value = row.get(indicator, "")
            long_value = long_value_map.get((geography_id, year, indicator), "")
            if wide_value != long_value:
                errors.append(f"M10 wide/long value mismatch: {(geography_id, year, indicator)}")

    if len(coverage_rows) != 15 or {row.get("indicator_id") for row in coverage_rows} != set(EXPECTED_INDICATORS):
        errors.append("M10 coverage table must contain exact 15 indicators")
    coverage_by_indicator = {row["indicator_id"]: row for row in coverage_rows if row.get("indicator_id")}
    for indicator in EXPECTED_INDICATORS:
        row = coverage_by_indicator.get(indicator)
        if row is None:
            continue
        present = sum(1 for key in long_keys if key[2] == indicator)
        if int(row["present_cells"]) != present:
            errors.append(f"M10 coverage present-cell mismatch: {indicator}")
        if int(row["total_possible_cells"]) != 152:
            errors.append(f"M10 coverage denominator drift: {indicator}")
        if int(row["missing_cells"]) != 152 - present:
            errors.append(f"M10 coverage missing-cell mismatch: {indicator}")

    if len(metadata_rows) != 15 or {row.get("indicator_id") for row in metadata_rows} != set(EXPECTED_INDICATORS):
        errors.append("M10 metadata table must contain exact 15 indicators")
    for row in metadata_rows:
        if not row.get("definition") or not row.get("domain") or not row.get("source_artifact") or not row.get("m10_semantic_caution"):
            errors.append(f"M10 metadata incomplete: {row.get('indicator_id')}")

    rainfall_rows = [row for row in long_rows if row.get("indicator_id") == "annual_rainfall"]
    if len(rainfall_rows) != 152 or {row.get("claim_type") for row in rainfall_rows} != {"model_estimate"}:
        errors.append("M10 CHIRPS rainfall must remain 152 model_estimate rows")
    disaster_rows = [row for row in long_rows if row.get("indicator_id") in {"flood_events", "landslide_events"}]
    if len(disaster_rows) != 38 or {row.get("analysis_year") for row in disaster_rows} != {"2024"} or {row.get("claim_type") for row in disaster_rows} != {"observed"}:
        errors.append("M10 BNPB disaster context must remain exact 38 observed rows in 2024 only")
    population_rows = [row for row in long_rows if row.get("indicator_id") == "population_total"]
    if len(population_rows) != 19 or {row.get("analysis_year") for row in population_rows} != {"2020"}:
        errors.append("M10 population must remain sparse SP2020 anchor only")

    required_spec_phrases = [
        "Missingness is an analytical object, not an inconvenience.",
        "No causal, frontier, counterfactual, or monetary wasted-potential claim is authorized.",
        "exact `19 geographies × 8 years = 152 rows`",
        "must not interpolate population between years",
    ]
    for phrase in required_spec_phrases:
        if phrase not in spec_text:
            errors.append(f"M10 spec lost required guardrail phrase: {phrase}")

    return {
        "schema": "ranah-observatory/milestone10-audit/v1",
        "phase": "final_analytical_research_engine",
        "milestone": 10,
        "regime_id": manifest.get("regime_id"),
        "geography_count": manifest.get("geography_count"),
        "year_count": manifest.get("year_count"),
        "indicator_count": manifest.get("indicator_count"),
        "wide_row_count": len(wide_rows),
        "long_observation_count": len(long_rows),
        "complete_indicator_count": len(manifest.get("complete_2018_2025_indicator_ids", [])),
        "missing_indicator_cells": manifest.get("missing_indicator_cells"),
        "imputation_performed": manifest.get("imputation_performed"),
        "foundation_9_of_9_still_complete": foundation.get("initial_research_foundation_complete") is True,
        "milestone10_complete": manifest.get("milestone10_complete") is True and not errors,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Milestone 10 Analytical Panel v1")
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit()
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    if report["errors"]:
        return 1
    if args.require_complete and report.get("milestone10_complete") is not True:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
