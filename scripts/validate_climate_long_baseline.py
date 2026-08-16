from __future__ import annotations

import csv
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data" / "registries" / "climate_sources.csv"
INDICATORS = ROOT / "data" / "registries" / "indicators.csv"
CATALOG = ROOT / "catalog" / "data-catalog.csv"
DOC = ROOT / "docs" / "CLIMATE_LONG_BASELINE.md"

EXPECTED_SOURCE_IDS = {
    "chirps_v3_final_monthly",
    "chirps_v3_daily_rnl",
    "era5_land_hourly",
}
ALLOWED_HOSTS = {
    "www.chc.ucsb.edu",
    "data.chc.ucsb.edu",
    "cds.climate.copernicus.eu",
}
EXPECTED_CATALOG_IDS = {"chirps_v3", "era5_land"}
EXPECTED_INDICATOR_CONTRACTS = {
    "annual_rainfall": {
        "required_sources": {"BMKG", "CHIRPS", "ERA5-Land"},
        "required_claims": {"observed", "derived", "model_estimate"},
    },
    "extreme_rainfall_days": {
        "required_sources": {"BMKG", "CHIRPS"},
        "required_claims": {"derived", "model_estimate"},
    },
    "mean_temperature": {
        "required_sources": {"BMKG", "ERA5-Land"},
        "required_claims": {"observed", "derived", "model_estimate"},
    },
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [
            {key: (value or "").strip() for key, value in row.items()}
            for row in csv.DictReader(handle)
        ]


def split_pipe(value: str) -> set[str]:
    return {part.strip() for part in value.split("|") if part.strip()}


def validate() -> list[str]:
    errors: list[str] = []
    sources = read_csv(SOURCES)
    indicators = {row["indicator_id"]: row for row in read_csv(INDICATORS)}
    catalog = {row["source_id"]: row for row in read_csv(CATALOG)}

    ids = [row["source_record_id"] for row in sources]
    if len(ids) != len(set(ids)):
        errors.append("climate source_record_id values must be unique")
    missing = EXPECTED_SOURCE_IDS - set(ids)
    if missing:
        errors.append(f"missing climate sources: {sorted(missing)}")

    by_id = {row["source_record_id"]: row for row in sources}
    for row in sources:
        parsed = urlparse(row["official_url"])
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
            errors.append(
                f"{row['source_record_id']}: official_url is not an approved producer/distributor host"
            )

    chirps = by_id.get("chirps_v3_final_monthly")
    if chirps:
        if chirps["auth_required"] != "false":
            errors.append("CHIRPS final monthly must remain credential-free")
        if chirps["evidence_class"] != "satellite_station_gridded_estimate":
            errors.append("CHIRPS final monthly evidence class changed unexpectedly")
        if chirps["qualification_status"] != "qualified":
            errors.append("CHIRPS final monthly must remain qualified")
        if chirps["canonical_role"] != "rainfall_model_estimate_candidate":
            errors.append("CHIRPS final monthly canonical role changed unexpectedly")

    daily = by_id.get("chirps_v3_daily_rnl")
    if daily:
        if daily["evidence_class"] != "derived_reanalysis_disaggregated_estimate":
            errors.append("CHIRPS daily rnl evidence class changed unexpectedly")
        if daily["canonical_role"] != "held_extreme_day_candidate":
            errors.append("CHIRPS daily rnl must remain held for extreme-day use")
        if daily["qualification_status"] == "qualified":
            errors.append("CHIRPS daily rnl must not be fully qualified by this phase")

    era5 = by_id.get("era5_land_hourly")
    if era5:
        if era5["auth_required"] != "true":
            errors.append("ERA5-Land access must retain its credential requirement")
        if era5["evidence_class"] != "reanalysis_model_estimate":
            errors.append("ERA5-Land evidence class changed unexpectedly")
        if era5["canonical_role"] != "long_baseline_extension_candidate":
            errors.append("ERA5-Land canonical role changed unexpectedly")

    for catalog_id in EXPECTED_CATALOG_IDS:
        if catalog_id not in catalog:
            errors.append(f"catalog missing {catalog_id}")

    for indicator_id, contract in EXPECTED_INDICATOR_CONTRACTS.items():
        row = indicators.get(indicator_id)
        if row is None:
            errors.append(f"missing climate indicator {indicator_id}")
            continue
        sources_set = split_pipe(row["source_priority"])
        claims_set = split_pipe(row["allowed_claim_types"])
        if not contract["required_sources"].issubset(sources_set):
            errors.append(
                f"{indicator_id}: missing required source families "
                f"{sorted(contract['required_sources'] - sources_set)}"
            )
        if not contract["required_claims"].issubset(claims_set):
            errors.append(
                f"{indicator_id}: missing required claim types "
                f"{sorted(contract['required_claims'] - claims_set)}"
            )

    doc = DOC.read_text(encoding="utf-8")
    required_phrases = (
        "Neither source is allowed to masquerade as a BMKG station observation.",
        "`model_estimate`",
        "`held_extreme_day_candidate`",
        "personal access token",
        "versioned polygon geometry",
        "must never silently treat a change of source in 1981",
    )
    for phrase in required_phrases:
        if phrase not in doc:
            errors.append(f"climate baseline methodology doc missing phrase {phrase!r}")

    return errors


def main() -> int:
    try:
        errors = validate()
    except (OSError, ValueError) as exc:
        print(f"Climate long-baseline validation FAILED: {exc}", file=sys.stderr)
        return 1

    if errors:
        print("Climate long-baseline validation FAILED", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(
        "Climate long-baseline validation passed: "
        "CHIRPS monthly qualified as model-estimate candidate; "
        "daily extremes held; ERA5-Land retained as authenticated reanalysis extension."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
