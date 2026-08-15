#!/usr/bin/env python3
from __future__ import annotations

import csv
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data" / "registries" / "bps_panel_series.csv"
QUALIFICATIONS = ROOT / "data" / "registries" / "bps_panel_qualification.csv"
GEOGRAPHY_MAP = ROOT / "data" / "registries" / "bps_panel_geography_map.csv"
CANDIDATES = ROOT / "data" / "registries" / "bps_live_candidates.csv"
INDICATORS = ROOT / "data" / "registries" / "indicators.csv"
GEOGRAPHIES = ROOT / "data" / "registries" / "geographies.csv"

QUALIFICATION_STATUSES = {"source_metadata_qualified", "methodology_specific_candidate"}
PROMOTION_STATUSES = {"pending_indicator_universe_review", "canonical_ready"}
QUALIFICATION_DECISIONS = {"canonical_ready", "hold_source_native"}
REFERENCE_PERIOD_RULES = {
    "calendar_month_august",
    "calendar_month_march",
    "calendar_year",
    "calendar_year_source_label",
}
CANONICAL_UNITS = {"percent", "years"}
SUBPERIOD_POLICIES = {"preserve_all"}
MAPPING_TYPES = {"direct_current_code", "source_aggregate_alias"}


def _read(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def _official_bps_url(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and (host == "bps.go.id" or host.endswith(".bps.go.id"))


def validate() -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    rows = _read(PANEL)
    qualifications = _read(QUALIFICATIONS)
    geography_map = _read(GEOGRAPHY_MAP)
    candidates = _read(CANDIDATES)
    indicator_rows = _read(INDICATORS)
    geography_rows = _read(GEOGRAPHIES)
    indicators = {row["indicator_id"] for row in indicator_rows}
    canonical_geographies = {row["geography_id"]: row for row in geography_rows}
    candidate_pairs = {(row["indicator_id"], row["bps_var_id"]): row for row in candidates}

    if len(rows) != 8:
        errors.append(f"{PANEL}: first panel must contain exactly 8 reviewed source series")

    qualification_by_id: dict[str, dict[str, str]] = {}
    qualification_by_series: dict[str, dict[str, str]] = {}
    for line_no, row in enumerate(qualifications, start=2):
        prefix = f"{QUALIFICATIONS}:{line_no}"
        required = (
            "qualification_id", "panel_series_id", "decision", "canonical_unit",
            "reference_period_rule", "source_universe", "method_version",
            "quality_flags_rule", "evidence_type", "notes",
        )
        for field in required:
            if not row.get(field):
                errors.append(f"{prefix}: {field} is required")
        qid = row.get("qualification_id", "")
        series_id = row.get("panel_series_id", "")
        if qid in qualification_by_id:
            errors.append(f"{prefix}: duplicate qualification_id {qid}")
        if series_id in qualification_by_series:
            errors.append(f"{prefix}: duplicate panel_series_id qualification {series_id}")
        qualification_by_id[qid] = row
        qualification_by_series[series_id] = row
        if row.get("decision") not in QUALIFICATION_DECISIONS:
            errors.append(f"{prefix}: unsupported decision {row.get('decision')!r}")
        if row.get("canonical_unit") not in CANONICAL_UNITS:
            errors.append(f"{prefix}: unsupported canonical_unit {row.get('canonical_unit')!r}")
        if row.get("reference_period_rule") not in REFERENCE_PERIOD_RULES:
            errors.append(f"{prefix}: unsupported reference_period_rule {row.get('reference_period_rule')!r}")
        evidence_type = row.get("evidence_type", "")
        urls = [item.strip() for item in row.get("evidence_url", "").split("|") if item.strip()]
        if evidence_type == "bps_webapi_var_metadata":
            if urls:
                errors.append(f"{prefix}: WebAPI-metadata-only qualification should not invent an external URL")
        else:
            if not urls:
                errors.append(f"{prefix}: evidence_url is required for external qualification evidence")
            for url in urls:
                if not _official_bps_url(url):
                    errors.append(f"{prefix}: qualification evidence must use an official BPS HTTPS host: {url}")

    if len(qualification_by_series) != len(rows):
        errors.append("every first-panel source series must have exactly one qualification record")

    ids: set[str] = set()
    pairs: set[tuple[str, str]] = set()
    panel_min_year = 9999
    panel_max_year = 0
    ready_count = 0
    held_count = 0
    for line_no, row in enumerate(rows, start=2):
        prefix = f"{PANEL}:{line_no}"
        required = (
            "panel_series_id", "indicator_id", "bps_var_id", "subject_id", "source_title",
            "target_start_year", "target_end_year", "selected_turvar_id", "selected_turvar_label",
            "subperiod_policy", "qualification_id", "qualification_status",
            "canonical_promotion_status", "comparability_notes",
        )
        for field in required:
            if not row.get(field):
                errors.append(f"{prefix}: {field} is required")

        series_id = row.get("panel_series_id", "")
        if series_id in ids:
            errors.append(f"{prefix}: duplicate panel_series_id {series_id}")
        ids.add(series_id)

        pair = (row.get("indicator_id", ""), row.get("bps_var_id", ""))
        if pair in pairs:
            errors.append(f"{prefix}: duplicate indicator/BPS variable mapping {pair}")
        pairs.add(pair)

        if row.get("indicator_id") not in indicators:
            errors.append(f"{prefix}: unresolved indicator_id {row.get('indicator_id')}")
        candidate = candidate_pairs.get(pair)
        if candidate is None:
            errors.append(f"{prefix}: mapping is not present in bps_live_candidates.csv")
        elif candidate.get("bps_title") != row.get("source_title"):
            errors.append(f"{prefix}: source_title differs from qualified live-candidate title")

        try:
            start = int(row.get("target_start_year", ""))
            end = int(row.get("target_end_year", ""))
        except ValueError:
            errors.append(f"{prefix}: target years must be integers")
        else:
            panel_min_year = min(panel_min_year, start)
            panel_max_year = max(panel_max_year, end)
            if start > end:
                errors.append(f"{prefix}: target_start_year is after target_end_year")
            if start < 1950 or end > 2100:
                errors.append(f"{prefix}: implausible target year range")

        try:
            int(row.get("bps_var_id", ""))
            int(row.get("subject_id", ""))
            int(row.get("selected_turvar_id", ""))
        except ValueError:
            errors.append(f"{prefix}: BPS ids must be integer-compatible")

        if row.get("subperiod_policy") not in SUBPERIOD_POLICIES:
            errors.append(f"{prefix}: unsupported subperiod_policy {row.get('subperiod_policy')!r}")
        if row.get("qualification_status") not in QUALIFICATION_STATUSES:
            errors.append(f"{prefix}: unsupported qualification_status {row.get('qualification_status')!r}")
        promotion = row.get("canonical_promotion_status")
        if promotion not in PROMOTION_STATUSES:
            errors.append(f"{prefix}: unsupported canonical_promotion_status {promotion!r}")

        qid = row.get("qualification_id", "")
        qualification = qualification_by_id.get(qid)
        if qualification is None:
            errors.append(f"{prefix}: unresolved qualification_id {qid}")
        else:
            if qualification.get("panel_series_id") != series_id:
                errors.append(f"{prefix}: qualification_id {qid} belongs to another panel series")
            expected_promotion = (
                "canonical_ready"
                if qualification.get("decision") == "canonical_ready"
                else "pending_indicator_universe_review"
            )
            if promotion != expected_promotion:
                errors.append(
                    f"{prefix}: promotion status {promotion!r} disagrees with qualification decision "
                    f"{qualification.get('decision')!r}"
                )

        if promotion == "canonical_ready":
            ready_count += 1
        else:
            held_count += 1

    if ready_count != 7 or held_count != 1:
        errors.append(f"first qualification pass must yield 7 canonical-ready and 1 held series, got {ready_count}/{held_count}")

    by_var = {row["bps_var_id"]: row for row in rows}
    internet = by_var.get("320")
    if internet is None:
        errors.append("internet source var 320 is missing")
    else:
        if internet["selected_turvar_id"] != "595" or "Pernah Mengakses Internet" not in internet["selected_turvar_label"]:
            errors.append("var 320 must explicitly select turvar 595 Pernah Mengakses Internet")
        if internet["canonical_promotion_status"] != "pending_indicator_universe_review":
            errors.append("person-level internet source must remain held until household/person ontology is resolved")

    life = by_var.get("752")
    if life and int(life["target_start_year"]) < 2020:
        errors.append("LF-SP2020 life-expectancy candidate must not be projected before 2020")

    map_ids: set[str] = set()
    canonical_ids_seen: set[str] = set()
    for line_no, row in enumerate(geography_map, start=2):
        prefix = f"{GEOGRAPHY_MAP}:{line_no}"
        for field in (
            "bps_vervar_id", "canonical_geography_id", "mapping_type",
            "applicable_start_year", "applicable_end_year", "notes",
        ):
            if not row.get(field):
                errors.append(f"{prefix}: {field} is required")
        source_id = row.get("bps_vervar_id", "")
        if source_id in map_ids:
            errors.append(f"{prefix}: duplicate bps_vervar_id {source_id}")
        map_ids.add(source_id)
        try:
            int(source_id)
            start = int(row.get("applicable_start_year", ""))
            end = int(row.get("applicable_end_year", ""))
        except ValueError:
            errors.append(f"{prefix}: source geography id and applicability years must be integer-compatible")
            continue
        if start > panel_min_year or end < panel_max_year:
            errors.append(
                f"{prefix}: geography mapping does not cover full first-panel window {panel_min_year}-{panel_max_year}"
            )
        canonical_id = row.get("canonical_geography_id", "")
        canonical = canonical_geographies.get(canonical_id)
        if canonical is None:
            errors.append(f"{prefix}: unresolved canonical geography {canonical_id}")
        if row.get("mapping_type") not in MAPPING_TYPES:
            errors.append(f"{prefix}: unsupported mapping_type {row.get('mapping_type')!r}")
        elif row["mapping_type"] == "direct_current_code" and canonical is not None:
            if canonical.get("status") != "current":
                errors.append(f"{prefix}: direct_current_code must map to a current geography")
            if canonical.get("bps_code") != source_id:
                errors.append(
                    f"{prefix}: direct_current_code {source_id} does not match canonical bps_code {canonical.get('bps_code')}"
                )
        canonical_ids_seen.add(canonical_id)

    expected_local_codes = {
        "1301", "1302", "1303", "1304", "1305", "1306", "1307", "1308", "1309",
        "1310", "1311", "1312", "1371", "1372", "1373", "1374", "1375", "1376", "1377",
    }
    if not expected_local_codes.issubset(map_ids):
        errors.append("BPS panel geography map is missing one or more current kabupaten/kota codes")
    for alias in ("1300", "1378"):
        alias_row = next((item for item in geography_map if item["bps_vervar_id"] == alias), None)
        if alias_row is None:
            errors.append(f"BPS province source alias {alias} is missing")
        elif alias_row["canonical_geography_id"] != "idn.13" or alias_row["mapping_type"] != "source_aggregate_alias":
            errors.append(f"BPS province source alias {alias} must map explicitly to idn.13 as source_aggregate_alias")

    current_bps_codes = {row["bps_code"] for row in geography_rows if row["status"] == "current" and row["bps_code"]}
    if "1378" in current_bps_codes or "1300" in current_bps_codes:
        errors.append("BPS API aggregate aliases 1300/1378 must not leak into the canonical current geography code registry")
    if "idn.13" not in canonical_ids_seen:
        errors.append("first-panel geography map must include the Sumatera Barat province aggregate")

    return errors, {
        "series": len(rows),
        "indicators": len({row["indicator_id"] for row in rows}),
        "canonical_ready": ready_count,
        "held_source_native": held_count,
        "qualifications": len(qualifications),
        "geography_mappings": len(geography_map),
    }


def main() -> int:
    errors, counts = validate()
    if errors:
        print("BPS normalized-panel registry validation FAILED", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(
        "BPS normalized-panel registry validation passed: "
        f"{counts['series']} source series, {counts['canonical_ready']} canonical-ready, "
        f"{counts['held_source_native']} held, {counts['geography_mappings']} geography mappings."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
