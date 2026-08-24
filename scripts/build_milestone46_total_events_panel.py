#!/usr/bin/env python3
"""Materialize the M45 total-event candidate and integrate its modern slice into Panel v3.

M46 preserves Panel v2 field-for-field, commits the full 2010-2024 BNPB
canonical separate layer, and appends only 2018-2024 to the current-entity
analytical regime. 2025 remains structurally missing rather than zero-filled.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from scripts.build_milestone45_bnpb_total_events_candidate import (
    DEFAULT_GEOGRAPHIES,
    DEFAULT_M44,
    DEFAULT_PACKAGE_METADATA,
    DEFAULT_SOURCE,
    build as build_m45,
    write_csv as write_m45_csv,
)

ROOT = Path(__file__).resolve().parents[1]
M45_MANIFEST = ROOT / "data/manifests/milestone45_bnpb_total_events_candidate.json"
M28_MANIFEST = ROOT / "data/manifests/milestone28_panel_integration.json"
M28_LONG = ROOT / "data/analysis/engine/panel_v2/m28-panel-long.csv"
M28_META = ROOT / "data/analysis/engine/panel_v2/m28-indicator-metadata.csv"
INDICATORS_REGISTRY = ROOT / "data/registries/indicators.csv"
GEOGRAPHIES = ROOT / "data/registries/geographies.csv"

CANONICAL_REL = Path("data/processed/bnpb/total_events/bnpb-total-events-canonical-observations.csv")
PROVENANCE_REL = Path("data/processed/bnpb/total_events/bnpb-total-events-canonical-provenance.json")
PANEL_LONG_REL = Path("data/analysis/engine/panel_v3/m46-panel-long.csv")
PANEL_WIDE_REL = Path("data/analysis/engine/panel_v3/m46-panel-wide.csv")
PANEL_COVERAGE_REL = Path("data/analysis/engine/panel_v3/m46-indicator-coverage.csv")
PANEL_META_REL = Path("data/analysis/engine/panel_v3/m46-indicator-metadata.csv")
MANIFEST_REL = Path("data/manifests/milestone46_total_events_panel_integration.json")

REGIME_ID = "sumbar_current_kabkota_2018_2025_v1"
YEARS = list(range(2018, 2026))
INDICATOR_ID = "total_disaster_events"

LONG_FIELDS = [
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
]
COVERAGE_FIELDS = [
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
]
META_FIELDS = [
    "indicator_id",
    "name",
    "domain",
    "definition",
    "registry_unit",
    "registry_frequency",
    "allowed_claim_types",
    "source_priority",
    "source_artifact",
    "semantic_caution",
    "registry_source",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def unique_join(values: list[str]) -> str:
    return "|".join(sorted({value for value in values if value}))


def current_geographies() -> tuple[list[str], dict[str, str]]:
    rows = read_csv(GEOGRAPHIES)
    selected = [
        row
        for row in rows
        if row.get("parent_geography_id") == "idn.13"
        and row.get("geography_level") in {"regency", "city"}
        and row.get("status") == "current"
    ]
    ids = sorted(row["geography_id"] for row in selected)
    if len(ids) != 19 or len(set(ids)) != 19:
        raise ValueError(f"expected 19 current Sumbar entities, got {len(ids)}")
    return ids, {row["geography_id"]: row["canonical_name"] for row in selected}


def build(output_root: Path) -> dict[str, Any]:
    m45_manifest = json.loads(M45_MANIFEST.read_text(encoding="utf-8"))
    m28_manifest = json.loads(M28_MANIFEST.read_text(encoding="utf-8"))
    if m45_manifest.get("milestone") != 45 or not m45_manifest.get("qualification", {}).get("candidate_artifact_reproducible"):
        raise ValueError("M45 candidate prerequisite is not frozen/reproducible")
    if not m28_manifest.get("integration_success") or m28_manifest.get("long_observation_count") != 2679:
        raise ValueError("Panel v2 prerequisite is not frozen at 2679 observations")
    if sha256(M28_LONG) != m28_manifest["outputs"]["long"]["sha256"]:
        raise ValueError("Panel v2 long checksum drift")

    registry_rows = read_csv(INDICATORS_REGISTRY)
    registry_by_id = {row["indicator_id"]: row for row in registry_rows}
    total_registry = registry_by_id.get(INDICATOR_ID)
    if total_registry is None or total_registry.get("status") != "qualified":
        raise ValueError("total_disaster_events must be qualified in the global indicator registry before M46 build")

    canonical_rows, provenance, m45_summary = build_m45(
        DEFAULT_SOURCE,
        DEFAULT_GEOGRAPHIES,
        DEFAULT_PACKAGE_METADATA,
        DEFAULT_M44,
    )
    canonical_path = output_root / CANONICAL_REL
    provenance_path = output_root / PROVENANCE_REL
    write_m45_csv(canonical_path, canonical_rows)
    provenance_path.parent.mkdir(parents=True, exist_ok=True)
    provenance_path.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    canonical_sha = sha256(canonical_path)
    provenance_sha = sha256(provenance_path)
    if canonical_sha != m45_manifest["candidate_artifact"]["sha256"]:
        raise ValueError("M45 canonical candidate fingerprint drift")
    if provenance_sha != m45_manifest["candidate_artifact"]["provenance_sha256"]:
        raise ValueError("M45 canonical provenance fingerprint drift")

    base_rows = read_csv(M28_LONG)
    if len(base_rows) != 2679 or list(base_rows[0]) != LONG_FIELDS:
        raise ValueError("Panel v2 long footprint/schema drift")
    base_fingerprints = {tuple(row[field] for field in LONG_FIELDS) for row in base_rows}
    if len(base_fingerprints) != len(base_rows):
        raise ValueError("Panel v2 rows are not field-unique")

    geography_ids, names = current_geographies()
    modern_rows = []
    for row in canonical_rows:
        year = int(row["time_start"][:4])
        if year < 2018 or year > 2024:
            continue
        if row["geography_id"] not in geography_ids:
            raise ValueError(f"candidate row outside current Sumbar entity set: {row['geography_id']}")
        modern_rows.append(
            {
                "regime_id": REGIME_ID,
                "geography_id": row["geography_id"],
                "analysis_year": str(year),
                "indicator_id": INDICATOR_ID,
                "value_numeric": str(row["value_numeric"]),
                "unit": row["unit"],
                "claim_type": row["claim_type"],
                "observation_id": row["observation_id"],
                "provenance_id": row["provenance_id"],
                "time_start": row["time_start"],
                "time_end": row["time_end"],
                "reference_period_pattern": "calendar_year",
                "comparable": "",
                "methodology_version": row["methodology_version"],
                "price_basis": "",
                "source_artifact": "bnpb_total_events_canonical_m46",
                "source_path": str(CANONICAL_REL),
                "source_notes": row["notes"],
            }
        )
    if len(modern_rows) != 133:
        raise ValueError(f"expected 133 M46 modern-slice rows, got {len(modern_rows)}")
    by_year = Counter(int(row["analysis_year"]) for row in modern_rows)
    if by_year != Counter({year: 19 for year in range(2018, 2025)}):
        raise ValueError(f"M46 modern-slice year coverage drift: {dict(sorted(by_year.items()))}")
    if any(row["comparable"] for row in modern_rows):
        raise ValueError("M46 total-event rows must keep comparable unset")
    if not all("exact_polygon_harmonization=not_proven" in row["source_notes"] for row in modern_rows):
        raise ValueError("M46 total-event rows lost exact-polygon caveat")

    combined = [dict(row) for row in base_rows] + modern_rows
    seen = set()
    for row in combined:
        key = (row["geography_id"], int(row["analysis_year"]), row["indicator_id"])
        if key in seen:
            raise ValueError(f"Panel v3 duplicate geography-year-indicator key: {key}")
        seen.add(key)

    indicator_ids = list(m28_manifest["indicator_ids"]) + [INDICATOR_ID]
    if len(indicator_ids) != 23 or len(set(indicator_ids)) != 23:
        raise ValueError("Panel v3 must contain exactly 23 unique indicators")
    combined.sort(key=lambda row: (row["geography_id"], int(row["analysis_year"]), indicator_ids.index(row["indicator_id"])))
    preserved = {
        tuple(row[field] for field in LONG_FIELDS)
        for row in combined
        if row["indicator_id"] != INDICATOR_ID
    } == base_fingerprints
    if not preserved:
        raise ValueError("Panel v2 rows were not preserved field-for-field")
    if len(combined) != 2812:
        raise ValueError(f"Panel v3 expected 2812 long rows, got {len(combined)}")

    long_path = output_root / PANEL_LONG_REL
    write_csv(long_path, LONG_FIELDS, combined)

    values = {
        (row["geography_id"], int(row["analysis_year"]), row["indicator_id"]): row["value_numeric"]
        for row in combined
    }
    wide_rows = []
    for geography_id in geography_ids:
        for year in YEARS:
            output: dict[str, Any] = {
                "regime_id": REGIME_ID,
                "geography_id": geography_id,
                "geography_name": names[geography_id],
                "analysis_year": year,
            }
            for indicator in indicator_ids:
                output[indicator] = values.get((geography_id, year, indicator), "")
            wide_rows.append(output)
    if len(wide_rows) != 152:
        raise ValueError("Panel v3 wide row count must be 152")
    if any(row[INDICATOR_ID] for row in wide_rows if row["analysis_year"] == 2025):
        raise ValueError("2025 total disaster events must remain missing, not zero-filled")
    wide_path = output_root / PANEL_WIDE_REL
    write_csv(wide_path, ["regime_id", "geography_id", "geography_name", "analysis_year", *indicator_ids], wide_rows)

    grouped: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for row in combined:
        grouped[row["indicator_id"]].append(row)
    coverage_rows = []
    for indicator in indicator_ids:
        rows = grouped[indicator]
        counts = Counter(int(row["analysis_year"]) for row in rows)
        years_present = sorted(counts)
        exact_years = [year for year in YEARS if counts.get(year, 0) == 19]
        coverage_rows.append(
            {
                "indicator_id": indicator,
                "source_artifact": unique_join([row["source_artifact"] for row in rows]),
                "present_cells": len(rows),
                "total_possible_cells": 152,
                "coverage_rate": f"{len(rows) / 152:.8f}",
                "missing_cells": 152 - len(rows),
                "first_year": min(years_present) if years_present else "",
                "last_year": max(years_present) if years_present else "",
                "years_present_count": len(years_present),
                "years_present": "|".join(map(str, years_present)),
                "exact_19_geography_year_count": len(exact_years),
                "exact_19_geography_years": "|".join(map(str, exact_years)),
                "coverage_by_year_json": json.dumps({str(year): counts.get(year, 0) for year in YEARS}, sort_keys=True, separators=(",", ":")),
                "units": unique_join([row["unit"] for row in rows]),
                "claim_types": unique_join([row["claim_type"] for row in rows]),
                "comparable_values": unique_join([row["comparable"] for row in rows]) or "blank_only",
                "methodology_versions": unique_join([row["methodology_version"] for row in rows]),
                "price_bases": unique_join([row["price_basis"] for row in rows]),
                "reference_period_patterns": unique_join([row["reference_period_pattern"] for row in rows]),
            }
        )
    coverage_path = output_root / PANEL_COVERAGE_REL
    write_csv(coverage_path, COVERAGE_FIELDS, coverage_rows)

    base_meta = read_csv(M28_META)
    if len(base_meta) != 22 or list(base_meta[0]) != META_FIELDS:
        raise ValueError("Panel v2 metadata footprint/schema drift")
    total_meta = {
        "indicator_id": INDICATOR_ID,
        "name": total_registry["name"],
        "domain": total_registry["domain"],
        "definition": total_registry["definition"],
        "registry_unit": total_registry["unit"],
        "registry_frequency": total_registry["frequency"],
        "allowed_claim_types": total_registry["allowed_claim_types"],
        "source_priority": total_registry["source_priority"],
        "source_artifact": "bnpb_total_events_canonical_m46",
        "semantic_caution": (
            "BNPB recorded all-disaster event counts; 2018-2024 is integrated into Panel v3. "
            "Exact historical-to-current polygon harmonization is not proven; reporting intensity, "
            "classification practice, and release revisions remain material. 2025 is missing, not zero."
        ),
        "registry_source": "central_indicators_registry_m46",
    }
    metadata_rows = [dict(row) for row in base_meta] + [total_meta]
    metadata_path = output_root / PANEL_META_REL
    write_csv(metadata_path, META_FIELDS, metadata_rows)

    output_hashes = {
        "canonical": {"path": str(CANONICAL_REL), "sha256": canonical_sha},
        "canonical_provenance": {"path": str(PROVENANCE_REL), "sha256": provenance_sha},
        "long": {"path": str(PANEL_LONG_REL), "sha256": sha256(long_path)},
        "wide": {"path": str(PANEL_WIDE_REL), "sha256": sha256(wide_path)},
        "coverage": {"path": str(PANEL_COVERAGE_REL), "sha256": sha256(coverage_path)},
        "metadata": {"path": str(PANEL_META_REL), "sha256": sha256(metadata_path)},
    }
    manifest = {
        "schema": "ranah-observatory/milestone46-total-events-panel-integration/v1",
        "milestone": 46,
        "integration_success": True,
        "regime_id": REGIME_ID,
        "start_year": 2018,
        "end_year": 2025,
        "year_count": 8,
        "geography_count": 19,
        "base_panel": "M28 Panel v2",
        "base_panel_preserved_field_exact": preserved,
        "base_observation_count": 2679,
        "added_indicator_id": INDICATOR_ID,
        "added_observation_count": 133,
        "long_observation_count": len(combined),
        "indicator_count": len(indicator_ids),
        "indicator_ids": indicator_ids,
        "wide_row_count": len(wide_rows),
        "total_event_full_canonical_period": [2010, 2024],
        "total_event_panel_period": [2018, 2024],
        "total_event_2025_state": "missing_not_zero",
        "total_event_comparable_flag": "unset",
        "exact_polygon_harmonization_proven": False,
        "zero_fill_performed": False,
        "imputation_performed": False,
        "cross_indicator_aggregation_performed": False,
        "causal_analysis_performed": False,
        "m45_candidate_sha256": m45_manifest["candidate_artifact"]["sha256"],
        "m45_candidate_year_sums": m45_summary["year_sums"],
        "outputs": output_hashes,
    }
    manifest_path = output_root / MANIFEST_REL
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=ROOT)
    args = parser.parse_args()
    manifest = build(args.output_root)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
