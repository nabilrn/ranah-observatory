from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
EVENTS = ROOT / "data" / "registries" / "historical_geography_events.csv"
SOURCES = ROOT / "data" / "registries" / "historical_source_inventory.csv"
ANOMALIES = ROOT / "data" / "registries" / "historical_source_anomalies.csv"
CANDIDATES = ROOT / "data" / "registries" / "historical_extraction_candidates.csv"
CATALOG = ROOT / "catalog" / "data-catalog.csv"
SCHEMA = ROOT / "schemas" / "historical-extraction.schema.json"
CANONICAL_EXTRACTIONS = ROOT / "data" / "extractions"

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
ALLOWED_ANOMALY_STATUS = {"unresolved", "resolved", "accepted_difference"}
ALLOWED_CANDIDATE_STATUS = {
    "pending_artifact_verification",
    "artifact_verified",
    "rejected",
}
ALLOWED_CANDIDATE_STATES = {
    "observed_retrospective_official",
    "observed_source_era",
    "not_comparable",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def official_url(url: str) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and (
        host.endswith(".bps.go.id")
        or host == "bps.go.id"
        or host == "www.bps.go.id"
        or host == "peraturan.bpk.go.id"
    )


def validate() -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    events = read_csv(EVENTS)
    sources = read_csv(SOURCES)
    anomalies = read_csv(ANOMALIES)
    candidates = read_csv(CANDIDATES)
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
    source_record_set = set(source_record_ids)
    if len(source_record_ids) != len(source_record_set):
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

    anomaly_ids = [row["anomaly_id"].strip() for row in anomalies]
    if len(anomaly_ids) != len(set(anomaly_ids)):
        errors.append("historical_source_anomalies.csv contains duplicate anomaly_id values")
    for row_number, row in enumerate(anomalies, start=2):
        if row["status"].strip() not in ALLOWED_ANOMALY_STATUS:
            errors.append(f"anomaly row {row_number}: invalid status")
        if not row["claim_a"].strip() or not row["claim_b"].strip():
            errors.append(f"anomaly row {row_number}: both conflicting claims are required")
        if not row["claim_a_source"].strip() or not row["claim_b_source"].strip():
            errors.append(f"anomaly row {row_number}: both source identifiers are required")
        if not row["analytical_rule"].strip():
            errors.append(f"anomaly row {row_number}: analytical_rule is required")

    candidate_ids = [row["candidate_id"].strip() for row in candidates]
    if len(candidate_ids) != len(set(candidate_ids)):
        errors.append("historical_extraction_candidates.csv contains duplicate candidate_id values")
    for row_number, row in enumerate(candidates, start=2):
        source_record_id = row["source_record_id"].strip()
        evidence_status = row["evidence_status"].strip()
        blocker = row["promotion_blocker"].strip()
        if source_record_id not in source_record_set:
            errors.append(
                f"candidate row {row_number}: unknown source_record_id={source_record_id!r}"
            )
        if evidence_status not in ALLOWED_CANDIDATE_STATUS:
            errors.append(f"candidate row {row_number}: invalid evidence_status")
        if row["reconstruction_state"].strip() not in ALLOWED_CANDIDATE_STATES:
            errors.append(f"candidate row {row_number}: invalid candidate reconstruction_state")
        if not official_url(row["evidence_locator"].strip()):
            errors.append(f"candidate row {row_number}: evidence_locator must be an official URL")
        try:
            value = float(row["raw_value"].strip())
            if value < 0:
                errors.append(f"candidate row {row_number}: raw_value must not be negative")
        except ValueError:
            errors.append(f"candidate row {row_number}: raw_value must be numeric")
        try:
            page = int(row["page"].strip())
            if page < 1:
                errors.append(f"candidate row {row_number}: page must be positive")
        except ValueError:
            errors.append(f"candidate row {row_number}: page must be an integer")
        if evidence_status == "pending_artifact_verification" and not blocker:
            errors.append(
                f"candidate row {row_number}: pending artifact verification requires a promotion_blocker"
            )
        if evidence_status == "artifact_verified" and blocker:
            errors.append(
                f"candidate row {row_number}: artifact_verified candidate must clear promotion_blocker"
            )

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

    state_values = set(schema["properties"]["reconstruction_state"].get("enum", []))
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

    series_anomaly = next(
        (row for row in anomalies if row["anomaly_id"].strip() == "sumbar_dalam_angka_series_start"),
        None,
    )
    if not series_anomaly or series_anomaly["status"].strip() != "unresolved":
        errors.append("Sumatera Barat Dalam Angka series-start metadata conflict must remain explicit")

    if CANONICAL_EXTRACTIONS.exists():
        for path in CANONICAL_EXTRACTIONS.rglob("*"):
            if path.is_file() and "candidate" in path.name.lower():
                errors.append(
                    f"candidate evidence must not be stored as canonical extraction: {path.relative_to(ROOT)}"
                )

    counts = {
        "events": len(events),
        "sources": len(sources),
        "qualified_sources": sum(row["status"].strip() == "qualified" for row in sources),
        "gaps": sum(row["status"].strip() == "gap" for row in sources),
        "anomalies": len(anomalies),
        "candidates": len(candidates),
        "blocked_candidates": sum(
            row["evidence_status"].strip() == "pending_artifact_verification"
            for row in candidates
        ),
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
        f"{counts['gaps']} explicit gaps; {counts['anomalies']} metadata anomalies; "
        f"{counts['blocked_candidates']} blocked extraction candidates"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
