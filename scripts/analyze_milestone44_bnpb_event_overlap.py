#!/usr/bin/env python3
"""Reconcile M42 historical BNPB event counts against the qualified 2010-2024 district matrix.

M44 phase 1 is deliberately narrow: it compares only explicit 2010-2017
`Jumlah Kejadian` rows from the historical archive with the already-qualified
BNPB district/city total-event resource. Missing historical rows are never
coerced to zero and the script does not promote any other historical metric.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
from collections import Counter, defaultdict
from pathlib import Path


DEFAULT_HISTORICAL = Path(
    "data/processed/bnpb_historical_source_native_rows_2000_2017.csv.gz"
)
DEFAULT_CURRENT = Path("data/processed/bnpb/disaster/bnpb-disaster-source-native.csv")
CURRENT_SOURCE_RECORD_ID = "bnpb_total_events_kab_2010_2024"
OVERLAP_YEARS = range(2010, 2018)


def load_historical(path: Path) -> list[dict[str, str]]:
    payload = gzip.decompress(path.read_bytes()).decode("utf-8")
    return list(csv.DictReader(io.StringIO(payload)))


def load_current(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def build_report(historical_path: Path, current_path: Path) -> dict:
    historical_rows = [
        row
        for row in load_historical(historical_path)
        if int(row["source_year"]) in OVERLAP_YEARS
    ]
    current_rows = [
        row
        for row in load_current(current_path)
        if row["source_record_id"] == CURRENT_SOURCE_RECORD_ID
        and int(row["year"]) in OVERLAP_YEARS
    ]

    current_by_key: dict[tuple[int, str], dict[str, str]] = {}
    current_geographies_by_year: defaultdict[int, set[str]] = defaultdict(set)
    for row in current_rows:
        key = (int(row["year"]), row["canonical_geography_id"])
        if key in current_by_key:
            raise ValueError(f"duplicate qualified current event key: {key}")
        current_by_key[key] = row
        current_geographies_by_year[key[0]].add(key[1])

    comparisons = []
    missing_current = []
    historical_keys = set()
    for row in historical_rows:
        year = int(row["source_year"])
        canonical_id = row["canonical_entity_id_by_name_lineage"]
        key = (year, canonical_id)
        if key in historical_keys:
            raise ValueError(f"duplicate historical overlap key: {key}")
        historical_keys.add(key)

        historical_value = int(row["jumlah_kejadian_value"])
        current = current_by_key.get(key)
        if current is None:
            missing_current.append(
                {
                    "year": year,
                    "canonical_geography_id": canonical_id,
                    "source_name_raw": row["source_name_raw"],
                    "historical_value": historical_value,
                }
            )
            continue

        current_value = int(float(current["value_numeric"]))
        delta = current_value - historical_value
        comparisons.append(
            {
                "year": year,
                "canonical_geography_id": canonical_id,
                "historical_source_name": row["source_name_raw"],
                "current_source_name": current["source_geography_name"],
                "historical_value": historical_value,
                "current_value": current_value,
                "delta_current_minus_historical": delta,
                "comparison_state": "exact_match" if delta == 0 else "value_disagreement",
                "historical_lineage_status": row["geography_lineage_status"],
                "historical_current_boundary_comparability": row[
                    "current_boundary_comparability"
                ],
            }
        )

    by_year = []
    for year in OVERLAP_YEARS:
        year_rows = [row for row in comparisons if row["year"] == year]
        exact = sum(row["comparison_state"] == "exact_match" for row in year_rows)
        disagree = len(year_rows) - exact
        historical_explicit = sum(int(row["source_year"]) == year for row in historical_rows)
        current_available = len(current_geographies_by_year[year])
        historical_total = sum(
            int(row["jumlah_kejadian_value"])
            for row in historical_rows
            if int(row["source_year"]) == year
        )
        current_on_historical_geographies = sum(
            row["current_value"] for row in year_rows
        )
        by_year.append(
            {
                "year": year,
                "historical_explicit_geographies": historical_explicit,
                "current_matrix_geographies": current_available,
                "compared_explicit_geographies": len(year_rows),
                "exact_matches": exact,
                "value_disagreements": disagree,
                "historical_explicit_sum": historical_total,
                "current_sum_on_same_explicit_geographies": current_on_historical_geographies,
                "sum_delta_current_minus_historical": (
                    current_on_historical_geographies - historical_total
                ),
            }
        )

    state_counts = Counter(row["comparison_state"] for row in comparisons)
    disagreements = [
        row for row in comparisons if row["comparison_state"] == "value_disagreement"
    ]
    disagreement_deltas = Counter(row["delta_current_minus_historical"] for row in disagreements)

    return {
        "schema": "ranah-observatory/milestone44-bnpb-event-overlap-reconciliation/v1",
        "milestone": 44,
        "phase": "event_count_overlap_2010_2017",
        "historical_source": str(historical_path),
        "current_source": str(current_path),
        "current_source_record_id": CURRENT_SOURCE_RECORD_ID,
        "comparison_contract": {
            "years": [2010, 2017],
            "historical_rows": "explicit M42 geography rows only",
            "join_key": ["year", "canonical_geography_id"],
            "historical_missing_rows_zero_filled": False,
            "historical_metric": "jumlah_kejadian",
            "current_metric_family": "recorded_disaster_events_total",
            "comparison_meaning": "value-level source-release reconciliation, not proof of true incidence",
        },
        "summary": {
            "historical_explicit_overlap_rows": len(historical_rows),
            "current_overlap_rows": len(current_rows),
            "compared_rows": len(comparisons),
            "missing_current_rows": len(missing_current),
            "exact_matches": state_counts["exact_match"],
            "value_disagreements": state_counts["value_disagreement"],
            "exact_match_rate": (
                state_counts["exact_match"] / len(comparisons) if comparisons else None
            ),
            "distinct_disagreement_deltas": len(disagreement_deltas),
        },
        "by_year": by_year,
        "missing_current": missing_current,
        "disagreements": disagreements,
        "comparisons": comparisons,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--historical", type=Path, default=DEFAULT_HISTORICAL)
    parser.add_argument("--current", type=Path, default=DEFAULT_CURRENT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    report = build_report(args.historical, args.current)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    if args.summary_only:
        printable = {
            "summary": report["summary"],
            "by_year": report["by_year"],
            "disagreements": report["disagreements"],
        }
    else:
        printable = report
    print(json.dumps(printable, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
