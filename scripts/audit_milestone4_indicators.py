#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROCESSED = ROOT / "data" / "processed"
DEFAULT_INDICATORS = ROOT / "data" / "registries" / "indicators.csv"
DEFAULT_OUTPUT = ROOT / "data" / "manifests" / "milestone4_indicator_inventory.json"
MIN_INDICATORS = 40
MAX_INDICATORS = 60

OBS_REQUIRED = {"observation_id", "indicator_id", "geography_id", "provenance_id", "claim_type"}
PROV_REQUIRED = {"provenance_id", "source_id", "artifact_locator", "extraction_method"}

# Milestone 4 is a historical completion gate. Freeze both its 40-indicator
# cohort and the exact evidence surfaces that originally closed the criterion.
# Later milestones remain independently auditable without retroactively
# rewriting the M4 snapshot whenever new processed datasets are added.
MILESTONE4_FROZEN_INDICATORS = {
    "agriculture_share_grdp",
    "annual_rainfall",
    "average_employee_wage",
    "child_mortality_rate",
    "dependency_ratio",
    "domestic_investment_realization",
    "elderly_population_share",
    "employed_population",
    "expected_years_schooling",
    "export_value",
    "flood_events",
    "food_inadequacy_prevalence",
    "foreign_investment_realization",
    "gini_ratio",
    "household_expenditure_per_capita_monthly",
    "infant_mortality_rate",
    "internet_access",
    "labor_force_count",
    "labor_force_participation",
    "landslide_events",
    "large_medium_industry_employment",
    "life_expectancy",
    "manufacturing_share_grdp",
    "mean_years_schooling",
    "mobile_phone_use",
    "neet_rate",
    "net_migration_rate",
    "population_growth",
    "population_total",
    "poverty_rate",
    "provincial_road_length",
    "real_grdp_growth",
    "rice_yield",
    "road_condition_good",
    "total_fertility_rate",
    "under_five_mortality_rate",
    "underemployment_rate",
    "unemployed_population",
    "unemployment_rate",
    "urban_population_share",
}

MILESTONE4_FROZEN_OBSERVATION_PATHS = (
    "bnpb/disaster/bnpb-disaster-canonical-observations.csv",
    "bps/demography/population-growth-2010-2020-observations.csv",
    "bps/expansion/bps-expansion-canonical-observations.csv",
    "bps/milestone4/bps-milestone4-batch1-observations.csv",
    "bps/panel/bps-canonical-observations.csv",
    "climate/rainfall/chirps-annual-rainfall-observations.csv",
)

MILESTONE4_FROZEN_PROVENANCE_PATHS = (
    "bnpb/disaster/bnpb-disaster-canonical-provenance.csv",
    "bps/demography/population-growth-2010-2020-provenance.csv",
    "bps/expansion/bps-expansion-canonical-provenance.csv",
    "bps/milestone4/bps-milestone4-batch1-provenance.csv",
    "bps/panel/bps-canonical-provenance.csv",
    "climate/rainfall/chirps-annual-rainfall-provenance.csv",
)


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        rows = [{key: (value or "").strip() for key, value in row.items()} for row in reader]
    return fields, rows


