#!/usr/bin/env python3
"""Promote validated 2024 Satu Data Sumbar BPBD impact tables to canonical observations.

This materializer is intentionally narrow. It promotes only columns whose meaning is
explicit in the source workbook headers and validates each source TOTAL row before
writing canonical observations. It never treats blanks as zero and never combines
conceptually different source columns into synthetic impact metrics.
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "data/processed/bpbd/sumbar_open_data/2024"
OUT_DIR = ROOT / "data/processed/bpbd/disaster_impact_2024"
OBS_PATH = OUT_DIR / "bpbd-disaster-impact-canonical-observations.csv"
PROV_PATH = OUT_DIR / "bpbd-disaster-impact-canonical-provenance.csv"
MANIFEST_PATH = OUT_DIR / "materialization.json"
GEOGRAPHY_MAP = ROOT / "data/registries/bps_panel_geography_map.csv"
ACQUISITION_MANIFEST = ROOT / "data/manifests/sumbar_bpbd_open_data_2024.json"

SOURCES = {
    "casualties": {
        "package": "jumlah-korban-per-kabkota-2024",
        "file": "01-Sheet1.csv",
        "columns": {
            "Meninggal": "deaths",
            "Hilang": "missing_people",
            "Luka/Sakit": "injured_or_sick_people",
            "Menderita": "suffering_people",
            "Mengungsi": "displaced_people",
        },
        "unit": "people",
    },
    "housing": {
        "package": "dampak-bencana-terhadap-pemukiman-per-kabkota-2024",
        "file": "01-Sheet1.csv",
        "columns": {
            "Rumah Rusak Berat": "houses_heavily_damaged",
            "Rumah Rusak Sedang": "houses_moderately_damaged",
            "Rumah Rusak Ringan": "houses_lightly_damaged",
            "Rumah Terendam": "houses_flooded",
        },
        "unit": "housing_units",
    },
    "facilities": {
        "package": "dampak-bencana-terhadap-fasilitas-umum-per-kabkota-2024",
        "file": "01-Sheet1.csv",
        "columns": {
            "Fasilitas Pendidikan": "education_facilities_affected",
            "Fasilitasi Peribadatan": "worship_facilities_affected",
            "Fasilitas Kesehatan": "health_facilities_affected",
            "Fasilitas Kantor": "office_facilities_affected",
            "Jembatan": "bridges_affected",
        },
        "unit": "facilities",
    },
}

OBS_FIELDS = [
    "observation_id",
    "indicator_id",
    "geography_id",
    "time_start",
    "time_end",
    "frequency",
    "value_numeric",
    "unit",
    "claim_type",
    "provenance_id",
    "suppressed",
    "comparable",
    "methodology_version",
    "price_basis",
    "notes",
]

PROV_FIELDS = [
    "provenance_id",
    "source_organization",
    "source_data",
    "source_title",
    "source_path",
    "source_sha256",
    "resource_url",
    "resource_sha256",
    "retrieved_at",
    "notes",
]


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:24]
    return f"{prefix}_{digest}"


def parse_nonnegative_integer(value: str, context: str) -> int:
    raw = str(value).strip()
    if raw == "":
        raise RuntimeError(f"blank value is not promoted as zero: {context}")
    try:
        number = float(raw)
    except ValueError as exc:
        raise RuntimeError(f"non-numeric value {raw!r}: {context}") from exc
    rounded = round(number)
    if abs(number - rounded) > 1e-9 or rounded < 0:
        raise RuntimeError(f"expected nonnegative integer, got {raw!r}: {context}")
    return int(rounded)


def load_geography_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    with GEOGRAPHY_MAP.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            code = str(row["bps_vervar_id"]).strip()
            if len(code) != 4 or not code.startswith("13"):
                continue
            if row["mapping_type"] != "direct_current_code":
                continue
            mapping[code] = row["canonical_geography_id"].strip()
    if len(mapping) != 19:
        raise RuntimeError(f"expected 19 current Sumbar BPS geography mappings, found {len(mapping)}")
    return mapping


def load_acquisition_manifest() -> tuple[dict, dict[str, dict]]:
    manifest = json.loads(ACQUISITION_MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("year") != 2024 or manifest.get("missing_values_inferred") is not False:
        raise RuntimeError("unexpected BPBD acquisition manifest contract")
    packages = {item["package_slug"]: item for item in manifest.get("packages", [])}
    return manifest, packages


def normalize_source_name(value: str) -> str:
    return " ".join(str(value).strip().upper().split())


def source_path(package: str, filename: str) -> Path:
    return SOURCE_ROOT / package / filename


def main() -> None:
    geography_map = load_geography_map()
    acquisition_manifest, packages = load_acquisition_manifest()
    retrieved_at = acquisition_manifest["retrieved_at"]

    observations: list[dict] = []
    provenance: list[dict] = []
    validations: list[dict] = []
    seen_observation_keys: set[tuple[str, str, int]] = set()
    district_sets: list[set[str]] = []

    for family, config in SOURCES.items():
        package_slug = config["package"]
        path = source_path(package_slug, config["file"])
        package = packages.get(package_slug)
        if not package:
            raise RuntimeError(f"acquisition manifest missing package {package_slug}")
        if not path.exists():
            raise RuntimeError(f"source-native worksheet missing: {path.relative_to(ROOT)}")

        worksheet = next(
            (sheet for sheet in package.get("worksheets", []) if sheet.get("path") == path.relative_to(ROOT).as_posix()),
            None,
        )
        if not worksheet:
            raise RuntimeError(f"manifest does not bind worksheet {path.relative_to(ROOT)}")
        actual_sha = sha256_path(path)
        if actual_sha != worksheet.get("sha256"):
            raise RuntimeError(f"worksheet checksum mismatch: {path.relative_to(ROOT)}")

        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        if not rows:
            raise RuntimeError(f"empty BPBD worksheet: {path.relative_to(ROOT)}")

        header = set(rows[0].keys())
        required = {"Kode Wilayah", "Jenis Bencana", *config["columns"].keys()}
        if not required.issubset(header):
            raise RuntimeError(
                f"unexpected columns in {path.relative_to(ROOT)}; missing={sorted(required - header)} header={sorted(header)}"
            )

        total_rows = [row for row in rows if str(row["Kode Wilayah"]).strip() == ""]
        district_rows = [row for row in rows if str(row["Kode Wilayah"]).strip() != ""]
        if len(total_rows) != 1:
            raise RuntimeError(f"expected exactly one TOTAL row in {path.relative_to(ROOT)}, found {len(total_rows)}")
        total_row = total_rows[0]
        if normalize_source_name(total_row["Jenis Bencana"]) != "TOTAL":
            raise RuntimeError(f"blank-code row is not TOTAL in {path.relative_to(ROOT)}")
        if len(district_rows) != 19:
            raise RuntimeError(f"expected 19 district rows in {path.relative_to(ROOT)}, found {len(district_rows)}")

        codes = {str(row["Kode Wilayah"]).strip() for row in district_rows}
        if codes != set(geography_map):
            raise RuntimeError(
                f"district code set mismatch in {path.relative_to(ROOT)}; missing={sorted(set(geography_map)-codes)} extra={sorted(codes-set(geography_map))}"
            )
        district_sets.append(codes)

        provenance_id = stable_id("bpbdprov", package_slug, actual_sha)
        provenance.append(
            {
                "provenance_id": provenance_id,
                "source_organization": "BPBD Provinsi Sumatera Barat",
                "source_data": "Pusdalops BPBD Sumatera Barat",
                "source_title": package.get("title", ""),
                "source_path": path.relative_to(ROOT).as_posix(),
                "source_sha256": actual_sha,
                "resource_url": package.get("resource_url", ""),
                "resource_sha256": package.get("download_sha256", ""),
                "retrieved_at": retrieved_at,
                "notes": "Source-native XLSX worksheet materialized to CSV without semantic reinterpretation before canonical promotion.",
            }
        )

        source_totals: dict[str, int] = {}
        computed_totals: dict[str, int] = {}
        for source_column, indicator_id in config["columns"].items():
            source_total = parse_nonnegative_integer(total_row[source_column], f"{package_slug}:TOTAL:{source_column}")
            computed_total = sum(
                parse_nonnegative_integer(row[source_column], f"{package_slug}:{row['Kode Wilayah']}:{source_column}")
                for row in district_rows
            )
            if source_total != computed_total:
                raise RuntimeError(
                    f"TOTAL mismatch for {package_slug}/{source_column}: source={source_total} computed={computed_total}"
                )
            source_totals[indicator_id] = source_total
            computed_totals[indicator_id] = computed_total

        for row_number, row in enumerate(district_rows, start=2):
            code = str(row["Kode Wilayah"]).strip()
            geography_id = geography_map[code]
            source_name = normalize_source_name(row["Jenis Bencana"])
            if not source_name.startswith(("KABUPATEN ", "KOTA ")):
                raise RuntimeError(f"unexpected BPBD geography label {source_name!r} at {package_slug}:{row_number}")

            for source_column, indicator_id in config["columns"].items():
                value = parse_nonnegative_integer(row[source_column], f"{package_slug}:{code}:{source_column}")
                key = (indicator_id, geography_id, 2024)
                if key in seen_observation_keys:
                    raise RuntimeError(f"duplicate canonical observation key: {key}")
                seen_observation_keys.add(key)
                observations.append(
                    {
                        "observation_id": stable_id("bpbdimpactobs", indicator_id, geography_id, "2024"),
                        "indicator_id": indicator_id,
                        "geography_id": geography_id,
                        "time_start": "2024-01-01",
                        "time_end": "2024-12-31",
                        "frequency": "annual",
                        "value_numeric": value,
                        "unit": config["unit"],
                        "claim_type": "observed",
                        "provenance_id": provenance_id,
                        "suppressed": "false",
                        "comparable": "",
                        "methodology_version": "BPBD/Pusdalops 2024 published table",
                        "price_basis": "",
                        "notes": (
                            f"source_geography_code={code}; source_geography_name={source_name}; "
                            f"source_column={source_column}; missing_values_inferred=false"
                        ),
                    }
                )

        validations.append(
            {
                "family": family,
                "package_slug": package_slug,
                "source_path": path.relative_to(ROOT).as_posix(),
                "source_sha256": actual_sha,
                "district_row_count": len(district_rows),
                "source_totals": source_totals,
                "computed_totals": computed_totals,
                "total_validation": "passed",
            }
        )

    if any(codes != district_sets[0] for codes in district_sets[1:]):
        raise RuntimeError("BPBD impact files do not cover the same 19 district codes")

    expected_observations = 19 * sum(len(config["columns"]) for config in SOURCES.values())
    if len(observations) != expected_observations:
        raise RuntimeError(f"expected {expected_observations} observations, got {len(observations)}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    observations.sort(key=lambda row: (row["indicator_id"], row["geography_id"]))
    provenance.sort(key=lambda row: row["provenance_id"])

    with OBS_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OBS_FIELDS)
        writer.writeheader()
        writer.writerows(observations)

    with PROV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=PROV_FIELDS)
        writer.writeheader()
        writer.writerows(provenance)

    indicator_totals = {
        indicator: sum(int(row["value_numeric"]) for row in observations if row["indicator_id"] == indicator)
        for config in SOURCES.values()
        for indicator in config["columns"].values()
    }

    materialized_at = datetime.now(timezone.utc).isoformat()
    manifest = {
        "schema": "ranah-observatory/bpbd-disaster-impact-materialization/v1",
        "materialized_at": materialized_at,
        "period": 2024,
        "source_organization": "BPBD Provinsi Sumatera Barat",
        "source_data": "Pusdalops BPBD Sumatera Barat",
        "district_count": 19,
        "indicator_count": len(indicator_totals),
        "observation_count": len(observations),
        "missing_values_inferred": False,
        "synthetic_cross_indicator_totals_created": False,
        "total_row_validation": "passed",
        "indicator_totals": indicator_totals,
        "validations": validations,
        "outputs": {
            "observations": {
                "path": OBS_PATH.relative_to(ROOT).as_posix(),
                "sha256": sha256_path(OBS_PATH),
            },
            "provenance": {
                "path": PROV_PATH.relative_to(ROOT).as_posix(),
                "sha256": sha256_path(PROV_PATH),
            },
        },
        "interpretation_notes": [
            "Menderita and Mengungsi remain separate source indicators and are not summed into a synthetic affected-population total.",
            "Rumah Terendam remains separate from the three Rumah Rusak severity indicators.",
            "Facility categories are kept separate; no synthetic facility total is stored as a canonical observation.",
            "Economic loss is not included because the acquired 2024 package set does not contain a validated 2024 loss table.",
        ],
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "observations": len(observations),
                "indicators": len(indicator_totals),
                "districts": 19,
                "total_validation": "passed",
                "indicator_totals": indicator_totals,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
