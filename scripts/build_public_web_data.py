#!/usr/bin/env python3
"""Build small public web artifacts from validated/canonical repository data.

This is a delivery transform only. It does not infer missing values, fit models,
merge impact concepts, or read raw acquisition files. The web application should
consume these outputs instead of reaching into research/analysis directories.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DISASTER_SOURCE = ROOT / "data/processed/bnpb/disaster/bnpb-disaster-canonical-observations.csv"
PUBLIC_CATALOG_SOURCE = ROOT / "catalog/public-datasets.csv"
OUTPUT_DIR = ROOT / "web/static/data"
DISASTER_OUTPUT = OUTPUT_DIR / "disaster-summary.json"
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


def build_disaster_summary() -> dict:
    required = {
        "indicator_id", "geography_id", "time_start", "value_numeric", "unit",
        "claim_type", "suppressed", "notes"
    }
    totals: dict[tuple[int, str], float] = defaultdict(float)
    rows: dict[tuple[int, str], dict] = {}
    indicators: set[str] = set()
    years: set[int] = set()
    source_rows = 0

    with DISASTER_SOURCE.open(newline="", encoding="utf-8") as handle:
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

    def json_number(value: float):
        return int(value) if value.is_integer() else value

    public_rows = []
    for item in sorted(rows.values(), key=lambda r: (r["year"], r["name"], r["geography_id"])):
        public_rows.append(
            {
                **{k: item[k] for k in ("year", "geography_id", "name")},
                "values": {k: json_number(v) for k, v in sorted(item["values"].items())},
            }
        )

    annual_totals = [
        {"year": year, "indicator_id": indicator, "value": json_number(value), "unit": "count"}
        for (year, indicator), value in sorted(totals.items())
    ]

    return {
        "schema": "ranah-observatory/public-disaster-summary/v1",
        "source": {
            "organization": "BNPB",
            "path": DISASTER_SOURCE.relative_to(ROOT).as_posix(),
            "sha256": sha256(DISASTER_SOURCE),
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
        "impact_values_included": False,
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


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    disaster = build_disaster_summary()
    catalog = build_catalog()
    write_json(DISASTER_OUTPUT, disaster)
    write_json(CATALOG_OUTPUT, catalog)
    print(json.dumps({
        "disaster": {
            "output": DISASTER_OUTPUT.relative_to(ROOT).as_posix(),
            "years": disaster["years"],
            "indicators": disaster["indicators"],
            "district_rows": len(disaster["district_rows"]),
            "source_rows": disaster["source"]["row_count_used"],
        },
        "catalog": {
            "output": CATALOG_OUTPUT.relative_to(ROOT).as_posix(),
            **catalog["summary"],
        },
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
