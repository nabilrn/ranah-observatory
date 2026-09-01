#!/usr/bin/env python3
"""Validate and materialize selected Sumbar exposure/context source-native tables.

This promotion step keeps source semantics explicit:
- rain-gauge inventory is monitoring capacity, not rainfall observations;
- road surface classes are mutually exclusive surface-length fields;
- ``Rusak Berat`` is a road-condition field and is NOT added into surface totals.

No district/geospatial inference is performed here.
"""

from __future__ import annotations

import csv
import hashlib
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "data/processed/sumbarprov/exposure_context"
OUTPUT_ROOT = ROOT / "data/processed/sumbarprov/context_2024"
SOURCE_MANIFEST = ROOT / "data/manifests/sumbar_exposure_context.json"
VALIDATION_OUTPUT = OUTPUT_ROOT / "validation.json"
RAIN_OUTPUT = OUTPUT_ROOT / "rain_gauge_inventory.csv"
ROAD_OUTPUT = OUTPUT_ROOT / "provincial_road_segments.csv"

RAIN_SOURCE = SOURCE_ROOT / "jumlah-pos-curah-hujan-dinas-sdabk-tahun-2024/01-Sheet1.csv"
ROAD_SOURCE = SOURCE_ROOT / "panjang-jalan-provinsi-berdasarkan-jenis-permukaan-km/01-Stat4.csv"

RAIN_HEADER = ["Penanggung Jawab", "Jumlah"]
ROAD_HEADER = [
    "NOMOR",
    "Nama Ruas Jalan",
    "Panjang Jalan (km)",
    "Beton (km)",
    "Blok Beton (km)",
    "Aspal (km)",
    "Lapen (km)",
    "Rusak Berat (km)",
    "Batu Kali (km)",
    "Kerikil (km)",
    "Tanah (km)",
]
ROAD_OUTPUT_HEADER = [
    "route_number",
    "route_name",
    "length_km",
    "concrete_km",
    "concrete_block_km",
    "asphalt_km",
    "lapen_km",
    "severely_damaged_km",
    "stone_km",
    "gravel_km",
    "earth_km",
]
SURFACE_FIELDS = (
    "concrete_km",
    "concrete_block_km",
    "asphalt_km",
    "lapen_km",
    "stone_km",
    "gravel_km",
    "earth_km",
)
TOTAL_TOLERANCE = Decimal("0.02")
PERCENT_TOLERANCE = Decimal("0.0001")


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decimal(value: str, label: str) -> Decimal:
    text = value.strip()
    if text == "":
        raise RuntimeError(f"missing numeric value: {label}")
    try:
        result = Decimal(text)
    except InvalidOperation as exc:
        raise RuntimeError(f"invalid numeric value for {label}: {value!r}") from exc
    if not result.is_finite():
        raise RuntimeError(f"non-finite numeric value for {label}: {value!r}")
    return result


def decimal_text(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return str(normalized.quantize(Decimal("1")))
    return format(normalized, "f")


def source_manifest() -> dict:
    payload = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    if payload.get("schema") != "ranah-observatory/sumbar-exposure-context-acquisition/v1":
        raise RuntimeError(f"unexpected source manifest schema: {payload.get('schema')!r}")
    packages = {item["role"]: item for item in payload.get("packages", [])}
    required = {"rain_gauge_inventory", "provincial_road_surface_length"}
    if set(packages) != required:
        raise RuntimeError(f"unexpected exposure-context roles: {sorted(packages)}")
    return packages


def verify_manifest_source(package: dict, source: Path) -> None:
    matching = [item for item in package.get("worksheets", []) if item.get("path") == source.relative_to(ROOT).as_posix()]
    if len(matching) != 1:
        raise RuntimeError(f"manifest worksheet mapping mismatch for {source}")
    actual = sha256_path(source)
    expected = matching[0].get("sha256")
    if actual != expected:
        raise RuntimeError(f"source checksum mismatch for {source}: expected={expected} actual={actual}")


def materialize_rain_inventory(package: dict) -> dict:
    verify_manifest_source(package, RAIN_SOURCE)
    with RAIN_SOURCE.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    if not rows or rows[0] != RAIN_HEADER:
        raise RuntimeError(f"rain-gauge header changed: {rows[0] if rows else None!r}")
    body = rows[1:]
    if not body:
        raise RuntimeError("rain-gauge inventory has no rows")

    normalized: list[tuple[str, int]] = []
    seen: set[str] = set()
    total = 0
    for index, row in enumerate(body, start=2):
        if len(row) != 2:
            raise RuntimeError(f"rain-gauge row {index} has {len(row)} columns")
        manager = row[0].strip()
        if not manager or manager in seen:
            raise RuntimeError(f"invalid/duplicate rain-gauge manager at row {index}: {manager!r}")
        count_value = decimal(row[1], f"rain-gauge row {index} count")
        if count_value != count_value.to_integral() or count_value < 0:
            raise RuntimeError(f"rain-gauge count must be a non-negative integer at row {index}: {row[1]!r}")
        count = int(count_value)
        seen.add(manager)
        normalized.append((manager, count))
        total += count

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    with RAIN_OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["responsible_unit", "rain_gauge_post_count"])
        writer.writerows(normalized)

    return {
        "source_role": "rain_gauge_inventory",
        "semantic_role": "hydrometeorological_monitoring_capacity",
        "not_rainfall_observations": True,
        "responsible_unit_count": len(normalized),
        "rain_gauge_post_total": total,
        "output": RAIN_OUTPUT.relative_to(ROOT).as_posix(),
        "output_sha256": sha256_path(RAIN_OUTPUT),
    }


