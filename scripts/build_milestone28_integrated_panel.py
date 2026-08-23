#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "data/manifests/milestone28_panel_integration_contract.json"
M10_MANIFEST = ROOT / "data/manifests/milestone10_analytical_panel.json"
M28_MANIFEST = ROOT / "data/manifests/milestone28_stage2b_full_history.json"
M28_REPRO = ROOT / "data/manifests/milestone28_stage2b_offline_reproducibility.json"
M10_LONG = ROOT / "data/analysis/engine/panel_v1/m10-panel-long.csv"
M10_META = ROOT / "data/analysis/engine/panel_v1/m10-indicator-metadata.csv"
M28_OBS = ROOT / "data/analysis/engine/broader_panel_v1/m28-broader-panel-observations.csv"
M28_PROV = ROOT / "data/analysis/engine/broader_panel_v1/m28-broader-panel-provenance.csv"
M28_EXTENSION = ROOT / "data/registries/milestone28_indicator_extension.csv"
GEOS = ROOT / "data/registries/geographies.csv"
OUT_DIR = ROOT / "data/analysis/engine/panel_v2"
OUT_LONG = OUT_DIR / "m28-panel-long.csv"
OUT_WIDE = OUT_DIR / "m28-panel-wide.csv"
OUT_COVERAGE = OUT_DIR / "m28-indicator-coverage.csv"
OUT_META = OUT_DIR / "m28-indicator-metadata.csv"
OUT_MANIFEST = ROOT / "data/manifests/milestone28_panel_integration.json"
REGIME_ID = "sumbar_current_kabkota_2018_2025_v1"
YEARS = list(range(2018, 2026))
M28_INDICATORS = [
    "real_grdp_per_capita",
    "morbidity_rate",
    "jkn_membership_coverage",
    "internet_access_age5plus",
    "adequate_sanitation_access",
    "adequate_drinking_water_access",
    "dependency_ratio",
]
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


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


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


def load_geographies() -> tuple[list[str], dict[str, str]]:
    rows = read_csv(GEOS)
    selected = [
        row
        for row in rows
        if row.get("parent_geography_id") == "idn.13"
        and row.get("geography_level") in {"regency", "city"}
        and row.get("status") == "current"
    ]
    ids = sorted(row["geography_id"] for row in selected)
    names = {row["geography_id"]: row["canonical_name"] for row in selected}
    if len(ids) != 19 or len(set(ids)) != 19:
        raise ValueError(f"expected 19 current Sumbar kabupaten/kota, got {len(ids)}")
    return ids, names


def unique_join(values: list[str]) -> str:
    return "|".join(sorted({value for value in values if value}))


