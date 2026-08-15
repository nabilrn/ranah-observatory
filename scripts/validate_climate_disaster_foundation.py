from __future__ import annotations

import csv
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data" / "registries" / "disaster_sources.csv"
QUALIFICATIONS = ROOT / "data" / "registries" / "bnpb_indicator_qualification.csv"
BNPB_GEOGRAPHY_MAP = ROOT / "data" / "registries" / "bnpb_geography_map.csv"
GEOGRAPHIES = ROOT / "data" / "registries" / "geographies.csv"
INDICATORS = ROOT / "data" / "registries" / "indicators.csv"
CATALOG = ROOT / "catalog" / "data-catalog.csv"
DOC = ROOT / "docs" / "CLIMATE_DISASTER_FOUNDATION.md"

EXPECTED_SOURCE_IDS = {
    "bnpb_master_compilation",
    "bnpb_total_events_kab_2010_2024",
    "bnpb_events_by_type_kab_2024_primary",
    "bnpb_events_by_type_kab_2024_crosscheck",
    "bnpb_affected_by_type_kab_2024",
    "bnpb_damage_loss_rrrp_2017_2024",
    "bnpb_compilation_2025",
    "bmkg_satu_peta_rainfall_wms",
    "bmkg_dataonline_station_daily",
}
ALLOWED_OFFICIAL_HOSTS = {
    "data.bnpb.go.id",
    "gis.bmkg.go.id",
    "dataonline.bmkg.go.id",
}
CRITICAL_BNPB_MAPPINGS = {
    "1301": ("PESISIR SELATAN", "idn.13.1302"),
    "1309": ("KEPULAUAN MENTAWAI", "idn.13.1301"),
    "1310": ("DHARMASRAYA", "idn.13.1311"),
    "1311": ("SOLOK SELATAN", "idn.13.1310"),
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def validate() -> list[str]:
    errors: list[str] = []
    sources = read_csv(SOURCES)
    qualifications = read_csv(QUALIFICATIONS)
    geography_map = read_csv(BNPB_GEOGRAPHY_MAP)
    current_sumbar = {
        row["geography_id"]: row
        for row in read_csv(GEOGRAPHIES)
        if row["parent_geography_id"] == "idn.13"
        and row["status"] == "current"
        and row["geography_level"] in {"regency", "city"}
    }
    indicators = {row["indicator_id"]: row for row in read_csv(INDICATORS)}
    catalog = {row["source_id"]: row for row in read_csv(CATALOG)}

    source_ids = [row["source_record_id"] for row in sources]
    if len(source_ids) != len(set(source_ids)):
        errors.append("disaster source_record_id values must be unique")
    missing = EXPECTED_SOURCE_IDS - set(source_ids)
    if missing:
        errors.append(f"missing disaster source records: {sorted(missing)}")

    resource_ids = [row["resource_id"] for row in sources if row["resource_id"]]
    if len(resource_ids) != len(set(resource_ids)):
        errors.append("nonblank disaster resource IDs must be unique")

    for row in sources:
        url = row["official_url"]
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_OFFICIAL_HOSTS:
            errors.append(f"{row['source_record_id']}: official_url is not an approved official host")
        if row["organization"] == "BNPB" and row["access_mode"] == "CKAN DataStore":
            if row["datastore_active"] != "true" or not row["resource_id"]:
                errors.append(f"{row['source_record_id']}: DataStore source must have active resource ID")

    if len(current_sumbar) != 19:
        errors.append(f"canonical current Sumatera Barat geography count is {len(current_sumbar)}, expected 19")
    if len(geography_map) != 19:
        errors.append(f"BNPB geography crosswalk has {len(geography_map)} rows, expected 19")
    source_codes = [row["source_code_normalized"] for row in geography_map]
    source_names = [row["source_name_expected"].upper() for row in geography_map]
    canonical_ids = [row["canonical_geography_id"] for row in geography_map]
    if len(source_codes) != len(set(source_codes)):
        errors.append("BNPB geography source codes must be unique")
    if len(source_names) != len(set(source_names)):
        errors.append("BNPB geography expected source names must be unique")
    if len(canonical_ids) != len(set(canonical_ids)):
        errors.append("BNPB geography canonical IDs must be unique")
    if set(canonical_ids) != set(current_sumbar):
        errors.append("BNPB geography crosswalk must cover exactly the 19 current Sumatera Barat kabupaten/kota")

    by_source_code = {row["source_code_normalized"]: row for row in geography_map}
    for code, (expected_name, expected_geography_id) in CRITICAL_BNPB_MAPPINGS.items():
        row = by_source_code.get(code)
        if row is None:
            errors.append(f"BNPB geography crosswalk missing critical source code {code}")
            continue
        if row["source_name_expected"].upper() != expected_name or row["canonical_geography_id"] != expected_geography_id:
            errors.append(
                f"BNPB critical source mapping {code} changed unexpectedly: "
                f"name={row['source_name_expected']!r} canonical={row['canonical_geography_id']!r}"
            )

    for row in geography_map:
        canonical = current_sumbar.get(row["canonical_geography_id"])
        if row["source_system"] != "Permendagri":
            errors.append(f"{row['source_code_display']}: BNPB crosswalk source_system must be Permendagri")
        if row["mapping_status"] != "qualified_current_crosswalk":
            errors.append(f"{row['source_code_display']}: BNPB crosswalk mapping is not qualified")
        if row["applicable_start_year"] != "2024" or row["applicable_end_year"] != "2024":
            errors.append(f"{row['source_code_display']}: first BNPB crosswalk must remain scoped to 2024")
        if not row["source_name_expected"]:
            errors.append(f"{row['source_code_display']}: expected BNPB source name is required")
        if canonical and canonical["geography_level"] != row["source_admin_type"]:
            errors.append(f"{row['source_code_display']}: source admin type conflicts with canonical geography level")
        if canonical and canonical["canonical_name"] != row["canonical_name"]:
            errors.append(f"{row['source_code_display']}: crosswalk canonical name conflicts with canonical registry")
        if not row["source_code_normalized"].startswith("13"):
            errors.append(f"{row['source_code_display']}: source code is outside the reviewed Sumatera Barat source range")

    qids = [row["qualification_id"] for row in qualifications]
    if len(qids) != len(set(qids)):
        errors.append("BNPB qualification IDs must be unique")
    canonical_ready = [row for row in qualifications if row["promotion_status"] == "canonical_ready"]
    canonical_pairs = {(row["indicator_id"], row["source_column"]) for row in canonical_ready}
    if canonical_pairs != {("flood_events", "BANJIR"), ("landslide_events", "TANAH LONGSOR")}:
        errors.append(f"unexpected first canonical BNPB scope: {sorted(canonical_pairs)}")
    for indicator_id in ("flood_events", "landslide_events", "disaster_affected_population"):
        if indicator_id not in indicators:
            errors.append(f"missing canonical indicator {indicator_id}")
    affected = [row for row in qualifications if row["indicator_id"] == "disaster_affected_population"]
    if len(affected) != 1 or affected[0]["promotion_status"] != "held_source_native":
        errors.append("disaster_affected_population must remain held source-native")
    total_context = [row for row in qualifications if row["series_id"] == "total_disaster_events_2010_2024"]
    if len(total_context) != 1 or total_context[0]["promotion_status"] != "source_native_context":
        errors.append("2010-2024 total disaster events must remain source-native context")
    if total_context and total_context[0]["indicator_id"]:
        errors.append("all-disaster total series must not masquerade as a canonical indicator")

    for required_catalog_id in ("bnpb_satu_data", "bmkg_satu_peta"):
        if required_catalog_id not in catalog:
            errors.append(f"catalog missing {required_catalog_id}")

    doc = DOC.read_text(encoding="utf-8")
    required_phrases = (
        "Meteorological hazard",
        "Recorded disaster event",
        "must not be relabeled as historical flood or landslide counts",
        "38 observations",
        "Forecast API exclusion",
        "Permendagri",
        "code + source-name pair",
    )
    for phrase in required_phrases:
        if phrase not in doc:
            errors.append(f"climate/disaster methodology doc missing phrase {phrase!r}")
    return errors


def main() -> int:
    try:
        errors = validate()
    except (OSError, ValueError) as exc:
        print(f"Climate/disaster foundation validation FAILED: {exc}", file=sys.stderr)
        return 1
    if errors:
        print("Climate/disaster foundation validation FAILED", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Climate/disaster foundation validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
