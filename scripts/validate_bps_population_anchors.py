#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUALIFICATION = ROOT / "data" / "registries" / "bps_population_anchor_qualification.csv"
DEFAULT_CANONICAL = ROOT / "data" / "processed" / "bps" / "expansion" / "bps-expansion-canonical-observations.csv"

EXPECTED_YEARS = (1971, 1980, 1990, 1995, 2000, 2005, 2010, 2015, 2020)
EXPECTED_COUNTS = {
    1971: 15,
    1980: 15,
    1990: 15,
    1995: 15,
    2000: 16,
    2005: 20,
    2010: 20,
    2015: 20,
    2020: 20,
}
OLD_15_CODES = {
    "1300", "1302", "1303", "1304", "1305", "1306", "1307", "1308", "1309",
    "1371", "1372", "1373", "1374", "1375", "1376",
}
ANOMALOUS_1995_CODES = {
    "1301", "1303", "1304", "1305", "1306", "1307", "1308", "1309", "1310",
    "1372", "1373", "1374", "1375", "1376", "1377",
}
CODES_2000 = OLD_15_CODES | {"1301"}
CURRENT_20_CODES = {
    "1300", "1301", "1302", "1303", "1304", "1305", "1306", "1307", "1308", "1309",
    "1310", "1311", "1312", "1371", "1372", "1373", "1374", "1375", "1376", "1377",
}
EXPECTED_CODE_SETS = {
    1971: OLD_15_CODES,
    1980: OLD_15_CODES,
    1990: OLD_15_CODES,
    1995: ANOMALOUS_1995_CODES,
    2000: CODES_2000,
    2005: CURRENT_20_CODES,
    2010: CURRENT_20_CODES,
    2015: CURRENT_20_CODES,
    2020: CURRENT_20_CODES,
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def validate_qualification(rows: list[dict[str, str]]) -> dict[str, Any]:
    if len(rows) != len(EXPECTED_YEARS):
        raise ValueError(f"expected {len(EXPECTED_YEARS)} qualification rows; got {len(rows)}")
    by_year: dict[int, dict[str, str]] = {}
    for row in rows:
        year = int(row["year"])
        if year in by_year:
            raise ValueError(f"duplicate population anchor qualification year {year}")
        by_year[year] = row
        if int(row["total_sex_row_count"]) != EXPECTED_COUNTS.get(year):
            raise ValueError(f"unexpected qualified row count for {year}")
        if not SHA256_RE.fullmatch(row["snapshot_sha256"]):
            raise ValueError(f"invalid audited snapshot SHA-256 for {year}")
        if not row["population_growth_derivation"].startswith("blocked"):
            raise ValueError(f"population growth must remain blocked for {year} in this milestone")
    if tuple(sorted(by_year)) != EXPECTED_YEARS:
        raise ValueError(f"unexpected population anchor qualification years: {sorted(by_year)}")
    if by_year[1995]["source_integrity_decision"] != "hold_key_label_alignment_anomaly":
        raise ValueError("1995 source-key anomaly must remain held")
    if by_year[1995]["population_total_promotion"] != "hold_all_rows":
        raise ValueError("1995 rows must not be promoted")
    if by_year[2020]["population_total_promotion"] != "already_canonical":
        raise ValueError("2020 SP2020 anchor must remain linked to the existing canonical expansion")
    if by_year[2020]["reference_date_decision"] != "qualified_september_2020":
        raise ValueError("2020 reference-date qualification drifted")
    return {
        "qualification_year_count": len(by_year),
        "growth_derivation_ready": False,
        "held_source_integrity_years": [1995],
        "already_canonical_years": [2020],
    }


def _canonical_code(geography_id: str) -> str:
    if geography_id == "idn.13":
        return "1300"
    prefix = "idn.13."
    if not geography_id.startswith(prefix):
        raise ValueError(f"unexpected canonical geography {geography_id!r}")
    return geography_id[len(prefix):]


def validate_2020_against_existing_canonical(
    source_rows: list[dict[str, str]], canonical_rows: list[dict[str, str]]
) -> dict[str, Any]:
    source = {
        row["bps_vervar_id"]: float(row["value"])
        for row in source_rows
        if row["bps_th_label"] == "2020" and row["bps_turvar_id"] == "34"
    }
    canonical_population = [row for row in canonical_rows if row["indicator_id"] == "population_total"]
    if len(canonical_population) != 20:
        raise ValueError(f"expected 20 existing canonical SP2020 rows; got {len(canonical_population)}")
    canonical = {_canonical_code(row["geography_id"]): float(row["value_numeric"]) for row in canonical_population}
    if set(source) != CURRENT_20_CODES or set(canonical) != CURRENT_20_CODES:
        raise ValueError("2020 source/canonical geography footprint mismatch")
    differences = {
        code: source[code] - canonical[code]
        for code in sorted(CURRENT_20_CODES)
        if source[code] != canonical[code]
    }
    if differences:
        raise ValueError(f"live SP2020 source differs from existing canonical expansion: {differences}")
    return {"row_count": 20, "values_match_existing_canonical": True}


def validate_live_source(rows: list[dict[str, str]], canonical_rows: list[dict[str, str]]) -> dict[str, Any]:
    selected = [
        row for row in rows
        if row.get("bps_var_id") == "484" and row.get("bps_turvar_id") == "34"
    ]
    if len(selected) != sum(EXPECTED_COUNTS.values()):
        raise ValueError(f"expected 156 total-sex source rows; got {len(selected)}")
    by_year: dict[int, list[dict[str, str]]] = {}
    for row in selected:
        year = int(row["bps_th_label"])
        by_year.setdefault(year, []).append(row)
        value = float(row["value"])
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"invalid population value for {year}/{row['bps_vervar_id']}: {value}")
        if row.get("bps_var_unit") != "Jiwa":
            raise ValueError(f"unexpected var 484 unit for {year}: {row.get('bps_var_unit')!r}")
    if tuple(sorted(by_year)) != EXPECTED_YEARS:
        raise ValueError(f"live source periods differ from audited anchors: {sorted(by_year)}")

    profiles: dict[str, Any] = {}
    for year in EXPECTED_YEARS:
        year_rows = by_year[year]
        codes = {row["bps_vervar_id"] for row in year_rows}
        if len(year_rows) != EXPECTED_COUNTS[year]:
            raise ValueError(f"unexpected total-sex row count for {year}: {len(year_rows)}")
        if codes != EXPECTED_CODE_SETS[year]:
            raise ValueError(
                f"source-code profile drift for {year}; expected={sorted(EXPECTED_CODE_SETS[year])}; got={sorted(codes)}"
            )
        profiles[str(year)] = {
            "total_sex_row_count": len(year_rows),
            "source_codes": sorted(codes),
            "profile_matches_audit": True,
        }

    # The 1995 response is not repaired here. Its key set itself is the evidence of
    # the audited structural alignment problem: province/current key 1300 is absent,
    # while the sequence includes 1301 and ends at 1377 rather than the expected
    # source-era 1300/1302.../1371...1376 profile.
    if "1300" in EXPECTED_CODE_SETS[1995] or "1300" in {row["bps_vervar_id"] for row in by_year[1995]}:
        raise ValueError("1995 anomaly guard no longer represents the audited source profile")

    return {
        "source_total_sex_row_count": len(selected),
        "profiles": profiles,
        "source_integrity_anomaly": {
            "year": 1995,
            "classification": "hold_key_label_alignment_anomaly",
            "auto_remap_allowed": False,
        },
        "sp2020_crosscheck": validate_2020_against_existing_canonical(selected, canonical_rows),
        "population_growth_derivation_ready": False,
        "population_growth_blockers": [
            "1995 source-key/metadata alignment anomaly",
            "pre-2020 local boundary continuity is not qualified for this anchor family",
            "exact reference dates are not qualified for non-2020 anchors",
        ],
    }


