from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
EVENTS = ROOT / "data" / "registries" / "historical_geography_events.csv"
SOURCES = ROOT / "data" / "registries" / "historical_source_inventory.csv"
CATALOG = ROOT / "catalog" / "data-catalog.csv"
SCHEMA = ROOT / "schemas" / "historical-extraction.schema.json"

DATE_PATTERNS = {
    "day": re.compile(r"^\d{4}-\d{2}-\d{2}$"),
    "month": re.compile(r"^\d{4}-\d{2}$"),
    "year": re.compile(r"^\d{4}$"),
}
ALLOWED_EVENT_TYPES = {
    "administrative_status",
    "legal_division",
    "province_formation",
    "province_reorganization",
    "legal_confirmation",
    "statistical_boundary_warning",
}
ALLOWED_EVIDENCE_STATUS = {"qualified", "provisional", "gap"}
ALLOWED_SOURCE_STATUS = {"qualified", "candidate", "gap"}
ALLOWED_PRIORITIES = {"P0", "P1", "P2"}
ALLOWED_RISKS = {"low", "medium", "high", "unknown"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def official_url(url: str) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and (
        host.endswith(".bps.go.id") or host == "bps.go.id" or host == "www.bps.go.id"
        or host == "peraturan.bpk.go.id"
    )


def validate() -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    events = read_csv(EVENTS)
    sources = read_csv(SOURCES)
    catalog = read_csv(CATALOG)
    catalog_ids = {row["source_id"].strip() for row in catalog}

    event_ids = [row["event_id"].strip() for row in events]
    if len(event_ids) != len(set(event_ids)):
        errors.append("historical_geography_events.csv contains duplicate event_id values")

    for row_number, row in enumerate(events, start=2):
        precision = row["event_date_precision"].strip()
        event_date = row["event_date"].strip()
        if precision not in DATE_PATTERNS:
            errors.append(f"event row {row_number}: invalid date precision {precision!r}")
        elif not DATE_PATTERNS[precision].match(event_date):
            errors.append(
                f"event row {row_number}: date {event_date!r} does not match precision {precision!r}"
            )
        if row["event_type"].strip() not in ALLOWED_EVENT_TYPES:
            errors.append(f"event row {row_number}: invalid event_type")
        if row["evidence_status"].strip() not in ALLOWED_EVIDENCE_STATUS:
            errors.append(f"event row {row_number}: invalid evidence_status")
        source_id = row["source_id"].strip()
        if source_id not in catalog_ids:
            errors.append(f"event row {row_number}: unknown source_id={source_id!r}")
        if not official_url(row["official_url"].strip()):
            errors.append(f"event row {row_number}: official_url is not an allowed official host")
        if not row["implication"].strip():
            errors.append(f"event row {row_number}: implication is required")

    source_record_ids = [row["source_record_id"].strip() for row in sources]
    if len(source_record_ids) != len(set(source_record_ids)):
        errors.append("historical_source_inventory.csv contains duplicate source_record_id values")

    for row_number, row in enumerate(sources, start=2):
        source_id = row["source_id"].strip()
        status = row["status"].strip()
        if source_id not in catalog_ids:
            errors.append(f"source row {row_number}: unknown source_id={source_id!r}")
        if status not in ALLOWED_SOURCE_STATUS:
            errors.append(f"source row {row_number}: invalid status={status!r}")
        if row["priority"].strip() not in ALLOWED_PRIORITIES:
            errors.append(f"source row {row_number}: invalid priority")
        if row["comparability_risk"].strip() not in ALLOWED_RISKS:
            errors.append(f"source row {row_number}: invalid comparability_risk")
        url = row["official_url"].strip()
        if status == "qualified" and not official_url(url):
            errors.append(
                f"source row {row_number}: qualified source must have an allowed official URL"
            )
        if status == "gap" and url:
            errors.append(f"source row {row_number}: gap records should not pretend to have a source URL")
        try:
            start = int(row["reference_start"].strip())
            end = int(row["reference_end"].strip())
            if start > end:
                errors.append(f"source row {row_number}: reference_start exceeds reference_end")
        except ValueError:
            errors.append(f"source row {row_number}: reference years must be integers")

    with SCHEMA.open("r", encoding="utf-8") as handle:
        schema = json.load(handle)
    required = set(schema.get("required", []))
    for field in {
        "source_record_id",
        "artifact_sha256",
        "source_geography_label",
        "reference_period",
        "reconstruction_state",
        "mapping_status",
    }:
        if field not in required:
            errors.append(f"historical extraction schema must require {field}")

    state_values = set(
        schema["properties"]["reconstruction_state"].get("enum", [])
    )
    expected_states = {
        "observed_source_era",
        "derived_source_era",
        "reconstructed_geography",
        "reconstructed_definition",
        "not_comparable",
    }
    if state_values != expected_states:
        errors.append("historical extraction schema reconstruction states do not match contract")

    by_id = {row["event_id"].strip(): row for row in events}
    required_events = {
        "sumatra_autonomy_1947",
        "sumatra_three_provinces_1948",
        "sumatera_tengah_1950",
        "sumbar_jambi_riau_1957",
        "sumbar_confirmation_1958",
        "census_boundary_warning_1961",
    }
    missing_events = sorted(required_events - by_id.keys())
    if missing_events:
        errors.append("missing required historical anchors: " + ", ".join(missing_events))
    if "sumatera_tengah_1950" in by_id:
        row = by_id["sumatera_tengah_1950"]
        if row["event_date_precision"].strip() != "year" or row["event_date"].strip() != "1950":
            errors.append("Perpu 4/1950 must remain year-precision until a primary exact date is qualified")

    source_by_id = {row["source_record_id"].strip(): row for row in sources}
    gap = source_by_id.get("archive_gap_1945_1946")
    if not gap or gap["status"].strip() != "gap":
        errors.append("1945-1946 must remain an explicit source gap")

    warning = by_id.get("census_boundary_warning_1961")
    if warning and "Tingkat I" not in warning["implication"]:
        errors.append("1961 census boundary warning must preserve the Tingkat I constraint")

    counts = {
        "events": len(events),
        "sources": len(sources),
        "qualified_sources": sum(row["status"].strip() == "qualified" for row in sources),
        "gaps": sum(row["status"].strip() == "gap" for row in sources),
    }
    return errors, counts


def main() -> int:
    errors, counts = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(
        "Historical reconstruction foundation valid: "
        f"{counts['events']} events; {counts['qualified_sources']} qualified sources; "
        f"{counts['gaps']} explicit gaps"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