def road_record(row: list[str], line_number: int) -> dict[str, Decimal | str]:
    if len(row) != len(ROAD_HEADER):
        raise RuntimeError(f"road row {line_number} has {len(row)} columns, expected {len(ROAD_HEADER)}")
    route_number = row[0].strip()
    route_name = row[1].strip()
    if not route_number or not route_name:
        raise RuntimeError(f"road segment missing number/name at row {line_number}")
    values = [decimal(row[index], f"road row {line_number} {ROAD_HEADER[index]}") for index in range(2, len(row))]
    if any(value < 0 for value in values):
        raise RuntimeError(f"negative road value at row {line_number}")
    result: dict[str, Decimal | str] = {
        "route_number": route_number,
        "route_name": route_name,
        "length_km": values[0],
        "concrete_km": values[1],
        "concrete_block_km": values[2],
        "asphalt_km": values[3],
        "lapen_km": values[4],
        "severely_damaged_km": values[5],
        "stone_km": values[6],
        "gravel_km": values[7],
        "earth_km": values[8],
    }
    surface_total = sum((result[field] for field in SURFACE_FIELDS), Decimal("0"))
    difference = abs(surface_total - result["length_km"])
    if difference > TOTAL_TOLERANCE:
        raise RuntimeError(
            f"surface lengths do not reconcile for route {route_number}: "
            f"surface={surface_total} length={result['length_km']} difference={difference}"
        )
    if result["severely_damaged_km"] > result["length_km"] + TOTAL_TOLERANCE:
        raise RuntimeError(f"severely damaged length exceeds route length for {route_number}")
    return result


