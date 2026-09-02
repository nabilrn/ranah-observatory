#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACQ = ROOT / "data/manifests/milestone61_irbi_sumbar_2015_2024_acquisition.json"
FINAL = ROOT / "data/manifests/milestone61_irbi_sumbar_2015_2024_final.json"
SOURCE = ROOT / "data/processed/bnpb/irbi_sumbar_2015_2024/irbi-sumbar-2015-2024-source-native.csv"
CANONICAL = ROOT / "data/processed/bnpb/irbi_sumbar_2015_2024/irbi-sumbar-2015-2024-canonical-long.csv"
CATALOG = ROOT / "catalog/public-datasets.csv"
YEARS = set(range(2015, 2025))
EXPECTED_2024 = {
    "idn.13.1307": (204.61, "tinggi"),
    "idn.13.1312": (192.85, "tinggi"),
    "idn.13.1301": (190.67, "tinggi"),
    "idn.13.1309": (177.65, "tinggi"),
    "idn.13.1371": (155.96, "tinggi"),
    "idn.13.1377": (153.04, "tinggi"),
    "idn.13.1306": (152.17, "tinggi"),
    "idn.13.1302": (149.22, "tinggi"),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate() -> dict:
    acq = json.loads(ACQ.read_text(encoding="utf-8"))
    final = json.loads(FINAL.read_text(encoding="utf-8"))

    assert acq["schema"] == "ranah-observatory/milestone61-irbi-sumbar-2015-2024-acquisition/v1"
    assert acq["source"]["publisher"] == "Badan Nasional Penanggulangan Bencana"
    assert acq["source"]["official_book_page"] == 67
    assert acq["source_native"]["row_count"] == 19
    assert acq["source_native"]["year_count"] == 10
    assert acq["source_native"]["value_count"] == 190
    assert sha256(SOURCE) == acq["output"]["sha256"]

    with SOURCE.open(newline="", encoding="utf-8") as handle:
        source_rows = list(csv.DictReader(handle))
    assert len(source_rows) == 19
    assert {int(row["NO"]) for row in source_rows} == set(range(1, 20))

    assert final["schema"] == "ranah-observatory/milestone61-irbi-sumbar-2015-2024-final/v2"
    result = final["result"]
    assert result["district_count"] == 19
    assert result["year_count"] == 10
    assert result["canonical_row_count"] == 190
    assert result["risk_class_counts_2024"] == {"tinggi": 8, "sedang": 11}
    assert result["geography_mapping_complete"] is True
    assert result["province_series_reconciled"] is True
    assert result["dashboard_risk_timeseries_ready"] is True
    assert result["dashboard_risk_map_2024_ready"] is True
    assert result["hazard_specific_risk_dimension_present"] is False
    assert result["prediction_claim_authorized"] is False
    assert result["missing_values_imputed"] is False
    assert final["province_reconciliation"]["all_years_match"] is True
    assert final["province_reconciliation"]["official_2024_score"] == 142.55
    assert final["province_reconciliation"]["official_2024_class"] == "sedang"
    assert sha256(CANONICAL) == final["output"]["sha256"]

    with CANONICAL.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 190
    assert {int(row["year"]) for row in rows} == YEARS
    assert len({row["geography_id"] for row in rows}) == 19
    assert all(sum(1 for row in rows if int(row["year"]) == year) == 19 for year in YEARS)
    assert all(row["claim_type"] == "official_index" for row in rows)
    assert all(row["unit"] == "index_points" for row in rows)
    assert all((row["risk_class"] == "") == (int(row["year"]) != 2024) for row in rows)

    rows_2024 = {row["geography_id"]: (float(row["irbi_score"]), row["risk_class"]) for row in rows if row["year"] == "2024"}
    for geography_id, expected in EXPECTED_2024.items():
        assert rows_2024[geography_id] == expected

    catalog = CATALOG.read_text(encoding="utf-8")
    assert "bnpb-irbi-sumbar-2015-2024" in catalog
    assert "irbi-sumbar-2015-2024-canonical-long.csv" in catalog

    return {
        "milestone": 61,
        "district_count": 19,
        "year_count": 10,
        "canonical_row_count": 190,
        "province_2024_score": 142.55,
        "high_risk_2024": 8,
        "medium_risk_2024": 11,
        "complete": True,
    }


def main() -> int:
    try:
        report = validate()
    except (AssertionError, OSError, ValueError, KeyError, csv.Error, json.JSONDecodeError) as exc:
        print(f"M61 validation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