def build_report(
    qualification_path: Path,
    canonical_path: Path,
    source_long_path: Path | None = None,
) -> dict[str, Any]:
    qualification = validate_qualification(read_csv(qualification_path))
    report: dict[str, Any] = {
        "schema": "ranah-observatory/bps-population-anchor-audit/v1",
        "source_id": "bps_webapi",
        "bps_var_id": 484,
        "source_family": "BPS census and SUPAS population anchors",
        "audited_years": list(EXPECTED_YEARS),
        "qualification": qualification,
        "live_source_validation": "not_run",
        "promotion_decision": {
            "population_total_2020": "already_canonical",
            "additional_current_population_total_rows": 0,
            "population_growth_rows": 0,
            "population_growth_status": "blocked_pending_compatible_anchor_pairs",
        },
    }
    if source_long_path is not None:
        report["live_source_validation"] = validate_live_source(
            read_csv(source_long_path), read_csv(canonical_path)
        )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate BPS var 484 population-anchor qualification and optional live harvest")
    parser.add_argument("--qualification", type=Path, default=DEFAULT_QUALIFICATION)
    parser.add_argument("--canonical", type=Path, default=DEFAULT_CANONICAL)
    parser.add_argument("--source-long", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = build_report(args.qualification, args.canonical, args.source_long)
    except (OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}")
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