def audit(processed_root: Path, indicator_registry: Path) -> dict[str, Any]:
    registry_fields, registry_rows = _read_csv(indicator_registry)
    if "indicator_id" not in registry_fields:
        raise ValueError("indicator registry is missing indicator_id")
    registered = {row["indicator_id"] for row in registry_rows if row["indicator_id"]}

    observation_files: list[str] = []
    provenance_files: list[str] = []
    observations: list[tuple[Path, dict[str, str]]] = []
    provenance_ids: set[str] = set()

    for relative_path in MILESTONE4_FROZEN_OBSERVATION_PATHS:
        path = processed_root / relative_path
        fields, rows = _read_csv(path)
        if not OBS_REQUIRED.issubset(set(fields)):
            raise ValueError(f"frozen observation file has incompatible schema: {path}")
        frozen_rows = [row for row in rows if row.get("indicator_id", "") in MILESTONE4_FROZEN_INDICATORS]
        if not frozen_rows:
            raise ValueError(f"frozen observation file has no M4 cohort rows: {path}")
        observation_files.append(path.relative_to(ROOT).as_posix())
        observations.extend((path, row) for row in frozen_rows)

    for relative_path in MILESTONE4_FROZEN_PROVENANCE_PATHS:
        path = processed_root / relative_path
        fields, rows = _read_csv(path)
        if not PROV_REQUIRED.issubset(set(fields)):
            raise ValueError(f"frozen provenance file has incompatible schema: {path}")
        provenance_files.append(path.relative_to(ROOT).as_posix())
        for row in rows:
            pid = row.get("provenance_id", "")
            if pid:
                provenance_ids.add(pid)

    by_indicator: dict[str, dict[str, Any]] = {}
    seen_observation_ids: set[str] = set()
    duplicate_observation_ids: list[str] = []
    missing_observation_ids: list[dict[str, str]] = []
    unresolved_provenance: list[dict[str, str]] = []

    for path, row in observations:
        oid = row.get("observation_id", "")
        indicator_id = row.get("indicator_id", "")
        if not oid:
            missing_observation_ids.append(
                {
                    "indicator_id": indicator_id,
                    "geography_id": row.get("geography_id", ""),
                    "time_start": row.get("time_start", ""),
                    "file": path.relative_to(ROOT).as_posix(),
                }
            )
        elif oid in seen_observation_ids:
            duplicate_observation_ids.append(oid)
        else:
            seen_observation_ids.add(oid)

        provenance_id = row.get("provenance_id", "")
        entry = by_indicator.setdefault(
            indicator_id,
            {
                "observation_count": 0,
                "geography_ids": set(),
                "claim_types": set(),
                "provenance_ids": set(),
                "files": set(),
                "registered": indicator_id in registered,
                "missing_observation_id_count": 0,
            },
        )
        entry["observation_count"] += 1
        if not oid:
            entry["missing_observation_id_count"] += 1
        entry["geography_ids"].add(row.get("geography_id", ""))
        entry["claim_types"].add(row.get("claim_type", ""))
        entry["provenance_ids"].add(provenance_id)
        entry["files"].add(path.relative_to(ROOT).as_posix())
        if provenance_id not in provenance_ids:
            unresolved_provenance.append(
                {
                    "observation_id": oid,
                    "indicator_id": indicator_id,
                    "provenance_id": provenance_id,
                    "file": path.relative_to(ROOT).as_posix(),
                }
            )

    inventory: list[dict[str, Any]] = []
    qualified_ids: list[str] = []
    for indicator_id in sorted(by_indicator):
        entry = by_indicator[indicator_id]
        unresolved_count = sum(1 for item in unresolved_provenance if item["indicator_id"] == indicator_id)
        qualified = (
            bool(indicator_id)
            and indicator_id in MILESTONE4_FROZEN_INDICATORS
            and entry["registered"]
            and entry["observation_count"] > 0
            and entry["missing_observation_id_count"] == 0
            and len(entry["provenance_ids"]) > 0
            and unresolved_count == 0
        )
        if qualified:
            qualified_ids.append(indicator_id)
        inventory.append(
            {
                "indicator_id": indicator_id,
                "registered": entry["registered"],
                "observation_count": entry["observation_count"],
                "geography_count": len({gid for gid in entry["geography_ids"] if gid}),
                "claim_types": sorted(ct for ct in entry["claim_types"] if ct),
                "provenance_count": len({pid for pid in entry["provenance_ids"] if pid}),
                "missing_observation_id_count": entry["missing_observation_id_count"],
                "unresolved_provenance_count": unresolved_count,
                "files": sorted(entry["files"]),
                "counts_toward_milestone4": qualified,
            }
        )

    count = len(qualified_ids)
    return {
        "schema": "ranah-observatory/milestone4-indicator-inventory/v1",
        "criterion": "40-60 high-value indicators with provenance",
        "minimum_indicator_count": MIN_INDICATORS,
        "maximum_initial_target_count": MAX_INDICATORS,
        "qualified_indicator_count": count,
        "remaining_to_minimum": max(0, MIN_INDICATORS - count),
        "milestone4_complete": MIN_INDICATORS <= count <= MAX_INDICATORS,
        "qualified_indicator_ids": qualified_ids,
        "inventory": inventory,
        "observation_file_count": len(observation_files),
        "provenance_file_count": len(provenance_files),
        "observation_files": observation_files,
        "provenance_files": provenance_files,
        "duplicate_observation_ids": sorted(set(duplicate_observation_ids)),
        "missing_observation_ids": missing_observation_ids,
        "unresolved_provenance": unresolved_provenance,
        "unregistered_observed_indicator_ids": sorted(
            indicator_id for indicator_id, entry in by_indicator.items() if indicator_id and not entry["registered"]
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit the frozen Ranah Observatory Milestone 4 evidence cohort.")
    parser.add_argument("--processed-root", type=Path, default=DEFAULT_PROCESSED)
    parser.add_argument("--indicator-registry", type=Path, default=DEFAULT_INDICATORS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    try:
        report = audit(args.processed_root, args.indicator_registry)
    except (OSError, ValueError, csv.Error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if report["duplicate_observation_ids"] or report["missing_observation_ids"] or report["unresolved_provenance"]:
        return 2
    if args.require_complete and not report["milestone4_complete"]:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
