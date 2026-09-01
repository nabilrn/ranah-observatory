#!/usr/bin/env python3
"""Promote validated BPBD context into the static public disaster contract v3.

The existing public-data builder remains the stable base for BNPB events, BPBD
2024 district impacts, BIG boundaries, and the catalog. This step only upgrades
that validated v2 artifact with already-materialized 2023 BPBD impact/loss data
and 2024 BPBD hazard/monthly/siren context.

No source-native workbook is read here. Missing loss values stay missing, blank
monthly cells stay null, and divergent BNPB/BPBD event series stay separate.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SUMMARY = ROOT / "web/static/data/disaster-summary.json"
CONTEXT_MANIFEST = ROOT / "data/processed/bpbd/disaster_context_2024/materialization.json"

EXPECTED_SCHEMA = "ranah-observatory/bpbd-priority-context-materialization/v1"
BASE_PUBLIC_SCHEMA = "ranah-observatory/public-disaster-summary/v2"
PUBLIC_SCHEMA = "ranah-observatory/public-disaster-summary/v3"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def number(value: str):
    parsed = float(value)
    return int(parsed) if parsed.is_integer() else parsed


def verified_output(manifest: dict, key: str) -> Path:
    output = manifest["outputs"][key]
    path = ROOT / output["path"]
    if not path.exists():
        raise RuntimeError(f"validated context output missing: {output['path']}")
    actual = sha256(path)
    if actual != output["sha256"]:
        raise RuntimeError(
            f"validated context checksum mismatch for {key}: manifest={output['sha256']} actual={actual}"
        )
    return path


def build_impact_2023(manifest: dict) -> dict:
    observations_path = verified_output(manifest, "observations_2023")
    coverage_path = verified_output(manifest, "loss_coverage_2023")
    observations = read_csv(observations_path)
    coverage_rows = read_csv(coverage_path)
    expected = manifest["result_2023"]

    if len(observations) != expected["observation_count"]:
        raise RuntimeError("2023 public promotion row count does not match materialization")
    if len(coverage_rows) != expected["district_count"]:
        raise RuntimeError("2023 loss coverage does not contain the expected 19 districts")

    coverage_ids: set[str] = set()
    names: dict[str, str] = {}
    public_coverage: list[dict] = []
    numeric_loss_total = 0
    numeric_loss_count = 0
    missing_loss_count = 0
    allowed_status = {"reported_numeric", "source_blank", "source_dash"}

    for row in coverage_rows:
        geography_id = row["geography_id"].strip()
        if not geography_id or geography_id in coverage_ids:
            raise RuntimeError(f"invalid or duplicate 2023 loss coverage geography: {geography_id!r}")
        coverage_ids.add(geography_id)
        names[geography_id] = row["canonical_name"].strip()
        status = row["loss_value_status"].strip()
        if status not in allowed_status:
            raise RuntimeError(f"unknown 2023 loss coverage status: {status}")
        raw_loss = row["economic_loss_estimate_idr"].strip()
        if status == "reported_numeric":
            if raw_loss == "":
                raise RuntimeError(f"reported numeric loss is blank for {geography_id}")
            loss_value = int(raw_loss)
            numeric_loss_total += loss_value
            numeric_loss_count += 1
        else:
            if raw_loss != "":
                raise RuntimeError(f"missing-source loss unexpectedly contains a value for {geography_id}")
            loss_value = None
            missing_loss_count += 1
        public_coverage.append(
            {
                "year": 2023,
                "geography_id": geography_id,
                "name": names[geography_id],
                "disaster_events_reported": int(row["disaster_events_reported"]),
                "economic_loss_estimate_idr": loss_value,
                "loss_value_status": status,
            }
        )

    if numeric_loss_count != expected["economic_loss_numeric_district_count"]:
        raise RuntimeError("2023 numeric loss coverage count does not match materialization")
    if missing_loss_count != expected["economic_loss_missing_district_count"]:
        raise RuntimeError("2023 missing loss coverage count does not match materialization")
    if numeric_loss_total != expected["economic_loss_numeric_sum_idr"]:
        raise RuntimeError("2023 reported economic-loss sum does not match materialization")

    grouped: dict[str, dict] = {}
    units: dict[str, str] = {}
    totals: dict[str, float] = defaultdict(float)
    indicators: set[str] = set()

    required = {
        "indicator_id", "geography_id", "time_start", "value_numeric", "unit",
        "claim_type", "suppressed", "comparable", "provenance_id",
    }
    if observations:
        missing = required - set(observations[0])
        if missing:
            raise RuntimeError(f"2023 canonical impact output missing columns: {sorted(missing)}")

    for record in observations:
        if record["suppressed"].strip().lower() == "true":
            continue
        if record["time_start"][:4] != "2023":
            raise RuntimeError("2023 impact output contains an observation outside 2023")
        geography_id = record["geography_id"].strip()
        if geography_id not in coverage_ids:
            raise RuntimeError(f"2023 impact observation has geography outside loss coverage: {geography_id}")
        indicator = record["indicator_id"].strip()
        raw_value = record["value_numeric"].strip()
        if raw_value == "":
            raise RuntimeError("validated 2023 impact observation unexpectedly has a blank value")
        value = float(raw_value)
        unit = record["unit"].strip()
        if units.setdefault(indicator, unit) != unit:
            raise RuntimeError(f"2023 indicator unit changed within output: {indicator}")
        row = grouped.setdefault(
            geography_id,
            {"year": 2023, "geography_id": geography_id, "name": names[geography_id], "values": {}},
        )
        if indicator in row["values"]:
            raise RuntimeError(f"duplicate 2023 public observation: {geography_id}/{indicator}")
        row["values"][indicator] = number(raw_value)
        totals[indicator] += value
        indicators.add(indicator)

    if set(grouped) != coverage_ids:
        raise RuntimeError("2023 impact/loss district coverage differs during public promotion")

    expected_totals = {
        **expected["social_totals"],
        **expected["housing_totals"],
        "economic_loss_estimate_idr": expected["economic_loss_numeric_sum_idr"],
    }
    for indicator, expected_value in expected_totals.items():
        actual = totals.get(indicator)
        if actual is None or actual != expected_value:
            raise RuntimeError(
                f"2023 public total mismatch for {indicator}: materialization={expected_value} public={actual}"
            )

    public_coverage.sort(key=lambda item: item["geography_id"])
    district_rows = sorted(grouped.values(), key=lambda item: item["geography_id"])
    annual_totals = [
        {"year": 2023, "indicator_id": indicator, "value": number(str(value)), "unit": units[indicator]}
        for indicator, value in sorted(totals.items())
    ]

    return {
        "source": {
            "organization": "BPBD Provinsi Sumatera Barat / Pusdalops",
            "path": observations_path.relative_to(ROOT).as_posix(),
            "sha256": sha256(observations_path),
            "row_count_used": len(observations),
            "materialization_path": CONTEXT_MANIFEST.relative_to(ROOT).as_posix(),
        },
        "years": [2023],
        "indicators": sorted(indicators),
        "indicator_units": dict(sorted(units.items())),
        "annual_totals": annual_totals,
        "district_rows": district_rows,
        "loss_coverage": public_coverage,
        "economic_loss": {
            "reported_total_idr": numeric_loss_total,
            "numeric_district_count": numeric_loss_count,
            "missing_district_count": missing_loss_count,
            "district_count": len(public_coverage),
            "coverage_complete": missing_loss_count == 0,
        },
        "interpretation": {
            "id": "Kerugian ekonomi 2023 adalah jumlah nilai numerik yang dilaporkan sumber pada 12 dari 19 kabupaten/kota. Tujuh wilayah dengan sel kosong atau tanda '-' tetap ditampilkan sebagai data tidak tersedia, bukan nol.",
            "en": "The 2023 economic-loss figure sums numeric values reported by the source for 12 of 19 regencies/cities. Seven regions with blank or '-' source cells remain unavailable rather than being converted to zero.",
        },
    }


def build_context_2024(manifest: dict) -> dict:
    casualty_path = verified_output(manifest, "casualties_by_hazard_2024")
    monthly_path = verified_output(manifest, "monthly_events_2024")
    siren_path = verified_output(manifest, "tsunami_sirens_2024")
    expected = manifest["result_2024"]

    casualty_rows = read_csv(casualty_path)
    monthly_rows = read_csv(monthly_path)
    siren_rows = read_csv(siren_path)
    if len(casualty_rows) != expected["casualty_by_hazard_rows"]:
        raise RuntimeError("2024 casualty-by-hazard row count mismatch")
    if len(monthly_rows) != expected["monthly_event_rows"]:
        raise RuntimeError("2024 monthly-event row count mismatch")
    if len(siren_rows) != expected["siren_count"]:
        raise RuntimeError("2024 tsunami-siren row count mismatch")

    public_casualties = [
        {
            "year": int(row["year"]),
            "hazard_id": row["hazard_id"],
            "source_hazard_label": row["source_hazard_label"],
            "indicator_id": row["indicator_id"],
            "value": int(row["value_numeric"]),
            "unit": row["unit"],
        }
        for row in casualty_rows
    ]

    public_monthly = []
    for row in monthly_rows:
        raw_value = row["value_numeric"].strip()
        source_blank = row["source_blank"].strip().lower() == "true"
        if source_blank != (raw_value == ""):
            raise RuntimeError("2024 monthly source_blank flag disagrees with value presence")
        public_monthly.append(
            {
                "year": int(row["year"]),
                "month": int(row["month"]),
                "month_name_source": row["month_name_source"],
                "hazard_id": row["hazard_id"],
                "source_hazard_label": row["source_hazard_label"],
                "value": None if raw_value == "" else int(raw_value),
                "unit": row["unit"],
                "source_blank": source_blank,
            }
        )

    public_sirens = []
    status_counts: dict[str, int] = defaultdict(int)
    geographies: set[str] = set()
    for row in siren_rows:
        status = row["normalized_status"]
        if status not in {"active", "inactive", "unknown"}:
            raise RuntimeError(f"unexpected normalized siren status: {status}")
        status_counts[status] += 1
        geographies.add(row["geography_id"])
        public_sirens.append(
            {
                "siren_id": row["siren_id"],
                "source_number": int(row["source_number"]),
                "location_name": row["location_name"],
                "address": row["address"],
                "geography_id": row["geography_id"],
                "name": row["canonical_name"],
                "ownership": row["ownership"],
                "installed_year": int(row["installed_year"]),
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
                "source_status": row["source_status"],
                "status": status,
                "status_check_date": row["status_check_date"],
            }
        )

    if dict(status_counts) != expected["siren_status_counts"]:
        raise RuntimeError("2024 siren status counts do not match materialization")
    if len(geographies) != expected["siren_geography_count"]:
        raise RuntimeError("2024 siren geography count does not match materialization")

    return {
        "source": {
            "organization": "BPBD Provinsi Sumatera Barat / Pusdalops",
            "materialization_path": CONTEXT_MANIFEST.relative_to(ROOT).as_posix(),
            "materialization_sha256": sha256(CONTEXT_MANIFEST),
            "cross_source_policy": manifest["cross_source_policy"],
        },
        "monthly_events": {
            "path": monthly_path.relative_to(ROOT).as_posix(),
            "sha256": sha256(monthly_path),
            "rows": public_monthly,
            "annual_total": expected["monthly_event_total"],
            "hazard_totals": expected["monthly_hazard_totals"],
            "event_source_comparison": expected["event_source_comparison"],
            "interpretation": {
                "id": "Seri bulanan BPBD/Pusdalops dipertahankan sebagai seri resmi yang terpisah dari BNPB. Untuk banjir dan longsor, total kedua sistem berbeda dan tidak dijumlahkan atau saling menimpa.",
                "en": "The BPBD/Pusdalops monthly series is retained as an official series separate from BNPB. Flood and landslide totals differ across the two systems and are neither added together nor overwritten.",
            },
        },
        "casualties_by_hazard": {
            "path": casualty_path.relative_to(ROOT).as_posix(),
            "sha256": sha256(casualty_path),
            "rows": public_casualties,
            "totals": expected["casualty_totals"],
        },
        "tsunami_sirens": {
            "path": siren_path.relative_to(ROOT).as_posix(),
            "sha256": sha256(siren_path),
            "rows": public_sirens,
            "count": expected["siren_count"],
            "status_counts": expected["siren_status_counts"],
            "geography_count": expected["siren_geography_count"],
            "interpretation": {
                "id": "Daftar sirine adalah inventaris kapasitas mitigasi, bukan skor kesiapsiagaan tsunami. Status kosong pada sumber dipertahankan sebagai tidak diketahui.",
                "en": "The siren list is a mitigation-capacity inventory, not a tsunami-readiness score. Blank source statuses remain unknown.",
            },
        },
    }


def main() -> None:
    if not PUBLIC_SUMMARY.exists():
        raise RuntimeError("base public disaster summary is missing; run build_public_web_data.py first")
    base = json.loads(PUBLIC_SUMMARY.read_text(encoding="utf-8"))
    if base.get("schema") != BASE_PUBLIC_SCHEMA:
        raise RuntimeError(f"expected base public schema {BASE_PUBLIC_SCHEMA}, got {base.get('schema')!r}")

    manifest = json.loads(CONTEXT_MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("schema") != EXPECTED_SCHEMA:
        raise RuntimeError(f"unsupported context materialization schema: {manifest.get('schema')!r}")
    if manifest.get("missing_values_inferred") is not False:
        raise RuntimeError("context materialization inferred missing values")

    impact_2023 = build_impact_2023(manifest)
    context_2024 = build_context_2024(manifest)

    event_ids = {row["geography_id"] for row in base["events"]["district_rows"]}
    impact_2024_ids = {row["geography_id"] for row in base["impact"]["district_rows"]}
    impact_2023_ids = {row["geography_id"] for row in impact_2023["district_rows"]}
    if event_ids != impact_2024_ids or event_ids != impact_2023_ids:
        raise RuntimeError("public event/2024-impact/2023-impact district coverage is not identical")

    payload = {
        "schema": PUBLIC_SCHEMA,
        "events": base["events"],
        "impact_2024": base["impact"],
        "impact_2023": impact_2023,
        "context_2024": context_2024,
        "geography": base["geography"],
        "impact_values_included": True,
        "economic_loss_2023_included": True,
        "economic_loss_2024_included": False,
        "missing_values_inferred": False,
    }
    PUBLIC_SUMMARY.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": PUBLIC_SCHEMA,
                "impact_2023_observations": impact_2023["source"]["row_count_used"],
                "loss_2023_reported_total_idr": impact_2023["economic_loss"]["reported_total_idr"],
                "loss_2023_numeric_districts": impact_2023["economic_loss"]["numeric_district_count"],
                "monthly_events_2024": context_2024["monthly_events"]["annual_total"],
                "siren_count": context_2024["tsunami_sirens"]["count"],
                "event_source_comparison": context_2024["monthly_events"]["event_source_comparison"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
