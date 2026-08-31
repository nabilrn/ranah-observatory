#!/usr/bin/env python3
"""Build small public web artifacts from validated/canonical repository data.

This is a delivery transform only. It does not infer missing values, fit models,
merge semantically different impact concepts, or read raw acquisition files. The
web application consumes these outputs instead of reaching into research folders.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVENT_SOURCE = ROOT / "data/processed/bnpb/disaster/bnpb-disaster-canonical-observations.csv"
IMPACT_SOURCE = ROOT / "data/processed/bpbd/disaster_impact_2024/bpbd-disaster-impact-canonical-observations.csv"
IMPACT_MANIFEST = ROOT / "data/processed/bpbd/disaster_impact_2024/materialization.json"
BOUNDARY_SOURCE = ROOT / "data/processed/geography/sumbar-big-kabkota.geojson"
BOUNDARY_MANIFEST = ROOT / "data/manifests/sumbar_big_kabkota_boundary.json"
BPS_GEOGRAPHY_MAP = ROOT / "data/registries/bps_panel_geography_map.csv"
PUBLIC_CATALOG_SOURCE = ROOT / "catalog/public-datasets.csv"
OUTPUT_DIR = ROOT / "web/static/data"
DISASTER_OUTPUT = OUTPUT_DIR / "disaster-summary.json"
BOUNDARY_OUTPUT = OUTPUT_DIR / "sumbar-kabkota.geojson"
CATALOG_OUTPUT = OUTPUT_DIR / "catalog.json"

NAME_RE = re.compile(r"source_geography=\d+:([^;]+)")
CATALOG_REQUIRED = {
    "id", "category", "title_id", "title_en", "description_id", "description_en",
    "source", "period", "geography", "formats", "status", "source_path",
}
CATALOG_STATUSES = {"materialized", "building"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clean_name(notes: str, fallback: str) -> str:
    match = NAME_RE.search(notes or "")
    if not match:
        return fallback
    return match.group(1).strip().title()


def json_number(value: float):
    return int(value) if value.is_integer() else value


def build_event_summary() -> dict:
    required = {
        "indicator_id", "geography_id", "time_start", "value_numeric", "unit",
        "claim_type", "suppressed", "notes"
    }
    totals: dict[tuple[int, str], float] = defaultdict(float)
    rows: dict[tuple[int, str], dict] = {}
    indicators: set[str] = set()
    years: set[int] = set()
    source_rows = 0

    with EVENT_SOURCE.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise RuntimeError(f"disaster canonical source missing columns: {sorted(missing)}")

        for record in reader:
            if str(record.get("suppressed", "")).strip().lower() == "true":
                continue
            indicator = str(record["indicator_id"]).strip()
            if not indicator.endswith("_events"):
                continue
            if str(record["unit"]).strip() != "count":
                continue
            value_text = str(record["value_numeric"]).strip()
            if value_text == "":
                continue

            year = int(str(record["time_start"])[:4])
            value = float(value_text)
            geography_id = str(record["geography_id"]).strip()
            key = (year, geography_id)
            row = rows.setdefault(
                key,
                {
                    "year": year,
                    "geography_id": geography_id,
                    "name": clean_name(str(record.get("notes", "")), geography_id),
                    "values": {},
                },
            )
            if indicator in row["values"]:
                raise RuntimeError(f"duplicate public event observation for {key} {indicator}")
            row["values"][indicator] = value
            totals[(year, indicator)] += value
            indicators.add(indicator)
            years.add(year)
            source_rows += 1

    public_rows = [
        {
            **{key: item[key] for key in ("year", "geography_id", "name")},
            "values": {key: json_number(value) for key, value in sorted(item["values"].items())},
        }
        for item in sorted(rows.values(), key=lambda row: (row["year"], row["name"], row["geography_id"]))
    ]
    annual_totals = [
        {"year": year, "indicator_id": indicator, "value": json_number(value), "unit": "count"}
        for (year, indicator), value in sorted(totals.items())
    ]

    if not public_rows:
        raise RuntimeError("no public disaster event rows materialized")

    return {
        "source": {
            "organization": "BNPB",
            "path": EVENT_SOURCE.relative_to(ROOT).as_posix(),
            "sha256": sha256(EVENT_SOURCE),
            "row_count_used": source_rows,
        },
        "years": sorted(years),
        "indicators": sorted(indicators),
        "annual_totals": annual_totals,
        "district_rows": public_rows,
        "interpretation": {
            "id": "Jumlah kejadian tercatat. Seri dapat dipengaruhi intensitas pelaporan dan praktik klasifikasi.",
            "en": "Recorded event counts. The series may be affected by reporting intensity and classification practice.",
        },
    }


def build_impact_summary() -> dict:
    required = {
        "indicator_id", "geography_id", "time_start", "value_numeric", "unit",
        "claim_type", "suppressed", "provenance_id"
    }
    totals: dict[tuple[int, str], float] = defaultdict(float)
    rows: dict[tuple[int, str], dict] = {}
    indicators: set[str] = set()
    indicator_units: dict[str, str] = {}
    years: set[int] = set()
    source_rows = 0

    materialization = json.loads(IMPACT_MANIFEST.read_text(encoding="utf-8"))
    if materialization.get("schema") != "ranah-observatory/bpbd-disaster-impact-materialization/v1":
        raise RuntimeError("unsupported BPBD impact materialization manifest")
    if materialization.get("missing_values_inferred") is not False:
        raise RuntimeError("BPBD impact materialization inferred missing values")
    expected_sha = materialization["outputs"]["observations"]["sha256"]
    actual_sha = sha256(IMPACT_SOURCE)
    if expected_sha != actual_sha:
        raise RuntimeError("BPBD impact canonical observation checksum does not match materialization manifest")

    with IMPACT_SOURCE.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise RuntimeError(f"impact canonical source missing columns: {sorted(missing)}")

        for record in reader:
            if str(record.get("suppressed", "")).strip().lower() == "true":
                continue
            value_text = str(record["value_numeric"]).strip()
            if value_text == "":
                raise RuntimeError("validated BPBD impact observation unexpectedly has a blank value")
            year = int(str(record["time_start"])[:4])
            indicator = str(record["indicator_id"]).strip()
            geography_id = str(record["geography_id"]).strip()
            unit = str(record["unit"]).strip()
            value = float(value_text)

            previous_unit = indicator_units.setdefault(indicator, unit)
            if previous_unit != unit:
                raise RuntimeError(f"impact indicator unit changed inside canonical file: {indicator}")

            key = (year, geography_id)
            row = rows.setdefault(key, {"year": year, "geography_id": geography_id, "values": {}})
            if indicator in row["values"]:
                raise RuntimeError(f"duplicate public impact observation for {key} {indicator}")
            row["values"][indicator] = value
            totals[(year, indicator)] += value
            indicators.add(indicator)
            years.add(year)
            source_rows += 1

    expected_count = materialization.get("observation_count")
    if expected_count != source_rows:
        raise RuntimeError(f"BPBD impact row count mismatch: manifest={expected_count} public={source_rows}")

    public_rows = [
        {
            "year": item["year"],
            "geography_id": item["geography_id"],
            "values": {key: json_number(value) for key, value in sorted(item["values"].items())},
        }
        for item in sorted(rows.values(), key=lambda row: (row["year"], row["geography_id"]))
    ]
    annual_totals = [
        {
            "year": year,
            "indicator_id": indicator,
            "value": json_number(value),
            "unit": indicator_units[indicator],
        }
        for (year, indicator), value in sorted(totals.items())
    ]

    return {
        "source": {
            "organization": "BPBD Provinsi Sumatera Barat / Pusdalops",
            "path": IMPACT_SOURCE.relative_to(ROOT).as_posix(),
            "sha256": actual_sha,
            "row_count_used": source_rows,
            "materialization_path": IMPACT_MANIFEST.relative_to(ROOT).as_posix(),
        },
        "years": sorted(years),
        "indicators": sorted(indicators),
        "indicator_units": dict(sorted(indicator_units.items())),
        "annual_totals": annual_totals,
        "district_rows": public_rows,
        "interpretation": {
            "id": "Kolom dampak dipertahankan sesuai definisi sumber BPBD. Menderita tidak digabung dengan mengungsi, rumah terendam tidak digabung dengan rumah rusak, dan kerugian ekonomi 2024 belum tersedia pada batch tervalidasi ini.",
            "en": "Impact columns retain the BPBD source definitions. Suffering is not combined with displacement, flooded houses are not combined with damaged houses, and 2024 economic losses are not available in this validated batch.",
        },
    }


def load_current_bps_geographies() -> dict[str, str]:
    mapping: dict[str, str] = {}
    with BPS_GEOGRAPHY_MAP.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            code = str(row["bps_vervar_id"]).strip()
            if len(code) != 4 or row["mapping_type"] != "direct_current_code":
                continue
            mapping[code] = str(row["canonical_geography_id"]).strip()
    if len(mapping) != 19:
        raise RuntimeError(f"public geography crosswalk expected 19 districts, found {len(mapping)}")
    return mapping


def build_public_boundary(event_summary: dict) -> dict:
    source_geojson = json.loads(BOUNDARY_SOURCE.read_text(encoding="utf-8"))
    boundary_manifest = json.loads(BOUNDARY_MANIFEST.read_text(encoding="utf-8"))
    if boundary_manifest.get("feature_count") != 19:
        raise RuntimeError("BIG boundary manifest does not contain 19 promoted districts")
    if boundary_manifest.get("output_sha256") != sha256(BOUNDARY_SOURCE):
        raise RuntimeError("BIG boundary checksum does not match acquisition manifest")

    code_map = load_current_bps_geographies()
    latest_year = max(event_summary["years"])
    event_names = {
        row["geography_id"]: row["name"]
        for row in event_summary["district_rows"]
        if row["year"] == latest_year
    }

    features: list[dict] = []
    seen_ids: set[str] = set()
    for feature in source_geojson.get("features", []):
        properties = feature.get("properties") or {}
        bps_code = str(properties.get("kdbbps") or "").strip()
        geography_id = code_map.get(bps_code)
        if not geography_id:
            raise RuntimeError(f"BIG public boundary has unmapped KDBBPS code: {bps_code!r}")
        if geography_id in seen_ids:
            raise RuntimeError(f"duplicate promoted public boundary geography: {geography_id}")
        seen_ids.add(geography_id)
        features.append(
            {
                "type": "Feature",
                "geometry": feature.get("geometry"),
                "properties": {
                    "geography_id": geography_id,
                    "name": event_names.get(geography_id, str(properties.get("name") or geography_id)),
                    "source_name": properties.get("name"),
                    "bps_code": bps_code,
                    "province": "Sumatera Barat",
                    "source_feature_count": properties.get("source_feature_count", 1),
                },
            }
        )

    if len(features) != 19 or seen_ids != set(code_map.values()):
        raise RuntimeError(
            f"public boundary coverage mismatch: features={len(features)} ids={len(seen_ids)} expected={len(code_map)}"
        )

    output = {
        "type": "FeatureCollection",
        "name": "Sumatera Barat Kabupaten/Kota — Ranah Observatory public boundary",
        "features": sorted(features, key=lambda item: item["properties"]["geography_id"]),
    }
    write_json(BOUNDARY_OUTPUT, output, compact=True)
    return {
        "organization": "Badan Informasi Geospasial",
        "path": BOUNDARY_SOURCE.relative_to(ROOT).as_posix(),
        "sha256": sha256(BOUNDARY_SOURCE),
        "feature_count": len(features),
        "public_path": f"data/{BOUNDARY_OUTPUT.name}",
        "anomaly_note": (
            f"{boundary_manifest.get('excluded_unnamed_feature_count', 0)} unnamed source polygons are documented in the acquisition manifest and excluded before public promotion."
        ),
    }


def build_disaster_summary() -> dict:
    events = build_event_summary()
    impact = build_impact_summary()
    geography = build_public_boundary(events)
    event_ids = {row["geography_id"] for row in events["district_rows"]}
    impact_ids = {row["geography_id"] for row in impact["district_rows"]}
    if event_ids != impact_ids:
        raise RuntimeError(
            f"event/impact district coverage differs: only_events={sorted(event_ids-impact_ids)} only_impact={sorted(impact_ids-event_ids)}"
        )
    return {
        "schema": "ranah-observatory/public-disaster-summary/v2",
        "events": events,
        "impact": impact,
        "geography": geography,
        "impact_values_included": True,
        "economic_loss_2024_included": False,
        "missing_values_inferred": False,
    }


def build_catalog() -> dict:
    datasets: list[dict] = []
    seen_ids: set[str] = set()

    with PUBLIC_CATALOG_SOURCE.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = CATALOG_REQUIRED - set(reader.fieldnames or [])
        if missing:
            raise RuntimeError(f"public catalog registry missing columns: {sorted(missing)}")

        for line_number, row in enumerate(reader, start=2):
            dataset_id = str(row["id"]).strip()
            if not dataset_id:
                raise RuntimeError(f"public catalog row {line_number} has no id")
            if dataset_id in seen_ids:
                raise RuntimeError(f"duplicate public catalog id: {dataset_id}")
            seen_ids.add(dataset_id)

            status = str(row["status"]).strip()
            if status not in CATALOG_STATUSES:
                raise RuntimeError(f"invalid public catalog status for {dataset_id}: {status}")

            source_path = str(row["source_path"]).strip()
            source_artifact = ROOT / source_path
            if not source_artifact.exists():
                raise RuntimeError(f"public catalog source path does not exist for {dataset_id}: {source_path}")

            datasets.append(
                {
                    "id": dataset_id,
                    "category": str(row["category"]).strip(),
                    "title": {"id": str(row["title_id"]).strip(), "en": str(row["title_en"]).strip()},
                    "description": {
                        "id": str(row["description_id"]).strip(),
                        "en": str(row["description_en"]).strip(),
                    },
                    "source": str(row["source"]).strip(),
                    "period": str(row["period"]).strip(),
                    "geography": str(row["geography"]).strip(),
                    "formats": [value.strip() for value in str(row["formats"]).split(";") if value.strip()],
                    "status": status,
                    "source_path": source_path,
                    "source_path_type": "directory" if source_artifact.is_dir() else "file",
                }
            )

    datasets.sort(key=lambda item: (item["category"].casefold(), item["title"]["id"].casefold(), item["id"]))
    categories = sorted({item["category"] for item in datasets})
    return {
        "schema": "ranah-observatory/public-data-catalog/v1",
        "source": {
            "path": PUBLIC_CATALOG_SOURCE.relative_to(ROOT).as_posix(),
            "sha256": sha256(PUBLIC_CATALOG_SOURCE),
        },
        "summary": {
            "dataset_count": len(datasets),
            "materialized_count": sum(item["status"] == "materialized" for item in datasets),
            "building_count": sum(item["status"] == "building" for item in datasets),
            "category_count": len(categories),
        },
        "categories": categories,
        "datasets": datasets,
    }


def write_json(path: Path, payload: dict, compact: bool = False) -> None:
    if compact:
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    else:
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    disaster = build_disaster_summary()
    catalog = build_catalog()
    write_json(DISASTER_OUTPUT, disaster)
    write_json(CATALOG_OUTPUT, catalog)
    print(json.dumps({
        "disaster": {
            "output": DISASTER_OUTPUT.relative_to(ROOT).as_posix(),
            "event_years": disaster["events"]["years"],
            "event_indicators": disaster["events"]["indicators"],
            "event_district_rows": len(disaster["events"]["district_rows"]),
            "impact_years": disaster["impact"]["years"],
            "impact_indicators": len(disaster["impact"]["indicators"]),
            "impact_district_rows": len(disaster["impact"]["district_rows"]),
            "boundary_features": disaster["geography"]["feature_count"],
        },
        "catalog": {
            "output": CATALOG_OUTPUT.relative_to(ROOT).as_posix(),
            **catalog["summary"],
        },
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
