from __future__ import annotations

import csv
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data" / "registries" / "geospatial_sources.csv"
GEOGRAPHIES = ROOT / "data" / "registries" / "geographies.csv"
CROSSWALK = ROOT / "data" / "registries" / "big_geography_map.csv"
CATALOG = ROOT / "catalog" / "data-catalog.csv"
DOC = ROOT / "docs" / "BIG_BOUNDARY_ACQUISITION.md"

EXPECTED_SOURCE_ID = "big_kabkota_area_june_2026"
EXPECTED_CATALOG_ID = "big_admin_boundaries_june_2026"
EXPECTED_HOST = "geoservices.big.go.id"
EXPECTED_EDITION = "Juni 2026"
CRITICAL_PERMENDAGRI_MAPPINGS = {
    "1301": ("PESISIR SELATAN", "idn.13.1302"),
    "1309": ("KEPULAUAN MENTAWAI", "idn.13.1301"),
    "1310": ("DHARMASRAYA", "idn.13.1311"),
    "1311": ("SOLOK SELATAN", "idn.13.1310"),
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [
            {key: (value or "").strip() for key, value in row.items()}
            for row in csv.DictReader(handle)
        ]


def validate() -> list[str]:
    errors: list[str] = []
    sources = read_csv(SOURCES)
    if len(sources) != 1:
        errors.append(
            f"expected exactly one qualified geospatial source in this phase, found {len(sources)}"
        )
        return errors

    source = sources[0]
    if source["source_record_id"] != EXPECTED_SOURCE_ID:
        errors.append(f"unexpected geospatial source id {source['source_record_id']!r}")
    parsed = urlparse(source["official_url"])
    if parsed.scheme != "https" or parsed.hostname != EXPECTED_HOST:
        errors.append(
            "BIG boundary official_url must remain on geoservices.big.go.id over HTTPS"
        )
    expected_values = {
        "organization": "Badan Informasi Geospasial",
        "source_edition": EXPECTED_EDITION,
        "temporal_role": "current_snapshot",
        "geography_grain": "kabupaten_kota",
        "geometry_type": "polygon",
        "crs": "EPSG:4326",
        "auth_required": "false",
        "qualification_status": "qualified_discovery",
        "canonical_role": "current_zonal_geometry_candidate",
    }
    for field, expected in expected_values.items():
        if source.get(field) != expected:
            errors.append(
                f"{EXPECTED_SOURCE_ID}: {field} changed from {expected!r} to {source.get(field)!r}"
            )

    geographies = read_csv(GEOGRAPHIES)
    current_sumbar = {
        row["geography_id"]: row
        for row in geographies
        if row["parent_geography_id"] == "idn.13"
        and row["status"] == "current"
        and row["geography_level"] in {"regency", "city"}
    }
    if len(current_sumbar) != 19:
        errors.append(
            f"expected 19 current Sumatera Barat kabupaten/kota, found {len(current_sumbar)}"
        )
    bps_codes = [row["bps_code"] for row in current_sumbar.values()]
    if len(bps_codes) != len(set(bps_codes)) or any(not value for value in bps_codes):
        errors.append(
            "current Sumatera Barat canonical BPS codes must be nonblank and unique"
        )

    crosswalk = read_csv(CROSSWALK)
    if len(crosswalk) != 19:
        errors.append(f"BIG June 2026 crosswalk has {len(crosswalk)} rows, expected 19")
    source_codes = [row["source_code_normalized"] for row in crosswalk]
    source_names = [row["source_name_expected"].upper() for row in crosswalk]
    canonical_ids = [row["canonical_geography_id"] for row in crosswalk]
    if len(source_codes) != len(set(source_codes)):
        errors.append("BIG crosswalk Permendagri source codes must be unique")
    if len(source_names) != len(set(source_names)):
        errors.append("BIG crosswalk source names must be unique")
    if len(canonical_ids) != len(set(canonical_ids)):
        errors.append("BIG crosswalk canonical geography IDs must be unique")
    if set(canonical_ids) != set(current_sumbar):
        errors.append(
            "BIG crosswalk must cover exactly the 19 current canonical Sumatera Barat geographies"
        )

    by_source_code = {row["source_code_normalized"]: row for row in crosswalk}
    for code, (expected_name, expected_geography_id) in CRITICAL_PERMENDAGRI_MAPPINGS.items():
        row = by_source_code.get(code)
        if row is None:
            errors.append(f"BIG crosswalk missing critical Permendagri code {code}")
            continue
        if (
            row["source_name_expected"].upper() != expected_name
            or row["canonical_geography_id"] != expected_geography_id
        ):
            errors.append(
                f"BIG critical Permendagri mapping {code} changed unexpectedly: "
                f"name={row['source_name_expected']!r} canonical={row['canonical_geography_id']!r}"
            )

    for row in crosswalk:
        canonical = current_sumbar.get(row["canonical_geography_id"])
        if row["source_system"] != "Permendagri":
            errors.append(
                f"{row['source_code_display']}: BIG crosswalk source_system must be Permendagri"
            )
        if row["source_edition"] != EXPECTED_EDITION:
            errors.append(
                f"{row['source_code_display']}: BIG crosswalk must remain scoped to {EXPECTED_EDITION}"
            )
        if row["mapping_status"] != "qualified_current_crosswalk":
            errors.append(
                f"{row['source_code_display']}: BIG crosswalk mapping is not qualified"
            )
        if not row["source_name_expected"]:
            errors.append(
                f"{row['source_code_display']}: expected BIG source name is required"
            )
        if canonical and canonical["geography_level"] != row["source_admin_type"]:
            errors.append(
                f"{row['source_code_display']}: BIG source admin type conflicts with canonical geography level"
            )
        if canonical and canonical["canonical_name"] != row["canonical_name"]:
            errors.append(
                f"{row['source_code_display']}: BIG crosswalk canonical name conflicts with canonical registry"
            )
        if not row["source_code_normalized"].startswith("13"):
            errors.append(
                f"{row['source_code_display']}: BIG source code is outside Sumatera Barat Permendagri range"
            )

    catalog_ids = {row["source_id"] for row in read_csv(CATALOG)}
    if EXPECTED_CATALOG_ID not in catalog_ids:
        errors.append(f"catalog missing {EXPECTED_CATALOG_ID}")

    doc = DOC.read_text(encoding="utf-8")
    required_phrases = (
        "current boundary snapshot",
        "`KDBBPS`: 0 nonblank values",
        "`KDPBPS`: 0 nonblank values",
        "Permendagri/PUM codes",
        "exactly 19 current Sumatera Barat mappings",
        "historical-boundary continuity remains explicitly false",
        "current-boundary reconstruction",
        "not the same object as a historical administrative-statistics panel",
    )
    for phrase in required_phrases:
        if phrase not in doc:
            errors.append(f"BIG boundary methodology doc missing phrase {phrase!r}")

    return errors


def main() -> int:
    try:
        errors = validate()
    except (OSError, ValueError) as exc:
        print(f"BIG boundary foundation validation FAILED: {exc}", file=sys.stderr)
        return 1
    if errors:
        print("BIG boundary foundation validation FAILED", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(
        "BIG boundary foundation validation passed: June 2026 source contract and "
        "19-row Permendagri-to-canonical crosswalk pinned."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
