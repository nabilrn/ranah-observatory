#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data/analysis/engine/panel_v1"
MANIFEST_PATH = ROOT / "data/manifests/milestone10_analytical_panel.json"
GEOGRAPHY_REGISTRY = ROOT / "data/registries/geographies.csv"
INDICATOR_REGISTRY = ROOT / "data/registries/indicators.csv"

START_YEAR = 2018
END_YEAR = 2025
YEARS = list(range(START_YEAR, END_YEAR + 1))
REGIME_ID = "sumbar_current_kabkota_2018_2025_v1"

INDICATORS = [
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

SOURCE_SPECS: list[dict[str, Any]] = [
    {
        "path": ROOT / "data/processed/bps/panel/bps-canonical-observations.csv",
        "source_artifact": "bps_canonical_panel",
        "indicators": {
            "expected_years_schooling",
            "mean_years_schooling",
            "life_expectancy",
            "labor_force_participation",
            "unemployment_rate",
            "poverty_rate",
            "real_grdp_growth",
        },
    },
    {
        "path": ROOT / "data/processed/bps/expansion/bps-expansion-canonical-observations.csv",
        "source_artifact": "bps_expansion_canonical",
        "indicators": {
            "agriculture_share_grdp",
            "manufacturing_share_grdp",
            "rice_yield",
            "underemployment_rate",
            "population_total",
        },
    },
    {
        "path": ROOT / "data/processed/climate/rainfall/chirps-annual-rainfall-observations.csv",
        "source_artifact": "chirps_annual_rainfall",
        "indicators": {"annual_rainfall"},
    },
    {
        "path": ROOT / "data/processed/bnpb/disaster/bnpb-disaster-canonical-observations.csv",
        "source_artifact": "bnpb_disaster_canonical",
        "indicators": {"flood_events", "landslide_events"},
    },
]

INDICATOR_CAUTIONS = {
    "expected_years_schooling": "Susenas/HDI annual indicator; retain March reference-period semantics.",
    "mean_years_schooling": "Susenas/HDI annual indicator; retain March reference-period semantics.",
    "life_expectancy": "LF-SP2020-based UHH only in the qualified modern series; do not chain to legacy methodology.",
    "labor_force_participation": "August Sakernas reference; source weighting-regime notes remain material.",
    "unemployment_rate": "August Sakernas reference; source weighting-regime notes remain material.",
    "poverty_rate": "Susenas March poverty measure; annual analysis-year indexing does not make it a year-end value.",
    "real_grdp_growth": "ADHK 2010 real growth; source release/revision status remains in lineage notes.",
    "agriculture_share_grdp": "Derived from same-source ADHB sector and total GRDP; current-price structural share, not real growth.",
    "manufacturing_share_grdp": "Derived from same-source ADHB sector and total GRDP; current-price structural share, not real growth.",
    "rice_yield": "KSA-based derived productivity; preserve KSA revision/caveat notes.",
    "underemployment_rate": "August Sakernas; cross-regime comparability remains source-qualified rather than assumed.",
    "population_total": "SP2020 census anchor is intentionally sparse; no interpolation or annual back/forward fill.",
    "annual_rainfall": "CHIRPS v3 Final fixed-current-boundary model estimate; not BMKG station-observation equivalence.",
    "flood_events": "BNPB observed recorded-event count for 2024 only; missing years are not zero-filled.",
    "landslide_events": "BNPB observed recorded-event count for 2024 only; missing years are not zero-filled.",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [
            {key: (value or "").strip() for key, value in row.items()}
            for row in csv.DictReader(handle)
        ]


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def reference_period_pattern(time_start: str, time_end: str) -> str:
    if len(time_start) < 10 or len(time_end) < 10:
        return "unclassified"
    start_md = time_start[5:10]
    end_md = time_end[5:10]
    known = {
        ("01-01", "12-31"): "calendar_year",
        ("03-01", "03-31"): "march_reference",
        ("08-01", "08-31"): "august_reference",
        ("09-01", "09-30"): "september_reference",
    }
    return known.get((start_md, end_md), f"other:{start_md}_to_{end_md}")


def load_geographies() -> tuple[list[str], dict[str, str]]:
    rows = read_csv(GEOGRAPHY_REGISTRY)
    selected = [
        row
        for row in rows
        if row.get("parent_geography_id") == "idn.13"
        and row.get("geography_level") in {"regency", "city"}
        and row.get("status") == "current"
    ]
    ids = sorted(row["geography_id"] for row in selected)
    if len(ids) != 19 or len(set(ids)) != 19:
        raise RuntimeError(f"expected exact 19 current Sumbar regency/city geographies, got {len(ids)}")
    names = {row["geography_id"]: row["canonical_name"] for row in selected}
    return ids, names


def load_indicator_registry() -> dict[str, dict[str, str]]:
    rows = read_csv(INDICATOR_REGISTRY)
    by_id = {row.get("indicator_id", ""): row for row in rows}
    missing = [indicator for indicator in INDICATORS if indicator not in by_id]
    if missing:
        raise RuntimeError(f"preregistered M10 indicators missing from registry: {missing}")
    return by_id


def finite_numeric(value: str) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def source_assignment() -> dict[str, str]:
    assignments: dict[str, str] = {}
    for spec in SOURCE_SPECS:
        for indicator in spec["indicators"]:
            if indicator in assignments:
                raise RuntimeError(f"indicator assigned to multiple source artifacts: {indicator}")
            assignments[indicator] = spec["source_artifact"]
    if set(assignments) != set(INDICATORS):
        raise RuntimeError("M10 source assignment does not exactly match preregistered indicator set")
    return assignments


def collect_long_rows(geography_ids: set[str]) -> tuple[list[dict[str, str]], dict[str, str], int]:
    output: list[dict[str, str]] = []
    source_hashes: dict[str, str] = {}
    suppressed_skipped = 0
    seen_keys: set[tuple[str, int, str]] = set()

    for spec in SOURCE_SPECS:
        path: Path = spec["path"]
        if not path.exists():
            raise RuntimeError(f"missing qualified canonical source: {path.relative_to(ROOT)}")
        source_hashes[str(path.relative_to(ROOT))] = sha256(path)
        rows = read_csv(path)
        for row in rows:
            indicator = row.get("indicator_id", "")
            if indicator not in spec["indicators"]:
                continue
            geography_id = row.get("geography_id", "")
            if geography_id not in geography_ids:
                continue
            time_start = row.get("time_start", "")
            try:
                year = int(time_start[:4])
            except ValueError:
                raise RuntimeError(f"invalid time_start for {row.get('observation_id')}: {time_start!r}")
            if year not in YEARS:
                continue
            if row.get("suppressed", "").lower() == "true":
                suppressed_skipped += 1
                continue
            if not row.get("observation_id") or not row.get("provenance_id"):
                raise RuntimeError(f"selected M10 row lacks observation/provenance id: {row}")
            if not finite_numeric(row.get("value_numeric", "")):
                raise RuntimeError(f"selected M10 row has non-finite value: {row.get('observation_id')}")

            key = (geography_id, year, indicator)
            if key in seen_keys:
                raise RuntimeError(f"duplicate M10 geography-year-indicator key: {key}")
            seen_keys.add(key)

            output.append(
                {
                    "regime_id": REGIME_ID,
                    "geography_id": geography_id,
                    "analysis_year": str(year),
                    "indicator_id": indicator,
                    "value_numeric": row.get("value_numeric", ""),
                    "unit": row.get("unit", ""),
                    "claim_type": row.get("claim_type", ""),
                    "observation_id": row.get("observation_id", ""),
                    "provenance_id": row.get("provenance_id", ""),
                    "time_start": row.get("time_start", ""),
                    "time_end": row.get("time_end", ""),
                    "reference_period_pattern": reference_period_pattern(row.get("time_start", ""), row.get("time_end", "")),
                    "comparable": row.get("comparable", ""),
                    "methodology_version": row.get("methodology_version", ""),
                    "price_basis": row.get("price_basis", ""),
                    "source_artifact": spec["source_artifact"],
                    "source_path": str(path.relative_to(ROOT)),
                    "source_notes": row.get("notes", ""),
                }
            )

    output.sort(key=lambda row: (row["geography_id"], int(row["analysis_year"]), INDICATORS.index(row["indicator_id"])))
    return output, source_hashes, suppressed_skipped


def build_wide(long_rows: list[dict[str, str]], geography_ids: list[str], names: dict[str, str]) -> list[dict[str, Any]]:
    values = {
        (row["geography_id"], int(row["analysis_year"]), row["indicator_id"]): row["value_numeric"]
        for row in long_rows
    }
    output: list[dict[str, Any]] = []
    for geography_id in geography_ids:
        for year in YEARS:
            row: dict[str, Any] = {
                "regime_id": REGIME_ID,
                "geography_id": geography_id,
                "geography_name": names[geography_id],
                "analysis_year": year,
            }
            for indicator in INDICATORS:
                row[indicator] = values.get((geography_id, year, indicator), "")
            output.append(row)
    if len(output) != 19 * len(YEARS):
        raise RuntimeError("M10 wide frame did not produce exact 19x8 rows")
    return output


def unique_join(values: list[str]) -> str:
    return "|".join(sorted({value for value in values if value != ""}))


def build_coverage(long_rows: list[dict[str, str]], geography_ids: list[str], assignments: dict[str, str]) -> list[dict[str, Any]]:
    by_indicator: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in long_rows:
        by_indicator[row["indicator_id"]].append(row)

    total_cells = len(geography_ids) * len(YEARS)
    output: list[dict[str, Any]] = []
    for indicator in INDICATORS:
        rows = by_indicator.get(indicator, [])
        counts_by_year = Counter(int(row["analysis_year"]) for row in rows)
        present_cells = len(rows)
        exact_years = [year for year in YEARS if counts_by_year.get(year, 0) == len(geography_ids)]
        years_present = sorted(counts_by_year)
        output.append(
            {
                "indicator_id": indicator,
                "source_artifact": assignments[indicator],
                "present_cells": present_cells,
                "total_possible_cells": total_cells,
                "coverage_rate": f"{present_cells / total_cells:.8f}",
                "missing_cells": total_cells - present_cells,
                "first_year": min(years_present) if years_present else "",
                "last_year": max(years_present) if years_present else "",
                "years_present_count": len(years_present),
                "years_present": "|".join(str(year) for year in years_present),
                "exact_19_geography_year_count": len(exact_years),
                "exact_19_geography_years": "|".join(str(year) for year in exact_years),
                "coverage_by_year_json": json.dumps({str(year): counts_by_year.get(year, 0) for year in YEARS}, sort_keys=True, separators=(",", ":")),
                "units": unique_join([row["unit"] for row in rows]),
                "claim_types": unique_join([row["claim_type"] for row in rows]),
                "comparable_values": unique_join([row["comparable"] for row in rows]) or "blank_only",
                "methodology_versions": unique_join([row["methodology_version"] for row in rows]),
                "price_bases": unique_join([row["price_basis"] for row in rows]),
                "reference_period_patterns": unique_join([row["reference_period_pattern"] for row in rows]),
            }
        )
    return output


def build_metadata(registry: dict[str, dict[str, str]], assignments: dict[str, str]) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for indicator in INDICATORS:
        source = registry[indicator]
        output.append(
            {
                "indicator_id": indicator,
                "name": source.get("name", ""),
                "domain": source.get("domain", ""),
                "definition": source.get("definition", ""),
                "registry_unit": source.get("unit", ""),
                "registry_frequency": source.get("frequency", ""),
                "allowed_claim_types": source.get("allowed_claim_types", ""),
                "source_priority": source.get("source_priority", ""),
                "source_artifact": assignments[indicator],
                "m10_semantic_caution": INDICATOR_CAUTIONS[indicator],
            }
        )
    return output


def main() -> int:
    geography_ids, names = load_geographies()
    registry = load_indicator_registry()
    assignments = source_assignment()
    long_rows, source_hashes, suppressed_skipped = collect_long_rows(set(geography_ids))

    observed_indicator_set = {row["indicator_id"] for row in long_rows}
    missing_indicators = sorted(set(INDICATORS) - observed_indicator_set)
    if missing_indicators:
        raise RuntimeError(f"M10 preregistered indicators have no selected observations: {missing_indicators}")

    wide_rows = build_wide(long_rows, geography_ids, names)
    coverage_rows = build_coverage(long_rows, geography_ids, assignments)
    metadata_rows = build_metadata(registry, assignments)

    long_path = OUT_DIR / "m10-panel-long.csv"
    wide_path = OUT_DIR / "m10-panel-wide.csv"
    coverage_path = OUT_DIR / "m10-indicator-coverage.csv"
    metadata_path = OUT_DIR / "m10-indicator-metadata.csv"

    write_csv(
        long_path,
        [
            "regime_id",
            "geography_id",
            "analysis_year",
            "indicator_id",
            "value_numeric",
            "unit",
            "claim_type",
            "observation_id",
            "provenance_id",
            "time_start",
            "time_end",
            "reference_period_pattern",
            "comparable",
            "methodology_version",
            "price_basis",
            "source_artifact",
            "source_path",
            "source_notes",
        ],
        long_rows,
    )
    write_csv(wide_path, ["regime_id", "geography_id", "geography_name", "analysis_year", *INDICATORS], wide_rows)
    write_csv(
        coverage_path,
        [
            "indicator_id",
            "source_artifact",
            "present_cells",
            "total_possible_cells",
            "coverage_rate",
            "missing_cells",
            "first_year",
            "last_year",
            "years_present_count",
            "years_present",
            "exact_19_geography_year_count",
            "exact_19_geography_years",
            "coverage_by_year_json",
            "units",
            "claim_types",
            "comparable_values",
            "methodology_versions",
            "price_bases",
            "reference_period_patterns",
        ],
        coverage_rows,
    )
    write_csv(
        metadata_path,
        [
            "indicator_id",
            "name",
            "domain",
            "definition",
            "registry_unit",
            "registry_frequency",
            "allowed_claim_types",
            "source_priority",
            "source_artifact",
            "m10_semantic_caution",
        ],
        metadata_rows,
    )

    total_possible = len(geography_ids) * len(YEARS) * len(INDICATORS)
    present = len(long_rows)
    complete_indicators = [row["indicator_id"] for row in coverage_rows if int(row["present_cells"]) == len(geography_ids) * len(YEARS)]
    sparse_indicators = [row["indicator_id"] for row in coverage_rows if int(row["present_cells"]) < len(geography_ids) * len(YEARS)]

    manifest = {
        "schema": "ranah-observatory/milestone10-analytical-panel/v1",
        "phase": "final_analytical_research_engine",
        "milestone": 10,
        "regime_id": REGIME_ID,
        "geography_count": len(geography_ids),
        "geography_ids": geography_ids,
        "start_year": START_YEAR,
        "end_year": END_YEAR,
        "years": YEARS,
        "year_count": len(YEARS),
        "indicator_count": len(INDICATORS),
        "indicator_ids": INDICATORS,
        "wide_row_count": len(wide_rows),
        "long_observation_count": present,
        "total_possible_indicator_cells": total_possible,
        "missing_indicator_cells": total_possible - present,
        "complete_2018_2025_indicator_ids": complete_indicators,
        "sparse_indicator_ids": sparse_indicators,
        "suppressed_source_rows_skipped": suppressed_skipped,
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
        "source_files": {path: digest for path, digest in sorted(source_hashes.items())},
        "registry_files": {
            str(GEOGRAPHY_REGISTRY.relative_to(ROOT)): sha256(GEOGRAPHY_REGISTRY),
            str(INDICATOR_REGISTRY.relative_to(ROOT)): sha256(INDICATOR_REGISTRY),
        },
        "outputs": {
            "long": {"path": str(long_path.relative_to(ROOT)), "sha256": sha256(long_path)},
            "wide": {"path": str(wide_path.relative_to(ROOT)), "sha256": sha256(wide_path)},
            "coverage": {"path": str(coverage_path.relative_to(ROOT)), "sha256": sha256(coverage_path)},
            "metadata": {"path": str(metadata_path.relative_to(ROOT)), "sha256": sha256(metadata_path)},
        },
        "milestone10_complete": True,
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
