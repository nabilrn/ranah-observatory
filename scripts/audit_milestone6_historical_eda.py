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
DEFAULT_ANALYSIS = ROOT / "data" / "analysis" / "historical"
DEFAULT_MANIFEST = ROOT / "data" / "manifests" / "milestone6_historical_eda.json"
DEFAULT_REPORT = ROOT / "data" / "manifests" / "milestone6_historical_eda_audit.json"

EXPECTED_OUTPUTS = {
    "timeline": "west-sumatra-source-era-timeline.csv",
    "historical_population_anchor": "west-sumatra-1971-population-anchor.csv",
    "modern_trajectory": "west-sumatra-modern-trajectory-2018-2025.csv",
    "modern_summary": "west-sumatra-modern-trend-summary.csv",
    "climate_yearly": "west-sumatra-chirps-regional-year-summary.csv",
    "climate_signals": "west-sumatra-chirps-geography-signals.csv",
    "findings": "west-sumatra-exploratory-findings.csv",
}
REQUIRED_EVENTS = {
    "sumatra_autonomy_1947",
    "sumatra_three_provinces_1948",
    "sumatera_tengah_1950",
    "sumbar_jambi_riau_1957",
    "sumbar_confirmation_1958",
    "census_boundary_warning_1961",
}
REQUIRED_GAPS = {"archive_gap_1945_1946", "archive_gap_1951_1960"}
TREND_QUALIFIED = {
    "poverty_rate",
    "real_grdp_growth",
    "mean_years_schooling",
    "expected_years_schooling",
    "life_expectancy",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def finite(value: str) -> bool:
    try:
        number = float(value)
    except ValueError:
        return False
    return math.isfinite(number)


def audit(analysis_dir: Path, manifest_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    if not manifest_path.exists():
        return {
            "schema": "ranah-observatory/milestone6-historical-eda-audit/v1",
            "errors": [f"missing manifest: {manifest_path}"],
            "milestone6_complete": False,
        }
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    if manifest.get("schema") != "ranah-observatory/milestone6-historical-eda/v1":
        errors.append("Milestone 6 manifest schema drift")
    if manifest.get("criterion") != "exploratory historical analysis":
        errors.append("Milestone 6 criterion drift")
    if manifest.get("scope") != "segmented_evidence_regimes_no_historical_boundary_harmonization":
        errors.append("Milestone 6 segmented scope drift")
    if manifest.get("causal_analysis_performed") is not False:
        errors.append("Milestone 6 must not perform causal analysis")
    if manifest.get("frontier_or_expected_performance_model_performed") is not False:
        errors.append("Milestone 6 must not perform frontier/expected-performance modelling")
    if manifest.get("historical_current_geography_bridge_performed") is not False:
        errors.append("Milestone 6 must not bridge historical and current geography automatically")

    output_files = manifest.get("output_files")
    output_hashes = manifest.get("output_sha256")
    if not isinstance(output_files, dict) or not isinstance(output_hashes, dict):
        errors.append("manifest output file/hash contracts are missing")
        output_files = {}
        output_hashes = {}

    resolved: dict[str, Path] = {}
    for key, filename in EXPECTED_OUTPUTS.items():
        path = analysis_dir / filename
        resolved[key] = path
        expected_rel = f"data/analysis/historical/{filename}"
        if output_files.get(key) != expected_rel:
            errors.append(f"manifest output path drift for {key}")
        if not path.exists():
            errors.append(f"missing Milestone 6 output {filename}")
            continue
        expected_hash = output_hashes.get(key)
        if not expected_hash or sha256_file(path) != expected_hash:
            errors.append(f"output SHA-256 mismatch for {filename}")

    source_hashes = manifest.get("source_sha256")
    required_sources = {
        "historical_geography_events": ROOT / "data" / "registries" / "historical_geography_events.csv",
        "historical_source_inventory": ROOT / "data" / "registries" / "historical_source_inventory.csv",
        "historical_population_source_native": ROOT / "data" / "processed" / "bps" / "historical_population_source_native.csv",
        "bps_canonical_observations": ROOT / "data" / "processed" / "bps" / "panel" / "bps-canonical-observations.csv",
        "bps_canonical_manifest": ROOT / "data" / "processed" / "bps" / "panel" / "bps-canonical-panel.manifest.json",
        "chirps_observations": ROOT / "data" / "processed" / "climate" / "rainfall" / "chirps-annual-rainfall-observations.csv",
        "chirps_manifest": ROOT / "data" / "processed" / "climate" / "rainfall" / "chirps-rainfall-materialization.manifest.json",
        "geographies": ROOT / "data" / "registries" / "geographies.csv",
    }
    if not isinstance(source_hashes, dict):
        errors.append("manifest source SHA-256 contract is missing")
        source_hashes = {}
    for name, path in required_sources.items():
        if source_hashes.get(name) != sha256_file(path):
            errors.append(f"source SHA-256 drift for {name}")

    if errors and any(not path.exists() for path in resolved.values()):
        return {
            "schema": "ranah-observatory/milestone6-historical-eda-audit/v1",
            "criterion": "exploratory historical analysis",
            "errors": errors,
            "milestone6_complete": False,
        }

    timeline = read_csv(resolved["timeline"])
    timeline_ids = {row["record_id"] for row in timeline}
    if not REQUIRED_EVENTS.issubset(timeline_ids):
        errors.append("timeline is missing one or more required qualified historical events")
    if not REQUIRED_GAPS.issubset(timeline_ids):
        errors.append("timeline is missing explicit 1945-1946 or 1951-1960 gap")
    if len(timeline) != 8:
        errors.append(f"expected 8 timeline rows; got {len(timeline)}")
    for row in timeline:
        if row.get("causal_claim") != "false":
            errors.append(f"timeline row {row.get('record_id')} must not make a causal claim")
    warning = next((row for row in timeline if row["record_id"] == "census_boundary_warning_1961"), None)
    if not warning or "Tingkat I" not in warning["analytical_implication"]:
        errors.append("1961 boundary warning lost the Tingkat I constraint")
    event_1957 = next((row for row in timeline if row["record_id"] == "sumbar_jambi_riau_1957"), None)
    if not event_1957 or "different analytical geography" not in event_1957["analytical_implication"]:
        errors.append("1957 boundary discontinuity constraint is missing")

    population = read_csv(resolved["historical_population_anchor"])
    if len(population) != 1:
        errors.append(f"expected exactly one historical population anchor; got {len(population)}")
    else:
        row = population[0]
        if row.get("source_geography_id") != "idn.13.h1958":
            errors.append("1971 population anchor is not attached to idn.13.h1958")
        if row.get("current_geography_bridge_allowed") != "false":
            errors.append("1971 anchor illegally allows a bridge to current idn.13")
        if row.get("mapping_status") != "qualified_source_era" or row.get("reconstruction_state") != "observed_source_era":
            errors.append("1971 anchor source-era state drift")
        if not finite(row.get("value_numeric", "")) or not math.isclose(float(row["value_numeric"]), 2789822.0, rel_tol=0.0, abs_tol=0.5):
            errors.append("1971 source-era province population is not 2,789,822")
        if row.get("local_source_row_count") != "14":
            errors.append("1971 local source row count is not 14")
        if not finite(row.get("local_source_rows_sum", "")) or not math.isclose(float(row["local_source_rows_sum"]), 2789822.0, rel_tol=0.0, abs_tol=0.5):
            errors.append("1971 local source rows no longer sum to the province total")

    modern = read_csv(resolved["modern_trajectory"])
    summary = read_csv(resolved["modern_summary"])
    if len(modern) != 54:
        errors.append(f"expected 54 modern province observations; got {len(modern)}")
    if len(summary) != 7:
        errors.append(f"expected 7 modern series summaries; got {len(summary)}")
    modern_keys: set[tuple[str, int]] = set()
    for row in modern:
        if row.get("boundary_regime") != "current_sumatera_barat_bps":
            errors.append("modern trajectory boundary regime drift")
        if row.get("causal_claim") != "false":
            errors.append("modern trajectory contains a causal claim")
        try:
            key = (row["indicator_id"], int(row["year"]))
        except ValueError:
            errors.append("modern trajectory contains an invalid year")
            continue
        if key in modern_keys:
            errors.append(f"duplicate modern trajectory key {key}")
        modern_keys.add(key)
        if not finite(row.get("value_numeric", "")):
            errors.append(f"non-finite modern value for {key}")
    qualified = {row["indicator_id"] for row in summary if row.get("trend_qualified") == "true"}
    if qualified != TREND_QUALIFIED:
        errors.append(f"trend-qualified indicator set drift: {sorted(qualified)}")
    for row in summary:
        if row["indicator_id"] in TREND_QUALIFIED and int(row["observation_count"]) < 6:
            errors.append(f"trend-qualified series {row['indicator_id']} has fewer than six observations")
        expected_change_unit = "percentage_points" if row.get("unit") == "percent" else row.get("unit")
        if row.get("absolute_change_unit") != expected_change_unit:
            errors.append(f"absolute-change unit drift for {row.get('indicator_id')}")
    grdp = next((row for row in summary if row["indicator_id"] == "real_grdp_growth"), None)
    if not grdp or grdp["minimum_year"] != "2020" or float(grdp["minimum_value"]) >= 0:
        errors.append("modern GRDP series no longer has a negative 2020 minimum within the 2018-2025 window")

    climate_yearly = read_csv(resolved["climate_yearly"])
    climate_signals = read_csv(resolved["climate_signals"])
    if len(climate_yearly) != 45:
        errors.append(f"expected 45 CHIRPS regional-year rows; got {len(climate_yearly)}")
    if {int(row["year"]) for row in climate_yearly} != set(range(1981, 2026)):
        errors.append("CHIRPS regional-year scope is not exactly 1981-2025")
    if len(climate_signals) != 19 or len({row["geography_id"] for row in climate_signals}) != 19:
        errors.append("expected exactly 19 CHIRPS geography signal rows")
    for row in climate_yearly + climate_signals:
        if row.get("claim_class") != "model_estimate":
            errors.append("CHIRPS EDA row is not labelled model_estimate")
        if row.get("spatial_frame") != "fixed_current_boundary_june_2026":
            errors.append("CHIRPS EDA spatial frame drift")
        if row.get("historical_boundary_continuity_claimed") != "false":
            errors.append("CHIRPS EDA illegally claims historical boundary continuity")
        if row.get("independent_station_validation") != "pending":
            errors.append("CHIRPS station-validation status drift")
        if row.get("causal_claim") != "false":
            errors.append("CHIRPS EDA contains a causal claim")
    if not all(row.get("wetter_in_1998") == "true" for row in climate_signals):
        errors.append("frozen 1997->1998 CHIRPS regional signal no longer holds for all 19 geographies")

    findings = read_csv(resolved["findings"])
    finding_ids = {row["finding_id"] for row in findings}
    required_findings = {
        "m6_boundary_discontinuity_1957",
        "m6_population_1971_anchor",
        "m6_climate_1997_1998_signal",
        "m6_grdp_2020_contraction",
    }
    if not required_findings.issubset(finding_ids):
        errors.append("required exploratory findings are missing")
    if len(findings) < 9:
        errors.append(f"expected at least 9 exploratory findings; got {len(findings)}")
    for row in findings:
        if row.get("causal_claim") != "false":
            errors.append(f"finding {row.get('finding_id')} contains a causal claim")
        statement = row.get("statement", "").casefold()
        forbidden = ("caused by", "causes ", "causal effect", "treatment effect", "wasted potential estimate")
        if any(term in statement for term in forbidden):
            errors.append(f"finding {row.get('finding_id')} uses prohibited causal/frontier language")

    diagnostics = manifest.get("climate", {})
    if diagnostics.get("year_count") != 45 or diagnostics.get("geography_count") != 19:
        errors.append("manifest CHIRPS diagnostics cardinality drift")
    if diagnostics.get("all_19_wetter_1998_vs_1997") is not True:
        errors.append("manifest lost all-19 1997->1998 rainfall signal")
    modern_manifest = manifest.get("modern", {})
    if modern_manifest.get("series_count") != 7 or modern_manifest.get("trend_qualified_count") != 5 or modern_manifest.get("observation_count") != 54:
        errors.append("manifest modern diagnostics drift")
    historical_manifest = manifest.get("historical_population_1971", {})
    if historical_manifest.get("local_count") != 14:
        errors.append("manifest 1971 local row count drift")

    complete = not errors
    return {
        "schema": "ranah-observatory/milestone6-historical-eda-audit/v1",
        "criterion": "exploratory historical analysis",
        "timeline_row_count": len(timeline),
        "explicit_gap_count": sum(row["record_type"] == "explicit_gap" for row in timeline),
        "historical_population_anchor_count": len(population),
        "modern_observation_count": len(modern),
        "modern_series_count": len(summary),
        "trend_qualified_modern_series_count": len(qualified),
        "climate_year_count": len(climate_yearly),
        "climate_geography_count": len(climate_signals),
        "finding_count": len(findings),
        "causal_analysis_performed": False,
        "frontier_model_performed": False,
        "historical_boundary_harmonization_performed": False,
        "errors": errors,
        "milestone6_complete": complete,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit the frozen Milestone 6 exploratory historical analysis.")
    parser.add_argument("--analysis-dir", type=Path, default=DEFAULT_ANALYSIS)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    try:
        report = audit(args.analysis_dir, args.manifest)
    except (OSError, csv.Error, json.JSONDecodeError, KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if args.require_complete and not report["milestone6_complete"]:
        return 3
    return 0 if report["milestone6_complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
