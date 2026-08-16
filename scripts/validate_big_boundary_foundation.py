from __future__ import annotations

import csv
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data" / "registries" / "geospatial_sources.csv"
GEOGRAPHIES = ROOT / "data" / "registries" / "geographies.csv"
CATALOG = ROOT / "catalog" / "data-catalog.csv"
DOC = ROOT / "docs" / "BIG_BOUNDARY_ACQUISITION.md"

EXPECTED_SOURCE_ID = "big_kabkota_area_june_2026"
EXPECTED_CATALOG_ID = "big_admin_boundaries_june_2026"
EXPECTED_HOST = "geoservices.big.go.id"


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
        errors.append(f"expected exactly one qualified geospatial source in this phase, found {len(sources)}")
        return errors

    source = sources[0]
    if source["source_record_id"] != EXPECTED_SOURCE_ID:
        errors.append(f"unexpected geospatial source id {source['source_record_id']!r}")
    parsed = urlparse(source["official_url"])
    if parsed.scheme != "https" or parsed.hostname != EXPECTED_HOST:
        errors.append("BIG boundary official_url must remain on geoservices.big.go.id over HTTPS")
    expected_values = {
        "organization": "Badan Informasi Geospasial",
        "source_edition": "Juni 2026",
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
    current_sumbar = [
        row
        for row in geographies
        if row["parent_geography_id"] == "idn.13"
        and row["status"] == "current"
        and row["geography_level"] in {"regency", "city"}
    ]
    if len(current_sumbar) != 19:
        errors.append(f"expected 19 current Sumatera Barat kabupaten/kota, found {len(current_sumbar)}")
    bps_codes = [row["bps_code"] for row in current_sumbar]
    if len(bps_codes) != len(set(bps_codes)) or any(not value for value in bps_codes):
        errors.append("current Sumatera Barat canonical BPS codes must be nonblank and unique")

    catalog_ids = {row["source_id"] for row in read_csv(CATALOG)}
    if EXPECTED_CATALOG_ID not in catalog_ids:
        errors.append(f"catalog missing {EXPECTED_CATALOG_ID}")

    doc = DOC.read_text(encoding="utf-8")
    required_phrases = (
        "current boundary snapshot",
        "exactly the 19 current BPS kabupaten/kota codes",
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
    print("BIG boundary foundation validation passed: current June 2026 snapshot contract pinned.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
