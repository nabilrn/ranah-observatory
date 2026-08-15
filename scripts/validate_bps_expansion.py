#!/usr/bin/env python3
from __future__ import annotations

import csv
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SERIES = ROOT / "data" / "registries" / "bps_expansion_series.csv"
QUALIFICATIONS = ROOT / "data" / "registries" / "bps_expansion_qualification.csv"
GEOGRAPHY_MAP = ROOT / "data" / "registries" / "bps_expansion_geography_map.csv"
INDICATORS = ROOT / "data" / "registries" / "indicators.csv"
GEOGRAPHIES = ROOT / "data" / "registries" / "geographies.csv"

EXPECTED_SERIES = {
    "underemployment_regency",
    "inequality_gini",
    "agriculture_share_adhb",
    "manufacturing_share_adhb",
    "rice_yield_ksa",
    "export_value_port_loading",
    "population_sp2020",
}
TRANSFORMS = {
    "identity",
    "share_percent",
    "quintal_per_hectare_to_tonnes_per_hectare",
}
GEOGRAPHY_DIMENSIONS = {"vervar", "turvar", "constant_province"}
CLAIM_TYPES = {"observed", "derived"}
SCOPES = {"all_geographies", "province_only"}
DECISIONS = {"canonical_ready", "canonical_ready_province_only"}
UNITS = {"percent", "index", "tonnes_per_hectare", "usd", "persons"}
REFERENCE_RULES = {
    "calendar_month_august",
    "calendar_month_march",
    "calendar_month_september",
    "calendar_year",
}
MAPPING_TYPES = {"direct_current_code", "source_aggregate_alias", "source_dimension_alias"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def official_bps_url(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and (host == "bps.go.id" or host.endswith(".bps.go.id"))


def validate() -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    series = read_csv(SERIES)
    qualifications = read_csv(QUALIFICATIONS)
    geography_map = read_csv(GEOGRAPHY_MAP)
    indicators = {row["indicator_id"] for row in read_csv(INDICATORS)}
    geographies = {row["geography_id"]: row for row in read_csv(GEOGRAPHIES)}

    series_ids = [row["expansion_series_id"] for row in series]
    if set(series_ids) != EXPECTED_SERIES or len(series_ids) != len(EXPECTED_SERIES):
        errors.append(f"expansion series membership differs from reviewed first batch: {series_ids}")

    q_by_id: dict[str, dict[str, str]] = {}
    for line_no, row in enumerate(qualifications, start=2):
        prefix = f"{QUALIFICATIONS}:{line_no}"
        for field in (
            "qualification_id", "decision", "canonical_unit", "reference_period_rule",
            "source_universe", "method_version", "quality_flags_rule", "evidence_type",
            "evidence_url", "notes",
        ):
            if not row.get(field):
                errors.append(f"{prefix}: {field} is required")
        qid = row.get("qualification_id", "")
        if qid in q_by_id:
            errors.append(f"{prefix}: duplicate qualification_id {qid}")
        q_by_id[qid] = row
        if row.get("decision") not in DECISIONS:
            errors.append(f"{prefix}: unsupported decision {row.get('decision')!r}")
        if row.get("canonical_unit") not in UNITS:
            errors.append(f"{prefix}: unsupported canonical_unit {row.get('canonical_unit')!r}")
        if row.get("reference_period_rule") not in REFERENCE_RULES:
            errors.append(f"{prefix}: unsupported reference_period_rule {row.get('reference_period_rule')!r}")
        for url in [item.strip() for item in row.get("evidence_url", "").split("|") if item.strip()]:
            if not official_bps_url(url):
                errors.append(f"{prefix}: qualification evidence must be official BPS HTTPS URL: {url}")

    expected_qids = {
        "q_underemployment_august", "q_gini_march", "q_sector_share_adhb2010",
        "q_rice_yield_ksa", "q_export_port_loading", "q_population_sp2020",
    }
    if set(q_by_id) != expected_qids:
        errors.append(f"qualification membership differs from reviewed batch: {sorted(q_by_id)}")

    for line_no, row in enumerate(series, start=2):
        prefix = f"{SERIES}:{line_no}"
        for field in (
            "expansion_series_id", "indicator_id", "bps_var_id", "target_start_year",
            "target_end_year", "geography_dimension", "transform", "claim_type",
            "canonical_scope", "qualification_id", "canonical_promotion_status", "notes",
        ):
            if not row.get(field):
                errors.append(f"{prefix}: {field} is required")
        if row.get("indicator_id") not in indicators:
            errors.append(f"{prefix}: unknown canonical indicator {row.get('indicator_id')}")
        try:
            int(row.get("bps_var_id", ""))
            start = int(row.get("target_start_year", ""))
            end = int(row.get("target_end_year", ""))
        except ValueError:
            errors.append(f"{prefix}: BPS var and year fields must be integer-compatible")
            continue
        if start > end:
            errors.append(f"{prefix}: start year is after end year")
        if row.get("geography_dimension") not in GEOGRAPHY_DIMENSIONS:
            errors.append(f"{prefix}: unsupported geography_dimension {row.get('geography_dimension')!r}")
        if row.get("transform") not in TRANSFORMS:
            errors.append(f"{prefix}: unsupported transform {row.get('transform')!r}")
        if row.get("claim_type") not in CLAIM_TYPES:
            errors.append(f"{prefix}: unsupported claim_type {row.get('claim_type')!r}")
        if row.get("canonical_scope") not in SCOPES:
            errors.append(f"{prefix}: unsupported canonical_scope {row.get('canonical_scope')!r}")
        qualification = q_by_id.get(row.get("qualification_id", ""))
        if qualification is None:
            errors.append(f"{prefix}: unresolved qualification_id {row.get('qualification_id')}")
        else:
            expected_status = (
                "canonical_ready_province_only"
                if qualification["decision"] == "canonical_ready_province_only"
                else "canonical_ready"
            )
            if row.get("canonical_promotion_status") != expected_status:
                errors.append(
                    f"{prefix}: promotion {row.get('canonical_promotion_status')!r} disagrees with qualification decision"
                )
        if row.get("transform") == "share_percent":
            if not row.get("selected_vervar_id") or not row.get("denominator_vervar_id"):
                errors.append(f"{prefix}: share transform requires numerator and denominator vervar ids")
            if row.get("geography_dimension") != "turvar":
                errors.append(f"{prefix}: PDRB share geography must come from turvar")
            if row.get("claim_type") != "derived":
                errors.append(f"{prefix}: share transform must remain a derived claim")
        if row.get("transform") == "quintal_per_hectare_to_tonnes_per_hectare" and row.get("claim_type") != "derived":
            errors.append(f"{prefix}: rice unit conversion must remain a derived claim")
        if row.get("geography_dimension") == "constant_province" and row.get("canonical_scope") != "province_only":
            errors.append(f"{prefix}: constant province source must remain province_only")

    by_id = {row["expansion_series_id"]: row for row in series}
    if by_id.get("inequality_gini", {}).get("canonical_scope") != "province_only":
        errors.append("Gini expansion must canonicalize province only")
    if by_id.get("inequality_gini", {}).get("canonical_promotion_status") != "canonical_ready_province_only":
        errors.append("Gini expansion must retain province-only promotion state")
    if by_id.get("population_sp2020", {}).get("target_start_year") != "2020" or by_id.get("population_sp2020", {}).get("target_end_year") != "2020":
        errors.append("SP2020 expansion must be a single 2020 census anchor")
    if by_id.get("export_value_port_loading", {}).get("selected_vervar_id") != "13" or by_id.get("export_value_port_loading", {}).get("selected_turvar_id") != "420":
        errors.append("export expansion must select annual Jumlah / Nilai US$ dimensions")
    if by_id.get("rice_yield_ksa", {}).get("selected_turvar_id") != "244":
        errors.append("rice expansion must select productivity turvar 244")
    if by_id.get("underemployment_regency", {}).get("selected_turvar_id") != "1081":
        errors.append("underemployment expansion must select Setengah Pengangguran turvar 1081")

    map_keys: set[tuple[str, str]] = set()
    for line_no, row in enumerate(geography_map, start=2):
        prefix = f"{GEOGRAPHY_MAP}:{line_no}"
        key = (row.get("source_dimension", ""), row.get("bps_dimension_id", ""))
        if key in map_keys:
            errors.append(f"{prefix}: duplicate geography map key {key}")
        map_keys.add(key)
        if row.get("source_dimension") not in {"vervar", "turvar"}:
            errors.append(f"{prefix}: source_dimension must be vervar or turvar")
        if row.get("mapping_type") not in MAPPING_TYPES:
            errors.append(f"{prefix}: unsupported mapping_type {row.get('mapping_type')!r}")
        canonical = geographies.get(row.get("canonical_geography_id", ""))
        if canonical is None:
            errors.append(f"{prefix}: unknown canonical geography {row.get('canonical_geography_id')}")
        try:
            int(row.get("bps_dimension_id", ""))
            start = int(row.get("applicable_start_year", ""))
            end = int(row.get("applicable_end_year", ""))
        except ValueError:
            errors.append(f"{prefix}: dimension id and years must be integer-compatible")
            continue
        if start > end:
            errors.append(f"{prefix}: mapping start year is after end year")
        if row.get("mapping_type") == "direct_current_code" and canonical is not None:
            if canonical.get("bps_code") != row.get("bps_dimension_id"):
                errors.append(f"{prefix}: direct current mapping does not match canonical BPS code")

    expected_vervar = {"1300", "1378"} | {
        "1301", "1302", "1303", "1304", "1305", "1306", "1307", "1308", "1309",
        "1310", "1311", "1312", "1371", "1372", "1373", "1374", "1375", "1376", "1377",
    }
    if {key[1] for key in map_keys if key[0] == "vervar"} != expected_vervar:
        errors.append("expansion vervar geography map must contain 19 local codes plus 1300/1378 aliases")
    expected_turvar = {str(value) for value in range(464, 484)}
    if {key[1] for key in map_keys if key[0] == "turvar"} != expected_turvar:
        errors.append("PDRB turvar geography map must contain exact aliases 464-483")

    expected_source_rows = 140 + 160 + 120 + 120 + 160 + 6 + 20
    expected_canonical_rows = 140 + 8 + 120 + 120 + 160 + 6 + 20
    expected_held_rows = 152
    return errors, {
        "series": len(series),
        "qualifications": len(qualifications),
        "geography_mappings": len(geography_map),
        "expected_source_rows": expected_source_rows,
        "expected_canonical_rows": expected_canonical_rows,
        "expected_held_rows": expected_held_rows,
    }


def main() -> int:
    errors, counts = validate()
    if errors:
        print("BPS expansion contract validation FAILED", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(
        "BPS expansion contract validation passed: "
        f"{counts['series']} logical series, {counts['qualifications']} qualifications, "
        f"{counts['expected_source_rows']} expected source rows, "
        f"{counts['expected_canonical_rows']} expected canonical rows."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
