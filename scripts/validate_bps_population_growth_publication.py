#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data" / "registries" / "bps_population_growth_2010_2020_publication.csv"
DEFAULT_GEOGRAPHIES = ROOT / "data" / "registries" / "geographies.csv"

EXPECTED_CODES = {
    "1301", "1302", "1303", "1304", "1305", "1306", "1307", "1308", "1309",
    "1310", "1311", "1312", "1371", "1372", "1373", "1374", "1375", "1376", "1377",
}
EXPECTED_PUBLICATION_ID = "438e46e73d9a64df8d8c34f2"
EXPECTED_PUBLICATION_NUMBER = "13000.2106"
EXPECTED_TABLE = "3.1.1"
EXPECTED_SP2010_TOTAL = 4_846_909
EXPECTED_SP2020_TOTAL = 5_534_472
INTERVAL_MONTHS = 124
INTERVAL_YEARS = INTERVAL_MONTHS / 12.0


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def current_geographies(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    selected = {
        row["bps_code"]: row
        for row in rows
        if row.get("parent_geography_id") == "idn.13"
        and row.get("status") == "current"
        and row.get("geography_level") in {"regency", "city"}
    }
    if set(selected) != EXPECTED_CODES:
        raise ValueError(f"current Sumbar geography code footprint drifted: {sorted(selected)}")
    return selected


def geometric_growth_pct(population_start: int, population_end: int) -> float:
    if population_start <= 0 or population_end <= 0:
        raise ValueError("population inputs must be positive")
    return ((population_end / population_start) ** (1.0 / INTERVAL_YEARS) - 1.0) * 100.0


def validate_source_contract(source_rows: list[dict[str, str]], geography_rows: list[dict[str, str]]) -> dict[str, Any]:
    if len(source_rows) != 19:
        raise ValueError(f"expected 19 publication source rows; got {len(source_rows)}")
    geographies = current_geographies(geography_rows)
    seen_codes: set[str] = set()
    seen_ids: set[str] = set()
    formula_checks: list[dict[str, Any]] = []
    total_2010 = 0
    total_2020 = 0

    for row in source_rows:
        code = row["bps_code"]
        if code in seen_codes:
            raise ValueError(f"duplicate BPS code {code}")
        seen_codes.add(code)
        source_row_id = row["source_row_id"]
        if source_row_id in seen_ids:
            raise ValueError(f"duplicate source row id {source_row_id}")
        seen_ids.add(source_row_id)

        if code not in geographies:
            raise ValueError(f"unexpected current geography code {code}")
        expected_gid = geographies[code]["geography_id"]
        if row["geography_id"] != expected_gid:
            raise ValueError(f"canonical geography mismatch for {code}: {row['geography_id']} != {expected_gid}")
        expected_name = geographies[code]["canonical_name"]
        if row["geography_name"] != expected_name:
            raise ValueError(f"canonical geography name mismatch for {code}: {row['geography_name']} != {expected_name}")

        if row["source_publication_id"] != EXPECTED_PUBLICATION_ID:
            raise ValueError("publication id drifted")
        if row["source_publication_number"] != EXPECTED_PUBLICATION_NUMBER:
            raise ValueError("publication number drifted")
        if row["source_table"] != EXPECTED_TABLE:
            raise ValueError("source table drifted")
        if row["target_indicator"] != "population_growth" or row["target_claim_type"] != "derived":
            raise ValueError(f"indicator/evidence semantics drifted for {code}")
        if row["verification_status"] != "publication_table_crosschecked_against_official_census_counts_and_formula":
            raise ValueError(f"verification status drifted for {code}")

        try:
            pop_2010 = int(row["population_2010_may"])
            pop_2020 = int(row["population_2020_september"])
            published_growth = float(row["growth_2010_2020_pct_per_year"])
            prior_growth = float(row["growth_2000_2010_pct_per_year"])
        except ValueError as exc:
            raise ValueError(f"non-numeric publication value for {code}") from exc
        if pop_2010 <= 0 or pop_2020 <= 0:
            raise ValueError(f"non-positive population count for {code}")
        if not math.isfinite(published_growth) or published_growth <= 0:
            raise ValueError(f"invalid 2010-2020 growth rate for {code}")
        if not math.isfinite(prior_growth):
            raise ValueError(f"invalid 2000-2010 context rate for {code}")

        calculated = geometric_growth_pct(pop_2010, pop_2020)
        if round(calculated, 2) != round(published_growth, 2):
            raise ValueError(
                f"published LPP formula cross-check failed for {code}: "
                f"published={published_growth:.2f}, calculated={calculated:.6f}"
            )
        total_2010 += pop_2010
        total_2020 += pop_2020
        formula_checks.append(
            {
                "bps_code": code,
                "geography_id": row["geography_id"],
                "published_growth_pct_per_year": published_growth,
                "calculated_growth_pct_per_year": round(calculated, 9),
                "rounded_match": True,
            }
        )

    if seen_codes != EXPECTED_CODES:
        raise ValueError(f"publication geography footprint incomplete: {sorted(seen_codes)}")
    if total_2010 != EXPECTED_SP2010_TOTAL:
        raise ValueError(f"SP2010 publication row sum mismatch: {total_2010}")
    if total_2020 != EXPECTED_SP2020_TOTAL:
        raise ValueError(f"SP2020 publication row sum mismatch: {total_2020}")

    return {
        "source_row_count": len(source_rows),
        "geography_count": len(seen_codes),
        "publication_id": EXPECTED_PUBLICATION_ID,
        "publication_number": EXPECTED_PUBLICATION_NUMBER,
        "table": EXPECTED_TABLE,
        "population_2010_row_sum": total_2010,
        "population_2020_row_sum": total_2020,
        "interval_months": INTERVAL_MONTHS,
        "interval_years": INTERVAL_YEARS,
        "formula": "100 * ((P2020 / P2010) ** (1 / (124/12)) - 1)",
        "formula_match_count": sum(1 for item in formula_checks if item["rounded_match"]),
        "formula_checks": formula_checks,
        "target_indicator": "population_growth",
        "target_claim_type": "derived",
        "canonical_promotion_ready": False,
        "canonical_promotion_performed": False,
    }


def build_report(source_path: Path, geography_path: Path) -> dict[str, Any]:
    validation = validate_source_contract(read_csv(source_path), read_csv(geography_path))
    return {
        "schema": "ranah-observatory/bps-population-growth-publication-contract/v1",
        "source": {
            "agency": "BPS Provinsi Sumatera Barat",
            "publication_title": "Provinsi Sumatera Barat Dalam Angka 2021",
            "publication_id": EXPECTED_PUBLICATION_ID,
            "publication_number": EXPECTED_PUBLICATION_NUMBER,
            "table": EXPECTED_TABLE,
            "official_publication_url": (
                "https://sumbar.bps.go.id/id/publication/2021/02/26/"
                "438e46e73d9a64df8d8c34f2/provinsi-sumatera-barat-dalam-angka-2021.html"
            ),
            "sp2010_crosscheck_url": "https://sensus.bps.go.id/topik/tabular/sp2010/10/91625/0",
            "sp2020_crosscheck_url": "https://sensus.bps.go.id/topik/tabular/sp2020/1/4/0",
        },
        "validation": validation,
        "decision": {
            "source_contract_qualified": True,
            "published_growth_values_in_scope": 19,
            "canonical_growth_rows_added": 0,
            "next_step": "materialize_official_bps_derived_population_growth_with_durable_provenance",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate BPS Table 3.1.1 population-growth source contract")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--geographies", type=Path, default=DEFAULT_GEOGRAPHIES)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = build_report(args.source, args.geographies)
    except (OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}")
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