def main() -> int:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    m10_manifest = json.loads(M10_MANIFEST.read_text(encoding="utf-8"))
    m28_manifest = json.loads(M28_MANIFEST.read_text(encoding="utf-8"))
    m28_repro = json.loads(M28_REPRO.read_text(encoding="utf-8"))

    if contract.get("schema") != "ranah-observatory/milestone28-panel-integration-contract/v1":
        raise ValueError("M28 integration contract schema drift")
    if m10_manifest.get("milestone10_complete") is not True or m10_manifest.get("regime_id") != REGIME_ID:
        raise ValueError("M10 base panel is not the required complete regime")
    if m28_manifest.get("full_history_success") is not True or m28_manifest.get("promoted_observation_count") != 931:
        raise ValueError("M28 full-history prerequisite is not qualified")
    if m28_repro.get("rebuild_success") is not True or m28_repro.get("all_outputs_byte_identical") is not True:
        raise ValueError("M28 offline reproducibility prerequisite is not qualified")
    if sha256(M10_LONG) != m10_manifest["outputs"]["long"]["sha256"]:
        raise ValueError("M10 authoritative long panel checksum drift")
    if sha256(M28_OBS) != m28_manifest["observations_csv"]["sha256"]:
        raise ValueError("M28 authoritative observation checksum drift")
    if sha256(M28_PROV) != m28_manifest["provenance_csv"]["sha256"]:
        raise ValueError("M28 provenance checksum drift")

    geography_ids, names = load_geographies()
    m10_rows = read_csv(M10_LONG)
    if len(m10_rows) != 1748:
        raise ValueError(f"expected 1748 M10 observations, got {len(m10_rows)}")
    if list(m10_rows[0].keys()) != LONG_FIELDS:
        raise ValueError("M10 long schema drift")

    m28_obs = read_csv(M28_OBS)
    m28_prov = read_csv(M28_PROV)
    if len(m28_obs) != 931 or len(m28_prov) != 49:
        raise ValueError(f"M28 source footprint drift: obs={len(m28_obs)} prov={len(m28_prov)}")
    prov_by_key = {(row["indicator_id"], int(row["year"])): row for row in m28_prov}
    if len(prov_by_key) != 49:
        raise ValueError("M28 provenance indicator-year keys are not unique")

    m10_indicator_ids = list(m10_manifest["indicator_ids"])
    if set(m10_indicator_ids) & set(M28_INDICATORS):
        raise ValueError("M28 indicators unexpectedly overlap M10 indicator IDs")
    indicator_ids = m10_indicator_ids + M28_INDICATORS
    if len(indicator_ids) != 22 or len(set(indicator_ids)) != 22:
        raise ValueError("combined indicator footprint must be exactly 22 unique IDs")

    m28_rows: list[dict[str, str]] = []
    seen_m28_keys: set[tuple[str, int, str]] = set()
    source_projection_checks = 0
    source_backcast_checks = 0
    for source in m28_obs:
        indicator = source["indicator_id"]
        geography_id = source["geography_id"]
        year = int(source["year"])
        if indicator not in M28_INDICATORS:
            raise ValueError(f"unexpected M28 indicator: {indicator}")
        if geography_id not in geography_ids or year not in YEARS:
            raise ValueError(f"M28 row outside target regime: {indicator} {geography_id} {year}")
        key = (geography_id, year, indicator)
        if key in seen_m28_keys:
            raise ValueError(f"duplicate M28 geography-year-indicator key: {key}")
        seen_m28_keys.add(key)
        provenance = prov_by_key.get((indicator, year))
        if provenance is None:
            raise ValueError(f"missing M28 provenance for {indicator} {year}")
        if source["claim_type"] != provenance["claim_type"] or source["methodology_regime"] != provenance["methodology_regime"]:
            raise ValueError(f"M28 observation/provenance semantic mismatch for {indicator} {year}")
        if source["raw_snapshot_sha256"] != provenance["raw_snapshot_sha256"]:
            raise ValueError(f"M28 raw checksum mismatch for {indicator} {year}")

        if indicator == "adequate_drinking_water_access" and year in {2019, 2020}:
            if source["claim_type"] != "backcast_estimate":
                raise ValueError("2019-2020 drinking-water observations must remain backcast_estimate")
            source_backcast_checks += 1
        if indicator == "adequate_drinking_water_access" and year == 2018:
            raise ValueError("2018 drinking-water row must not exist in SDGs-aligned regime")
        if indicator == "dependency_ratio":
            expected_claim = "observed_census_anchor" if year == 2020 else "model_estimate_projection"
            if source["claim_type"] != expected_claim:
                raise ValueError(f"dependency-ratio claim-type drift in {year}")
            if year > 2020:
                source_projection_checks += 1

        var_id = source["source_var_id"]
        price_basis = "constant_2010" if indicator == "real_grdp_per_capita" else ""
        m28_rows.append(
            {
                "regime_id": REGIME_ID,
                "geography_id": geography_id,
                "analysis_year": str(year),
                "indicator_id": indicator,
                "value_numeric": source["value"],
                "unit": source["unit"],
                "claim_type": source["claim_type"],
                "observation_id": f"m28:bps:{var_id}:{year}:{source['bps_code']}",
                "provenance_id": f"m28:bps:{var_id}:{year}",
                "time_start": "",
                "time_end": "",
                "reference_period_pattern": "source_annual_period_unspecified_within_year",
                "comparable": "",
                "methodology_version": source["methodology_regime"],
                "price_basis": price_basis,
                "source_artifact": "m28_bps_broader_panel",
                "source_path": source["raw_snapshot_path"],
                "source_notes": "Exact BPS source definition, note, selector, update metadata, claim type, and methodology regime are preserved in m28-broader-panel-provenance.csv.",
            }
        )

    if len(m28_rows) != 931 or len(seen_m28_keys) != 931:
        raise ValueError("M28 integration row footprint drift")
    if source_backcast_checks != 38 or source_projection_checks != 76:
        raise ValueError(f"M28 methodology check footprint drift: backcast={source_backcast_checks} projection={source_projection_checks}")

    # Base rows are copied field-for-field and never rewritten semantically.
    base_fingerprints = {tuple(row[field] for field in LONG_FIELDS) for row in m10_rows}
    if len(base_fingerprints) != len(m10_rows):
        raise ValueError("M10 long rows are not field-unique")

    combined = [dict(row) for row in m10_rows] + m28_rows
    seen_keys: set[tuple[str, int, str]] = set()
    for row in combined:
        key = (row["geography_id"], int(row["analysis_year"]), row["indicator_id"])
        if key in seen_keys:
            raise ValueError(f"combined duplicate geography-year-indicator key: {key}")
        seen_keys.add(key)

    combined.sort(key=lambda row: (row["geography_id"], int(row["analysis_year"]), indicator_ids.index(row["indicator_id"])))
    combined_base_fingerprints = {
        tuple(row[field] for field in LONG_FIELDS)
        for row in combined
        if row["source_artifact"] != "m28_bps_broader_panel"
    }
    base_preserved = combined_base_fingerprints == base_fingerprints
    if not base_preserved:
        raise ValueError("M10 rows were not preserved field-for-field in Panel v2")

    # Verify all M28 source values and semantic labels appear unchanged in the union.
    combined_m28 = {
        (row["geography_id"], int(row["analysis_year"]), row["indicator_id"]): row
        for row in combined
        if row["source_artifact"] == "m28_bps_broader_panel"
    }
    source_values_preserved = True
    for source in m28_obs:
        key = (source["geography_id"], int(source["year"]), source["indicator_id"])
        target = combined_m28.get(key)
        if target is None or target["value_numeric"] != source["value"] or target["unit"] != source["unit"] or target["claim_type"] != source["claim_type"] or target["methodology_version"] != source["methodology_regime"]:
            source_values_preserved = False
            break
    if not source_values_preserved:
        raise ValueError("M28 values/semantic labels changed during panel integration")

    values = {(row["geography_id"], int(row["analysis_year"]), row["indicator_id"]): row["value_numeric"] for row in combined}
    wide_rows: list[dict[str, Any]] = []
    for geography_id in geography_ids:
        for year in YEARS:
            row: dict[str, Any] = {
                "regime_id": REGIME_ID,
                "geography_id": geography_id,
                "geography_name": names[geography_id],
                "analysis_year": year,
            }
            for indicator in indicator_ids:
                row[indicator] = values.get((geography_id, year, indicator), "")
            wide_rows.append(row)
    if len(wide_rows) != 152:
        raise ValueError("Panel v2 wide row count must remain 152")

    by_indicator: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in combined:
        by_indicator[row["indicator_id"]].append(row)
    total_cells_per_indicator = 19 * 8
    coverage_rows: list[dict[str, Any]] = []
    for indicator in indicator_ids:
        rows = by_indicator.get(indicator, [])
        counts = Counter(int(row["analysis_year"]) for row in rows)
        exact_years = [year for year in YEARS if counts.get(year, 0) == 19]
        years_present = sorted(counts)
        coverage_rows.append(
            {
                "indicator_id": indicator,
                "source_artifact": unique_join([row["source_artifact"] for row in rows]),
                "present_cells": len(rows),
                "total_possible_cells": total_cells_per_indicator,
                "coverage_rate": f"{len(rows) / total_cells_per_indicator:.8f}",
                "missing_cells": total_cells_per_indicator - len(rows),
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

    m10_meta = read_csv(M10_META)
    if len(m10_meta) != 15:
        raise ValueError("M10 metadata footprint drift")
    extension = read_csv(M28_EXTENSION)
    if len(extension) != 7 or {row["indicator_id"] for row in extension} != set(M28_INDICATORS):
        raise ValueError("M28 indicator extension must cover exactly seven added indicators")
    metadata_rows: list[dict[str, str]] = []
    for row in m10_meta:
        metadata_rows.append(
            {
                "indicator_id": row["indicator_id"],
                "name": row["name"],
                "domain": row["domain"],
                "definition": row["definition"],
                "registry_unit": row["registry_unit"],
                "registry_frequency": row["registry_frequency"],
                "allowed_claim_types": row["allowed_claim_types"],
                "source_priority": row["source_priority"],
                "source_artifact": row["source_artifact"],
                "semantic_caution": row["m10_semantic_caution"],
                "registry_source": "central_indicators_registry_via_m10",
            }
        )
    extension_by_id = {row["indicator_id"]: row for row in extension}
    for indicator in M28_INDICATORS:
        row = extension_by_id[indicator]
        metadata_rows.append(
            {
                "indicator_id": indicator,
                "name": row["name"],
                "domain": row["domain"],
                "definition": row["definition"],
                "registry_unit": row["registry_unit"],
                "registry_frequency": row["registry_frequency"],
                "allowed_claim_types": row["allowed_claim_types"],
                "source_priority": row["source_priority"],
                "source_artifact": "m28_bps_broader_panel",
                "semantic_caution": row["m28_semantic_caution"],
                "registry_source": row["registry_basis"],
            }
        )

    if len(combined) != 2679 or len(seen_keys) != 2679:
        raise ValueError(f"combined long footprint mismatch: {len(combined)}")
    total_possible = 19 * 8 * 22
    missing = total_possible - len(combined)
    if total_possible != 3344 or missing != 665:
        raise ValueError(f"combined possible/missing footprint mismatch: possible={total_possible} missing={missing}")

    complete = [row["indicator_id"] for row in coverage_rows if int(row["present_cells"]) == 152]
    sparse = [row["indicator_id"] for row in coverage_rows if int(row["present_cells"]) < 152]
    if "internet_access_age5plus" not in complete or "adequate_sanitation_access" not in complete:
        raise ValueError("expected fully balanced M28 internet/sanitation indicators are not complete")

    write_csv(OUT_LONG, LONG_FIELDS, combined)
    write_csv(OUT_WIDE, ["regime_id", "geography_id", "geography_name", "analysis_year", *indicator_ids], wide_rows)
    coverage_fields = [
        "indicator_id", "source_artifact", "present_cells", "total_possible_cells", "coverage_rate", "missing_cells",
        "first_year", "last_year", "years_present_count", "years_present", "exact_19_geography_year_count",
        "exact_19_geography_years", "coverage_by_year_json", "units", "claim_types", "comparable_values",
        "methodology_versions", "price_bases", "reference_period_patterns",
    ]
    write_csv(OUT_COVERAGE, coverage_fields, coverage_rows)
    meta_fields = [
        "indicator_id", "name", "domain", "definition", "registry_unit", "registry_frequency", "allowed_claim_types",
        "source_priority", "source_artifact", "semantic_caution", "registry_source",
    ]
    write_csv(OUT_META, meta_fields, metadata_rows)

    manifest = {
        "schema": "ranah-observatory/milestone28-integrated-panel/v1",
        "milestone": 28,
        "regime_id": REGIME_ID,
        "geography_count": 19,
        "start_year": 2018,
        "end_year": 2025,
        "year_count": 8,
        "wide_row_count": 152,
        "base_indicator_count": 15,
        "added_indicator_count": 7,
        "indicator_count": 22,
        "indicator_ids": indicator_ids,
        "base_observation_count": len(m10_rows),
        "added_observation_count": len(m28_rows),
        "long_observation_count": len(combined),
        "total_possible_indicator_cells": total_possible,
        "missing_indicator_cells": missing,
        "m28_structured_missing_indicator_cells": 133,
        "duplicate_key_count": 0,
        "base_m10_rows_preserved_field_exact": base_preserved,
        "m28_values_claims_methodologies_preserved": source_values_preserved,
        "m28_drinking_water_backcast_row_count": source_backcast_checks,
        "m28_dependency_projection_row_count": source_projection_checks,
        "complete_2018_2025_indicator_ids": complete,
        "sparse_indicator_ids": sparse,
        "base_panel_overwritten": False,
        "global_window_shortening_performed": False,
        "imputation_performed": False,
        "forward_fill_performed": False,
        "backward_fill_performed": False,
        "zero_fill_missing_years_performed": False,
        "cross_indicator_aggregation_performed": False,
        "statistical_model_fit": False,
        "causal_analysis_performed": False,
        "monetary_wasted_potential_estimated": False,
        "source_files": {
            str(M10_LONG.relative_to(ROOT)): sha256(M10_LONG),
            str(M10_META.relative_to(ROOT)): sha256(M10_META),
            str(M28_OBS.relative_to(ROOT)): sha256(M28_OBS),
            str(M28_PROV.relative_to(ROOT)): sha256(M28_PROV),
            str(M28_EXTENSION.relative_to(ROOT)): sha256(M28_EXTENSION),
        },
        "prerequisite_manifests": {
            str(M10_MANIFEST.relative_to(ROOT)): sha256(M10_MANIFEST),
            str(M28_MANIFEST.relative_to(ROOT)): sha256(M28_MANIFEST),
            str(M28_REPRO.relative_to(ROOT)): sha256(M28_REPRO),
            str(CONTRACT.relative_to(ROOT)): sha256(CONTRACT),
        },
        "outputs": {
            "long": {"path": str(OUT_LONG.relative_to(ROOT)), "sha256": sha256(OUT_LONG)},
            "wide": {"path": str(OUT_WIDE.relative_to(ROOT)), "sha256": sha256(OUT_WIDE)},
            "coverage": {"path": str(OUT_COVERAGE.relative_to(ROOT)), "sha256": sha256(OUT_COVERAGE)},
            "metadata": {"path": str(OUT_META.relative_to(ROOT)), "sha256": sha256(OUT_META)},
        },
        "integration_success": True,
    }
    OUT_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "integration_success": True,
        "indicators": 22,
        "observations": len(combined),
        "missing_cells": missing,
        "complete_indicators": len(complete),
        "base_preserved": base_preserved,
        "m28_preserved": source_values_preserved,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
