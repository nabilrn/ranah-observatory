#!/usr/bin/env python3
"""Validate and materialize BPBD 2023 loss/impact and 2024 context tables.

Rules:
- Source-native CSV hashes must match the acquisition manifest.
- Current Sumbar district names must map exactly through the canonical geography registry.
- 2023 event counts must agree between social-impact and economic-loss tables.
- Economic-loss blanks/dashes remain missing; they are never converted to zero.
- Count-table dash markers are interpreted as explicit source zeros and validated to totals.
- Excel floating-point artifacts are accepted only when within tolerance of an integer.
- 2024 casualties by hazard must reconcile to the already-validated district-impact totals.
- Flood/landslide monthly totals must reconcile to the BNPB canonical 2024 event totals.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_MANIFEST = ROOT / "data/manifests/sumbar_bpbd_priority_context.json"
GEOGRAPHIES = ROOT / "data/registries/geographies.csv"
IMPACT_2024 = ROOT / "data/processed/bpbd/disaster_impact_2024/bpbd-disaster-impact-canonical-observations.csv"
EVENTS_2024 = ROOT / "data/processed/bnpb/disaster/bnpb-disaster-canonical-observations.csv"

OUTPUT_2023 = ROOT / "data/processed/bpbd/disaster_impact_2023"
OUTPUT_2024 = ROOT / "data/processed/bpbd/disaster_context_2024"
OBS_2023 = OUTPUT_2023 / "bpbd-disaster-impact-2023-canonical-observations.csv"
PROV_2023 = OUTPUT_2023 / "bpbd-disaster-impact-2023-provenance.csv"
LOSS_COVERAGE_2023 = OUTPUT_2023 / "bpbd-disaster-loss-2023-coverage.csv"
CTX_CASUALTY_2024 = OUTPUT_2024 / "bpbd-casualties-by-hazard-2024.csv"
CTX_MONTHLY_2024 = OUTPUT_2024 / "bpbd-monthly-events-by-hazard-2024.csv"
CTX_SIRENS_2024 = OUTPUT_2024 / "bpbd-tsunami-sirens-2024.csv"
MATERIALIZATION = OUTPUT_2024 / "materialization.json"

HAZARDS = {
    "Banjir": "flood",
    "Cuaca ekstrem": "extreme_weather",
    "Erupsi Gunung Api": "volcanic_eruption",
    "Gelombang Pasang dan abrasi": "tidal_wave_and_coastal_erosion",
    "Kebakaran Hutan dan Lahan": "forest_and_land_fire",
    "Kekeringan": "drought",
    "Tanah Longsor": "landslide",
}

CASUALTY_HEADERS = {
    "Meninggal": "deaths",
    "Hilang": "missing_people",
    "Luka/Sakit": "injured_or_sick_people",
    "Menderita": "suffering_people",
    "Mengungsi": "displaced_people",
}

MONTHS = {
    "Januari": 1, "Februari": 2, "Maret": 3, "April": 4,
    "Mei": 5, "Juni": 6, "Juli": 7, "Agustus": 8,
    "September": 9, "Oktober": 10, "November": 11, "Desember": 12,
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(path: Path) -> list[list[str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [[cell.strip() for cell in row] for row in csv.reader(handle)]


def as_int(value: str, *, dash_zero: bool = False) -> int:
    text = value.strip()
    if dash_zero and text in {"", "-"}:
        return 0
    if text == "":
        raise RuntimeError("blank numeric cell")
    number = float(text)
    rounded = round(number)
    if not math.isfinite(number) or abs(number - rounded) > 1e-6:
        raise RuntimeError(f"expected integer-like value, got {value!r}")
    if rounded < 0:
        raise RuntimeError(f"negative count not allowed: {value!r}")
    return int(rounded)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_manifest() -> tuple[dict, dict[str, dict]]:
    payload = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    if payload.get("schema") != "ranah-observatory/sumbar-bpbd-priority-context-acquisition/v1":
        raise RuntimeError("unsupported priority-context acquisition manifest")
    if payload.get("missing_values_inferred") is not False:
        raise RuntimeError("acquisition manifest indicates missing-value inference")
    by_role = {str(item["role"]): item for item in payload.get("packages", [])}
    expected = {
        "economic_loss", "impact_continuity", "housing_continuity",
        "casualties_by_hazard", "monthly_events", "mitigation_capacity",
    }
    if set(by_role) != expected:
        raise RuntimeError(f"priority-context roles mismatch: {sorted(by_role)}")
    return payload, by_role


def role_sheet(by_role: dict[str, dict], role: str) -> Path:
    package = by_role[role]
    sheets = package.get("worksheets", [])
    if len(sheets) != 1:
        raise RuntimeError(f"{role}: expected one worksheet, found {len(sheets)}")
    path = ROOT / sheets[0]["path"]
    if sha256(path) != sheets[0]["sha256"]:
        raise RuntimeError(f"{role}: source-native worksheet checksum mismatch")
    return path


def load_geography_aliases() -> tuple[dict[str, tuple[str, str]], set[str]]:
    aliases: dict[str, tuple[str, str]] = {}
    ids: set[str] = set()
    with GEOGRAPHIES.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["parent_geography_id"] != "idn.13" or row["geography_level"] not in {"regency", "city"}:
                continue
            if row["status"] != "current":
                continue
            geography_id = row["geography_id"].strip()
            name = row["canonical_name"].strip()
            ids.add(geography_id)
            candidates = {name.casefold()}
            if row["geography_level"] == "regency":
                candidates.add(f"kabupaten {name}".casefold())
            else:
                candidates.add(f"kota {name}".casefold())
            for alias in candidates:
                existing = aliases.get(alias)
                if existing and existing[0] != geography_id:
                    raise RuntimeError(f"ambiguous geography alias {alias!r}")
                aliases[alias] = (geography_id, name)
    if len(ids) != 19:
        raise RuntimeError(f"expected 19 current Sumbar districts, found {len(ids)}")
    return aliases, ids


def map_geography(source_name: str, aliases: dict[str, tuple[str, str]]) -> tuple[str, str]:
    key = re.sub(r"\s+", " ", source_name.strip()).casefold()
    result = aliases.get(key)
    if not result:
        raise RuntimeError(f"unmapped Sumbar geography name: {source_name!r}")
    return result


def provenance_row(provenance_id: str, role: str, package: dict, sheet: Path, note: str) -> dict:
    return {
        "provenance_id": provenance_id,
        "source_organization": package.get("organization") or "BPBD Provinsi Sumatera Barat",
        "source_title": package.get("title"),
        "source_role": role,
        "source_path": sheet.relative_to(ROOT).as_posix(),
        "source_sha256": sha256(sheet),
        "download_sha256": package.get("download_sha256"),
        "resource_url": package.get("resource_url"),
        "notes": note,
    }


def build_2023(by_role: dict[str, dict], aliases: dict[str, tuple[str, str]], expected_ids: set[str]) -> dict:
    social_path = role_sheet(by_role, "impact_continuity")
    housing_path = role_sheet(by_role, "housing_continuity")
    loss_path = role_sheet(by_role, "economic_loss")

    social = read_rows(social_path)
    housing = read_rows(housing_path)
    loss = read_rows(loss_path)

    if social[0] != ["Kabupaten/Kota", "Jumlah Kejadian", "Meninggal", "Hilang", "Luka/ Sakit", "Mengungsi"]:
        raise RuntimeError(f"unexpected 2023 social header: {social[0]}")
    if housing[0] != ["Kabupaten", "Rusak Berat", "Rusak Sedang", "Rusak Ringan", "Jumlah"]:
        raise RuntimeError(f"unexpected 2023 housing header: {housing[0]}")
    if loss[0][:3] != ["Kabupaten/Kota", "Jumlah Kejadian", "Taksiran kerugian"]:
        raise RuntimeError(f"unexpected 2023 loss header: {loss[0]}")

    observations: list[dict] = []
    loss_coverage: list[dict] = []
    social_events: dict[str, int] = {}
    social_totals = defaultdict(int)
    social_ids: set[str] = set()

    social_indicators = [
        ("deaths", 2), ("missing_people", 3),
        ("injured_or_sick_people", 4), ("displaced_people", 5),
    ]
    for row in social[1:-1]:
        geography_id, canonical_name = map_geography(row[0], aliases)
        if geography_id in social_ids:
            raise RuntimeError(f"duplicate 2023 social geography {geography_id}")
        social_ids.add(geography_id)
        events = as_int(row[1])
        social_events[geography_id] = events
        social_totals["disaster_events_reported"] += events
        observations.append(make_obs(2023, geography_id, "disaster_events_reported", events, "count", "bpbd2023_social", canonical_name))
        for indicator, index in social_indicators:
            value = as_int(row[index], dash_zero=True)
            social_totals[indicator] += value
            observations.append(make_obs(2023, geography_id, indicator, value, "people", "bpbd2023_social", canonical_name))

    if social_ids != expected_ids:
        raise RuntimeError(f"2023 social coverage mismatch: {sorted(expected_ids-social_ids)}")
    total = social[-1]
    expected_social_totals = {
        "disaster_events_reported": as_int(total[1]),
        "deaths": as_int(total[2], dash_zero=True),
        "missing_people": as_int(total[3], dash_zero=True),
        "injured_or_sick_people": as_int(total[4], dash_zero=True),
        "displaced_people": as_int(total[5], dash_zero=True),
    }
    if dict(social_totals) != expected_social_totals:
        raise RuntimeError(f"2023 social total mismatch: calculated={dict(social_totals)} source={expected_social_totals}")

    housing_totals = defaultdict(int)
    housing_ids: set[str] = set()
    for row in housing[1:-1]:
        geography_id, canonical_name = map_geography(row[0], aliases)
        if geography_id in housing_ids:
            raise RuntimeError(f"duplicate 2023 housing geography {geography_id}")
        housing_ids.add(geography_id)
        heavy = as_int(row[1], dash_zero=True)
        moderate = as_int(row[2], dash_zero=True)
        light = as_int(row[3], dash_zero=True)
        source_total = as_int(row[4], dash_zero=True)
        if heavy + moderate + light != source_total:
            raise RuntimeError(f"2023 housing row total mismatch for {canonical_name}")
        for indicator, value in (
            ("houses_heavily_damaged", heavy),
            ("houses_moderately_damaged", moderate),
            ("houses_lightly_damaged", light),
        ):
            housing_totals[indicator] += value
            observations.append(make_obs(2023, geography_id, indicator, value, "houses", "bpbd2023_housing", canonical_name))
    if housing_ids != expected_ids:
        raise RuntimeError("2023 housing district coverage mismatch")
    source_housing_total = housing[-1]
    expected_housing = {
        "houses_heavily_damaged": as_int(source_housing_total[1], dash_zero=True),
        "houses_moderately_damaged": as_int(source_housing_total[2], dash_zero=True),
        "houses_lightly_damaged": as_int(source_housing_total[3], dash_zero=True),
    }
    if dict(housing_totals) != expected_housing or sum(expected_housing.values()) != as_int(source_housing_total[4]):
        raise RuntimeError("2023 housing grand-total validation failed")

    loss_ids: set[str] = set()
    loss_numeric_sum = 0
    loss_numeric_count = 0
    for row in loss[1:-1]:
        geography_id, canonical_name = map_geography(row[0], aliases)
        if geography_id in loss_ids:
            raise RuntimeError(f"duplicate 2023 loss geography {geography_id}")
        loss_ids.add(geography_id)
        events = as_int(row[1])
        if social_events.get(geography_id) != events:
            raise RuntimeError(f"2023 event count disagrees between social/loss tables for {canonical_name}")
        raw_loss = row[3].strip() if len(row) > 3 else ""
        if raw_loss and raw_loss != "-":
            loss_value = as_int(raw_loss)
            loss_status = "reported_numeric"
            loss_numeric_sum += loss_value
            loss_numeric_count += 1
            observations.append(make_obs(2023, geography_id, "economic_loss_estimate_idr", loss_value, "IDR", "bpbd2023_loss", canonical_name))
        else:
            loss_value = ""
            loss_status = "source_dash" if raw_loss == "-" else "source_blank"
        loss_coverage.append({
            "year": 2023,
            "geography_id": geography_id,
            "canonical_name": canonical_name,
            "disaster_events_reported": events,
            "economic_loss_estimate_idr": loss_value,
            "loss_value_status": loss_status,
        })
    if loss_ids != expected_ids:
        raise RuntimeError("2023 loss district coverage mismatch")
    loss_total = loss[-1]
    if as_int(loss_total[1]) != social_totals["disaster_events_reported"]:
        raise RuntimeError("2023 loss event grand total disagrees with social table")
    if as_int(loss_total[3]) != loss_numeric_sum:
        raise RuntimeError(f"2023 economic loss total mismatch: calculated={loss_numeric_sum} source={loss_total[3]}")

    observations.sort(key=lambda row: (row["geography_id"], row["indicator_id"]))
    loss_coverage.sort(key=lambda row: row["geography_id"])
    write_csv(OBS_2023, list(observations[0].keys()), observations)
    write_csv(LOSS_COVERAGE_2023, list(loss_coverage[0].keys()), loss_coverage)

    provenance = [
        provenance_row("bpbd2023_social", "impact_continuity", by_role["impact_continuity"], social_path, "Dash markers in additive count cells are interpreted as explicit source zeros; totals validated."),
        provenance_row("bpbd2023_housing", "housing_continuity", by_role["housing_continuity"], housing_path, "Heavy/moderate/light damage counts and source row totals validated."),
        provenance_row("bpbd2023_loss", "economic_loss", by_role["economic_loss"], loss_path, "Only numeric Taksiran kerugian cells are materialized; source blanks/dashes remain missing and are documented in coverage table."),
    ]
    write_csv(PROV_2023, list(provenance[0].keys()), provenance)

    return {
        "observation_count": len(observations),
        "district_count": len(expected_ids),
        "social_totals": dict(social_totals),
        "housing_totals": dict(housing_totals),
        "economic_loss_numeric_district_count": loss_numeric_count,
        "economic_loss_missing_district_count": 19 - loss_numeric_count,
        "economic_loss_numeric_sum_idr": loss_numeric_sum,
    }


def make_obs(year: int, geography_id: str, indicator: str, value: int, unit: str, provenance_id: str, name: str) -> dict:
    return {
        "observation_id": f"bpbd-{year}-{geography_id}-{indicator}",
        "indicator_id": indicator,
        "geography_id": geography_id,
        "time_start": f"{year}-01-01",
        "time_end": f"{year}-12-31",
        "frequency": "annual",
        "value_numeric": value,
        "unit": unit,
        "claim_type": "observed_reported",
        "provenance_id": provenance_id,
        "suppressed": "false",
        "comparable": "true",
        "methodology_version": "bpbd-priority-context-v1",
        "notes": f"canonical_name={name}; missing values not inferred",
    }


def validated_2024_impact_totals() -> dict[str, int]:
    totals = defaultdict(int)
    with IMPACT_2024.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["suppressed"].strip().lower() == "true":
                continue
            totals[row["indicator_id"]] += as_int(row["value_numeric"])
    return dict(totals)


def canonical_2024_event_totals() -> dict[str, int]:
    totals = defaultdict(int)
    with EVENTS_2024.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if not row["indicator_id"].endswith("_events") or row["time_start"][:4] != "2024":
                continue
            if row["suppressed"].strip().lower() == "true" or not row["value_numeric"].strip():
                continue
            totals[row["indicator_id"]] += as_int(row["value_numeric"])
    return dict(totals)


def build_2024(by_role: dict[str, dict], aliases: dict[str, tuple[str, str]]) -> dict:
    casualty_path = role_sheet(by_role, "casualties_by_hazard")
    monthly_path = role_sheet(by_role, "monthly_events")
    siren_path = role_sheet(by_role, "mitigation_capacity")

    casualty = read_rows(casualty_path)
    monthly = read_rows(monthly_path)
    sirens = read_rows(siren_path)

    expected_casualty_header = ["Jenis Bencana", "Meninggal", "Hilang", "Luka/Sakit", "Menderita", "Mengungsi"]
    if casualty[0] != expected_casualty_header:
        raise RuntimeError(f"unexpected casualty-by-hazard header: {casualty[0]}")
    casualty_rows: list[dict] = []
    casualty_totals = defaultdict(int)
    for row in casualty[1:-1]:
        source_hazard = row[0]
        hazard_id = HAZARDS.get(source_hazard)
        if not hazard_id:
            raise RuntimeError(f"unmapped hazard label: {source_hazard!r}")
        for index, header in enumerate(expected_casualty_header[1:], start=1):
            indicator = CASUALTY_HEADERS[header]
            value = as_int(row[index], dash_zero=True)
            casualty_totals[indicator] += value
            casualty_rows.append({
                "year": 2024,
                "hazard_id": hazard_id,
                "source_hazard_label": source_hazard,
                "indicator_id": indicator,
                "value_numeric": value,
                "unit": "people",
            })
    source_total = casualty[-1]
    source_totals = {
        CASUALTY_HEADERS[header]: as_int(source_total[index], dash_zero=True)
        for index, header in enumerate(expected_casualty_header[1:], start=1)
    }
    if dict(casualty_totals) != source_totals:
        raise RuntimeError("2024 casualty-by-hazard source totals failed")
    validated = validated_2024_impact_totals()
    for indicator, value in source_totals.items():
        if validated.get(indicator) != value:
            raise RuntimeError(f"2024 hazard/district impact reconciliation failed for {indicator}: {value} != {validated.get(indicator)}")
    write_csv(CTX_CASUALTY_2024, list(casualty_rows[0].keys()), casualty_rows)

    expected_month_header = ["Nama Bencana", *MONTHS.keys(), "Total"]
    if monthly[0] != expected_month_header:
        raise RuntimeError(f"unexpected monthly-event header: {monthly[0]}")
    monthly_rows: list[dict] = []
    month_totals = defaultdict(int)
    hazard_totals: dict[str, int] = {}
    for row in monthly[1:-1]:
        source_hazard = row[0]
        hazard_id = HAZARDS.get(source_hazard)
        if not hazard_id:
            raise RuntimeError(f"unmapped monthly hazard label: {source_hazard!r}")
        row_sum = 0
        for index, (month_name, month_number) in enumerate(MONTHS.items(), start=1):
            raw = row[index]
            if raw == "":
                value = ""
                source_blank = "true"
            else:
                numeric = as_int(raw)
                value = numeric
                source_blank = "false"
                row_sum += numeric
                month_totals[month_number] += numeric
            monthly_rows.append({
                "year": 2024,
                "month": month_number,
                "month_name_source": month_name,
                "hazard_id": hazard_id,
                "source_hazard_label": source_hazard,
                "value_numeric": value,
                "unit": "events",
                "source_blank": source_blank,
            })
        source_row_total = as_int(row[-1])
        if row_sum != source_row_total:
            raise RuntimeError(f"monthly row total mismatch for {source_hazard}: {row_sum} != {source_row_total}")
        hazard_totals[hazard_id] = source_row_total

    grand = monthly[-1]
    grand_total = as_int(grand[-1])
    if sum(hazard_totals.values()) != grand_total:
        raise RuntimeError("monthly hazard grand total mismatch")
    for index, month_number in enumerate(MONTHS.values(), start=1):
        if month_totals[month_number] != as_int(grand[index]):
            raise RuntimeError(f"monthly column total mismatch for month={month_number}")
    canonical_events = canonical_2024_event_totals()
    if canonical_events.get("flood_events") is not None and hazard_totals["flood"] != canonical_events["flood_events"]:
        raise RuntimeError("flood total disagrees with BNPB canonical 2024")
    if canonical_events.get("landslide_events") is not None and hazard_totals["landslide"] != canonical_events["landslide_events"]:
        raise RuntimeError("landslide total disagrees with BNPB canonical 2024")
    write_csv(CTX_MONTHLY_2024, list(monthly_rows[0].keys()), monthly_rows)

    header_index = next((i for i, row in enumerate(sirens) if row and row[0] == "NO"), None)
    if header_index is None:
        raise RuntimeError("tsunami siren header row not found")
    siren_rows: list[dict] = []
    statuses = defaultdict(int)
    geography_counts = defaultdict(int)
    seen_numbers: set[int] = set()
    for row in sirens[header_index + 2:]:
        if not row or not row[0].isdigit():
            continue
        number = as_int(row[0])
        if number in seen_numbers:
            raise RuntimeError(f"duplicate siren number {number}")
        seen_numbers.add(number)
        geography_id, canonical_name = map_geography(row[3], aliases)
        latitude = float(row[6])
        longitude = float(row[7])
        if not (-3.5 <= latitude <= 1.5 and 97 <= longitude <= 102):
            raise RuntimeError(f"siren coordinate outside Sumbar envelope: {number} {latitude},{longitude}")
        source_status = row[8].strip() if len(row) > 8 else ""
        normalized_status = {"AKTIF": "active", "NON AKTIF": "inactive", "": "unknown"}.get(source_status)
        if normalized_status is None:
            raise RuntimeError(f"unknown siren status marker: {source_status!r}")
        statuses[normalized_status] += 1
        geography_counts[geography_id] += 1
        siren_rows.append({
            "siren_id": f"bpbd-sumbar-siren-{number:02d}",
            "source_number": number,
            "location_name": row[1],
            "address": row[2],
            "geography_id": geography_id,
            "canonical_name": canonical_name,
            "source_geography": row[3],
            "ownership": row[4],
            "installed_year": as_int(row[5]),
            "latitude": latitude,
            "longitude": longitude,
            "source_status": source_status,
            "normalized_status": normalized_status,
            "status_check_date": "2024-02-26",
        })
    if seen_numbers != set(range(1, 47)):
        raise RuntimeError(f"expected siren source numbers 1..46, got {sorted(seen_numbers)}")
    write_csv(CTX_SIRENS_2024, list(siren_rows[0].keys()), siren_rows)

    return {
        "casualty_by_hazard_rows": len(casualty_rows),
        "casualty_totals": dict(casualty_totals),
        "monthly_event_rows": len(monthly_rows),
        "monthly_event_total": grand_total,
        "monthly_hazard_totals": hazard_totals,
        "siren_count": len(siren_rows),
        "siren_status_counts": dict(statuses),
        "siren_geography_count": len(geography_counts),
    }


def main() -> None:
    source_manifest, by_role = load_manifest()
    aliases, ids = load_geography_aliases()
    result_2023 = build_2023(by_role, aliases, ids)
    result_2024 = build_2024(by_role, aliases)

    payload = {
        "schema": "ranah-observatory/bpbd-priority-context-materialization/v1",
        "source_manifest": SOURCE_MANIFEST.relative_to(ROOT).as_posix(),
        "source_manifest_sha256": sha256(SOURCE_MANIFEST),
        "missing_values_inferred": False,
        "zero_interpretation": "Dash markers are converted to zero only in additive count tables whose source totals validate that interpretation. Economic-loss blanks/dashes remain missing.",
        "result_2023": result_2023,
        "result_2024": result_2024,
        "outputs": {
            "observations_2023": {"path": OBS_2023.relative_to(ROOT).as_posix(), "sha256": sha256(OBS_2023)},
            "provenance_2023": {"path": PROV_2023.relative_to(ROOT).as_posix(), "sha256": sha256(PROV_2023)},
            "loss_coverage_2023": {"path": LOSS_COVERAGE_2023.relative_to(ROOT).as_posix(), "sha256": sha256(LOSS_COVERAGE_2023)},
            "casualties_by_hazard_2024": {"path": CTX_CASUALTY_2024.relative_to(ROOT).as_posix(), "sha256": sha256(CTX_CASUALTY_2024)},
            "monthly_events_2024": {"path": CTX_MONTHLY_2024.relative_to(ROOT).as_posix(), "sha256": sha256(CTX_MONTHLY_2024)},
            "tsunami_sirens_2024": {"path": CTX_SIRENS_2024.relative_to(ROOT).as_posix(), "sha256": sha256(CTX_SIRENS_2024)},
        },
    }
    MATERIALIZATION.parent.mkdir(parents=True, exist_ok=True)
    MATERIALIZATION.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"result_2023": result_2023, "result_2024": result_2024}, ensure_ascii=False))


if __name__ == "__main__":
    main()
