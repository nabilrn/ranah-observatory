#!/usr/bin/env python3
"""Validate Ranah Observatory's dependency-free data-foundation registries."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CLAIM_TYPES = {
    "observed",
    "derived",
    "reconstructed",
    "model_estimate",
    "causal_estimate",
    "qualitative",
    "scenario",
}

DOMAINS = {
    "demography_migration",
    "health",
    "education_knowledge",
    "labor_livelihoods",
    "income_productivity_poverty_inequality",
    "production_trade",
    "infrastructure_connectivity",
    "public_finance_institutions",
    "environment_climate",
    "disaster_resilience",
    "geography_market_access",
    "historical_social_context",
}

GEOGRAPHY_LEVELS = {
    "country",
    "province",
    "regency",
    "city",
    "district",
    "village",
    "historical_region",
    "watershed",
    "station",
    "grid",
    "other",
}

GEOGRAPHY_STATUSES = {"current", "historical", "provisional", "retired"}
INDICATOR_STATUSES = {"backlog", "qualified", "ingested", "deprecated"}
RELATIONSHIP_TYPES = {
    "rename",
    "code_change",
    "split",
    "merge",
    "boundary_adjustment",
    "containment",
    "equivalent",
}
CONFIDENCE_LEVELS = {"high", "medium", "low"}


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for raw in reader:
            rows.append({key: (value or "").strip() for key, value in raw.items()})
        return list(reader.fieldnames or []), rows


def require_columns(
    errors: list[str], path: Path, headers: list[str], required: set[str]
) -> None:
    missing = sorted(required - set(headers))
    if missing:
        errors.append(f"{path}: missing columns: {', '.join(missing)}")


def duplicates(values: list[str]) -> list[str]:
    seen: set[str] = set()
    repeated: set[str] = set()
    for value in values:
        if value in seen:
            repeated.add(value)
        seen.add(value)
    return sorted(repeated)


def validate() -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []

    geography_path = ROOT / "data" / "registries" / "geographies.csv"
    crosswalk_path = ROOT / "data" / "registries" / "geography_crosswalk.csv"
    indicator_path = ROOT / "data" / "registries" / "indicators.csv"
    source_path = ROOT / "catalog" / "data-catalog.csv"
    schema_path = ROOT / "schemas" / "data-foundation.schema.json"

    source_headers, sources = read_csv(source_path)
    require_columns(errors, source_path, source_headers, {"source_id", "status"})
    source_ids = [row["source_id"] for row in sources if row.get("source_id")]
    for value in duplicates(source_ids):
        errors.append(f"{source_path}: duplicate source_id {value}")
    source_id_set = set(source_ids)

    geography_headers, geographies = read_csv(geography_path)
    require_columns(
        errors,
        geography_path,
        geography_headers,
        {
            "geography_id",
            "geography_level",
            "canonical_name",
            "bps_code",
            "parent_geography_id",
            "valid_from",
            "valid_to",
            "status",
            "source_id",
        },
    )

    geography_ids = [row["geography_id"] for row in geographies if row.get("geography_id")]
    for value in duplicates(geography_ids):
        errors.append(f"{geography_path}: duplicate geography_id {value}")
    geography_id_set = set(geography_ids)

    bps_codes = [row["bps_code"] for row in geographies if row.get("bps_code")]
    for value in duplicates(bps_codes):
        errors.append(f"{geography_path}: duplicate bps_code {value}")

    for line_no, row in enumerate(geographies, start=2):
        prefix = f"{geography_path}:{line_no}"
        for field in ("geography_id", "geography_level", "canonical_name", "status", "source_id"):
            if not row.get(field):
                errors.append(f"{prefix}: {field} is required")
        if row.get("geography_level") not in GEOGRAPHY_LEVELS:
            errors.append(f"{prefix}: unknown geography_level {row.get('geography_level')!r}")
        if row.get("status") not in GEOGRAPHY_STATUSES:
            errors.append(f"{prefix}: unknown geography status {row.get('status')!r}")
        parent = row.get("parent_geography_id")
        if parent and parent not in geography_id_set:
            errors.append(f"{prefix}: unresolved parent_geography_id {parent}")
        source_id = row.get("source_id")
        if source_id and source_id not in source_id_set:
            errors.append(f"{prefix}: unresolved source_id {source_id}")
        valid_from = row.get("valid_from")
        valid_to = row.get("valid_to")
        if valid_from and valid_to and valid_from > valid_to:
            errors.append(f"{prefix}: valid_from is after valid_to")

    indicator_headers, indicators = read_csv(indicator_path)
    require_columns(
        errors,
        indicator_path,
        indicator_headers,
        {
            "indicator_id",
            "name",
            "domain",
            "definition",
            "unit",
            "frequency",
            "preferred_geography",
            "source_priority",
            "allowed_claim_types",
            "status",
        },
    )

    indicator_ids = [row["indicator_id"] for row in indicators if row.get("indicator_id")]
    for value in duplicates(indicator_ids):
        errors.append(f"{indicator_path}: duplicate indicator_id {value}")

    represented_domains: set[str] = set()
    for line_no, row in enumerate(indicators, start=2):
        prefix = f"{indicator_path}:{line_no}"
        for field in (
            "indicator_id",
            "name",
            "domain",
            "definition",
            "unit",
            "frequency",
            "preferred_geography",
            "source_priority",
            "allowed_claim_types",
            "status",
        ):
            if not row.get(field):
                errors.append(f"{prefix}: {field} is required")
        domain = row.get("domain", "")
        represented_domains.add(domain)
        if domain not in DOMAINS:
            errors.append(f"{prefix}: unknown domain {domain!r}")
        status = row.get("status", "")
        if status not in INDICATOR_STATUSES:
            errors.append(f"{prefix}: unknown indicator status {status!r}")
        claim_types = {value for value in row.get("allowed_claim_types", "").split("|") if value}
        unknown_claim_types = sorted(claim_types - CLAIM_TYPES)
        if unknown_claim_types:
            errors.append(
                f"{prefix}: unknown allowed claim types: {', '.join(unknown_claim_types)}"
            )

    # The indicator registry is the research ontology/backlog and may contain
    # more than the initial 40-60 indicators. The Research Charter's 40-60
    # success criterion applies to indicators with canonical observations and
    # resolved provenance, which is enforced separately by the Milestone 4
    # indicator audit. Data-foundation validation only requires a sufficiently
    # broad ontology and validates every registered row structurally.
    if len(indicators) < 40:
        errors.append(
            f"{indicator_path}: expected at least 40 registered indicator definitions, found {len(indicators)}"
        )
    missing_domains = sorted(DOMAINS - represented_domains)
    if missing_domains:
        errors.append(
            f"{indicator_path}: missing research domains: {', '.join(missing_domains)}"
        )

    crosswalk_headers, crosswalks = read_csv(crosswalk_path)
    require_columns(
        errors,
        crosswalk_path,
        crosswalk_headers,
        {
            "crosswalk_id",
            "from_geography_id",
            "to_geography_id",
            "relationship_type",
            "effective_date",
            "weight",
            "weight_basis",
            "evidence_source_id",
            "confidence",
        },
    )

    crosswalk_ids = [row["crosswalk_id"] for row in crosswalks if row.get("crosswalk_id")]
    for value in duplicates(crosswalk_ids):
        errors.append(f"{crosswalk_path}: duplicate crosswalk_id {value}")

    for line_no, row in enumerate(crosswalks, start=2):
        prefix = f"{crosswalk_path}:{line_no}"
        for field in (
            "crosswalk_id",
            "from_geography_id",
            "to_geography_id",
            "relationship_type",
            "evidence_source_id",
            "confidence",
        ):
            if not row.get(field):
                errors.append(f"{prefix}: {field} is required")
        for field in ("from_geography_id", "to_geography_id"):
            if row.get(field) and row[field] not in geography_id_set:
                errors.append(f"{prefix}: unresolved {field} {row[field]}")
        if row.get("relationship_type") not in RELATIONSHIP_TYPES:
            errors.append(f"{prefix}: unknown relationship_type {row.get('relationship_type')!r}")
        if row.get("confidence") not in CONFIDENCE_LEVELS:
            errors.append(f"{prefix}: unknown confidence {row.get('confidence')!r}")
        if row.get("evidence_source_id") and row["evidence_source_id"] not in source_id_set:
            errors.append(f"{prefix}: unresolved evidence_source_id {row['evidence_source_id']}")
        if row.get("weight"):
            try:
                weight = float(row["weight"])
            except ValueError:
                errors.append(f"{prefix}: weight must be numeric")
            else:
                if not 0 <= weight <= 1:
                    errors.append(f"{prefix}: weight must be between 0 and 1")
            if not row.get("weight_basis"):
                errors.append(f"{prefix}: weight_basis required when weight is present")

    try:
        with schema_path.open("r", encoding="utf-8") as handle:
            schema = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{schema_path}: invalid JSON schema: {exc}")
        schema = {}

    expected_defs = {
        "claimType",
        "geographyLevel",
        "geography",
        "geographyCrosswalk",
        "indicator",
        "provenance",
        "observation",
    }
    missing_defs = sorted(expected_defs - set(schema.get("$defs", {})))
    if missing_defs:
        errors.append(f"{schema_path}: missing $defs: {', '.join(missing_defs)}")

    counts = {
        "sources": len(sources),
        "geographies": len(geographies),
        "crosswalks": len(crosswalks),
        "indicators": len(indicators),
        "domains": len(represented_domains & DOMAINS),
    }
    return errors, counts


def main() -> int:
    errors, counts = validate()
    if errors:
        print("Data foundation validation FAILED", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(
        "Data foundation validation passed: "
        f"{counts['sources']} sources, "
        f"{counts['geographies']} geographies, "
        f"{counts['crosswalks']} crosswalks, "
        f"{counts['indicators']} registered indicator definitions across {counts['domains']} domains."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
