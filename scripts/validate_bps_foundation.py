from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDICATORS = ROOT / "data" / "registries" / "indicators.csv"
COVERAGE = ROOT / "data" / "registries" / "bps_indicator_coverage.csv"
PUBLICATIONS = ROOT / "data" / "registries" / "bps_publications_seed.csv"
CATALOG = ROOT / "catalog" / "data-catalog.csv"

ALLOWED_BPS_ROLES = {"primary", "crosscheck", "derived_input", "not_primary", "archive"}
ALLOWED_QUALIFICATION = {
    "candidate",
    "candidate_secondary",
    "derived_candidate",
    "defer_non_bps",
    "historical_inventory",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def validate() -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    indicators = read_csv(INDICATORS)
    coverage = read_csv(COVERAGE)
    publications = read_csv(PUBLICATIONS)
    catalog = read_csv(CATALOG)

    indicator_ids = {row["indicator_id"].strip() for row in indicators}
    coverage_ids = [row["indicator_id"].strip() for row in coverage]
    coverage_set = set(coverage_ids)
    catalog_ids = {row["source_id"].strip() for row in catalog}

    if len(coverage_ids) != len(coverage_set):
        errors.append("bps_indicator_coverage.csv contains duplicate indicator_id values")

    missing = sorted(indicator_ids - coverage_set)
    extra = sorted(coverage_set - indicator_ids)
    if missing:
        errors.append(f"BPS coverage is missing canonical indicators: {', '.join(missing)}")
    if extra:
        errors.append(f"BPS coverage contains unknown indicators: {', '.join(extra)}")

    for row_number, row in enumerate(coverage, start=2):
        role = row["bps_role"].strip()
        qualification = row["qualification_status"].strip()
        if role not in ALLOWED_BPS_ROLES:
            errors.append(f"coverage row {row_number}: invalid bps_role={role!r}")
        if qualification not in ALLOWED_QUALIFICATION:
            errors.append(
                f"coverage row {row_number}: invalid qualification_status={qualification!r}"
            )
        if not row["acquisition_lane"].strip():
            errors.append(f"coverage row {row_number}: acquisition_lane is required")
        if not row["query_terms"].strip():
            errors.append(f"coverage row {row_number}: query_terms is required")

    publication_ids = [row["source_id"].strip() for row in publications]
    if len(publication_ids) != len(set(publication_ids)):
        errors.append("bps_publications_seed.csv contains duplicate source_id values")

    for row_number, row in enumerate(publications, start=2):
        source_id = row["source_id"].strip()
        if source_id not in catalog_ids:
            errors.append(
                f"publication row {row_number}: source_id={source_id!r} is missing from data catalog"
            )
        if row["status"].strip() != "qualified":
            errors.append(f"publication row {row_number}: seed publication must be qualified")
        if not row["official_url"].strip().startswith("https://"):
            errors.append(f"publication row {row_number}: official_url must be HTTPS")

    if "bps_webapi" not in catalog_ids:
        errors.append("data catalog must contain bps_webapi")

    counts = {
        "canonical_indicators": len(indicator_ids),
        "coverage_rows": len(coverage_ids),
        "seed_publications": len(publications),
    }
    return errors, counts


def main() -> int:
    errors, counts = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(
        "BPS ingestion foundation valid: "
        f"{counts['coverage_rows']}/{counts['canonical_indicators']} indicators covered; "
        f"{counts['seed_publications']} qualified seed publications"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