def materialize_roads(package: dict) -> dict:
    verify_manifest_source(package, ROAD_SOURCE)
    with ROAD_SOURCE.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    if not rows or rows[0] != ROAD_HEADER:
        raise RuntimeError(f"road header changed: {rows[0] if rows else None!r}")

    total_positions = [index for index, row in enumerate(rows) if row and row[0].strip().upper() == "TOTAL"]
    percent_positions = [index for index, row in enumerate(rows) if row and row[0].strip().lower() == "persentase"]
    if len(total_positions) != 1 or len(percent_positions) != 1:
        raise RuntimeError("road source must contain exactly one TOTAL and one Persentase row")
    total_index = total_positions[0]
    percent_index = percent_positions[0]
    if percent_index != total_index + 1 or percent_index != len(rows) - 1:
        raise RuntimeError("road TOTAL/Persentase rows are not the final two rows")

    segments = [road_record(row, line_number=index + 2) for index, row in enumerate(rows[1:total_index])]
    if not segments:
        raise RuntimeError("road dataset contains no segment rows")
    route_numbers = [str(item["route_number"]) for item in segments]
    if len(route_numbers) != len(set(route_numbers)):
        raise RuntimeError("road route numbers are not unique")

    total_row = rows[total_index]
    if len(total_row) != len(ROAD_HEADER):
        raise RuntimeError("road TOTAL row width changed")
    source_totals = {
        "length_km": decimal(total_row[2], "road TOTAL length"),
        "concrete_km": decimal(total_row[3], "road TOTAL concrete"),
        "concrete_block_km": decimal(total_row[4], "road TOTAL concrete block"),
        "asphalt_km": decimal(total_row[5], "road TOTAL asphalt"),
        "lapen_km": decimal(total_row[6], "road TOTAL lapen"),
        "severely_damaged_km": decimal(total_row[7], "road TOTAL severely damaged"),
        "stone_km": decimal(total_row[8], "road TOTAL stone"),
        "gravel_km": decimal(total_row[9], "road TOTAL gravel"),
        "earth_km": decimal(total_row[10], "road TOTAL earth"),
    }

    computed_totals: dict[str, Decimal] = {}
    for field in source_totals:
        computed_totals[field] = sum((item[field] for item in segments), Decimal("0"))
        if abs(computed_totals[field] - source_totals[field]) > TOTAL_TOLERANCE:
            raise RuntimeError(
                f"road source TOTAL mismatch for {field}: "
                f"source={source_totals[field]} computed={computed_totals[field]}"
            )

    source_surface_total = sum((source_totals[field] for field in SURFACE_FIELDS), Decimal("0"))
    if abs(source_surface_total - source_totals["length_km"]) > TOTAL_TOLERANCE:
        raise RuntimeError(
            f"road source surface TOTAL does not reconcile: surface={source_surface_total} length={source_totals['length_km']}"
        )

    percent_row = rows[percent_index]
    if len(percent_row) != len(ROAD_HEADER):
        raise RuntimeError("road Persentase row width changed")
    percentage_fields = {
        "concrete_km": 3,
        "concrete_block_km": 4,
        "asphalt_km": 5,
        "lapen_km": 6,
        "severely_damaged_km": 7,
        "stone_km": 8,
        "gravel_km": 9,
        "earth_km": 10,
    }
    source_percentages: dict[str, Decimal] = {}
    for field, column in percentage_fields.items():
        source_value = decimal(percent_row[column], f"road Persentase {field}")
        expected = (source_totals[field] / source_totals["length_km"]).quantize(Decimal("0.0001"))
        if abs(source_value - expected) > PERCENT_TOLERANCE:
            raise RuntimeError(
                f"road percentage mismatch for {field}: source={source_value} expected={expected}"
            )
        source_percentages[field] = source_value

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    with ROAD_OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(ROAD_OUTPUT_HEADER)
        for item in segments:
            writer.writerow([
                item["route_number"],
                item["route_name"],
                *[decimal_text(item[field]) for field in ROAD_OUTPUT_HEADER[2:]],
            ])

    return {
        "source_role": "provincial_road_surface_length",
        "semantic_role": "provincial_road_exposure_and_condition_context",
        "segment_count": len(segments),
        "surface_fields_mutually_exclusive": list(SURFACE_FIELDS),
        "severely_damaged_is_overlapping_condition": True,
        "totals": {field: decimal_text(value) for field, value in source_totals.items()},
        "source_percentages": {field: decimal_text(value) for field, value in source_percentages.items()},
        "output": ROAD_OUTPUT.relative_to(ROOT).as_posix(),
        "output_sha256": sha256_path(ROAD_OUTPUT),
    }


def main() -> None:
    packages = source_manifest()
    rain_result = materialize_rain_inventory(packages["rain_gauge_inventory"])
    road_result = materialize_roads(packages["provincial_road_surface_length"])
    result = {
        "schema": "ranah-observatory/sumbar-exposure-context-validated/v1",
        "year": 2024,
        "source_manifest": SOURCE_MANIFEST.relative_to(ROOT).as_posix(),
        "source_manifest_sha256": sha256_path(SOURCE_MANIFEST),
        "missing_values_inferred": False,
        "geography_inferred": False,
        "rain_gauge_inventory": rain_result,
        "provincial_roads": road_result,
    }
    VALIDATION_OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "rain_gauge_posts": rain_result["rain_gauge_post_total"],
        "rain_gauge_units": rain_result["responsible_unit_count"],
        "road_segments": road_result["segment_count"],
        "road_total_km": road_result["totals"]["length_km"],
        "road_severely_damaged_km": road_result["totals"]["severely_damaged_km"],
        "validation": VALIDATION_OUTPUT.relative_to(ROOT).as_posix(),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
