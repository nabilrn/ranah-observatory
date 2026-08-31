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
OUTPUT_DIR = ROOT / "web/static/data"
DISASTER_OUTPUT = OUTPUT_DIR / "disaster-summary.json"

NAME_RE = re.compile(r"source_geography=\d+:([^;]+)")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clean_name(notes: str, fallback: str) -> str:
    match = NAME_RE.search(notes or "")
    if not match:
        return fallback
    value = match.group(1).strip().title()
    return value.replace("Kota ", "Kota ").replace("Kabupaten ", "Kabupaten ")


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


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = build_disaster_summary()
    DISASTER_OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": DISASTER_OUTPUT.relative_to(ROOT).as_posix(),
        "years": payload["years"],
        "indicators": payload["indicators"],
        "district_rows": len(payload["district_rows"]),
        "source_rows": payload["source"]["row_count_used"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
