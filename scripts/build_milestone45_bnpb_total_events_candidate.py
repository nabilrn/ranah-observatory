#!/usr/bin/env python3
"""Build the M45 BNPB total-disaster-event canonical candidate.

This milestone deliberately does not rewrite the reviewed BNPB baseline. It
promotes the already-frozen source-native 2010-2024 all-disaster event matrix
into a candidate canonical artifact with explicit release and geography
boundaries, so downstream panel integration can be reviewed separately.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data/processed/bnpb/disaster/bnpb-disaster-source-native.csv"
DEFAULT_GEOGRAPHIES = ROOT / "data/registries/geographies.csv"
DEFAULT_PACKAGE_METADATA = ROOT / "data/processed/bnpb/m26_stage2_ckan_discovery/package-metadata.json"
DEFAULT_M44 = ROOT / "data/manifests/milestone44_bnpb_event_overlap_reconciliation.json"
SOURCE_RECORD_ID = "bnpb_total_events_kab_2010_2024"
RESOURCE_ID = "21044ffd-c397-4b3c-acbd-5adaa03d79e3"
INDICATOR_ID = "total_disaster_events"
YEARS = range(2010, 2025)

FIELDS = [
    "observation_id",
    "indicator_id",
    "geography_id",
    "time_start",
    "time_end",
    "frequency",
    "value_numeric",
    "unit",
    "claim_type",
    "provenance_id",
    "suppressed",
    "comparable",
    "methodology_version",
    "price_basis",
    "notes",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_id(prefix: str, *parts: str) -> str:
    return prefix + hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:24]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def current_sumbar_ids(path: Path) -> set[str]:
    rows = read_csv(path)
    ids = {
        row["geography_id"]
        for row in rows
        if row.get("parent_geography_id") == "idn.13"
        and row.get("geography_level") in {"regency", "city"}
        and row.get("status") == "current"
    }
    if len(ids) != 19:
        raise ValueError(f"expected 19 current Sumatera Barat kab/kota, found {len(ids)}")
    return ids


def resource_metadata(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    resources = payload.get("result", {}).get("resources", [])
    matches = [item for item in resources if item.get("id") == RESOURCE_ID]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one BNPB resource {RESOURCE_ID}, found {len(matches)}")
    return matches[0]


def validate_m44(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("milestone") != 44:
        raise ValueError("M45 requires the frozen M44 reconciliation manifest")
    result = payload.get("result", {})
    expected = {
        "historical_explicit_overlap_rows": 119,
        "compared_rows": 119,
        "exact_matches": 113,
        "value_disagreements": 6,
        "modern_rows_without_historical_explicit_row": 33,
        "modern_positive_where_historical_row_absent": 0,
    }
    for key, value in expected.items():
        if result.get(key) != value:
            raise ValueError(f"unexpected M44 {key}: {result.get(key)!r} != {value!r}")
    if payload.get("qualification", {}).get("event_count_overlap_reconciled") is not True:
        raise ValueError("M44 overlap reconciliation is not frozen as qualified")
    return payload


def build(source: Path, geographies: Path, package_metadata: Path, m44_path: Path):
    source_rows = [row for row in read_csv(source) if row.get("source_record_id") == SOURCE_RECORD_ID]
    if len(source_rows) != 285:
        raise ValueError(f"expected 285 total-event source rows, found {len(source_rows)}")

    canonical_ids = current_sumbar_ids(geographies)
    observed_ids = {row["canonical_geography_id"] for row in source_rows}
    if observed_ids != canonical_ids:
        raise ValueError("total-event matrix does not exactly cover the 19 current Sumatera Barat entity IDs")

    by_year: defaultdict[int, list[dict[str, str]]] = defaultdict(list)
    source_snapshot_hashes = set()
    seen_keys: set[tuple[str, int]] = set()
    for row in source_rows:
        year = int(row["year"])
        if year not in YEARS:
            raise ValueError(f"unexpected total-event year: {year}")
        geography_id = row["canonical_geography_id"]
        key = (geography_id, year)
        if key in seen_keys:
            raise ValueError(f"duplicate geography-year key: {key}")
        seen_keys.add(key)
        raw_value = row["value_numeric"]
        try:
            value_float = float(raw_value)
        except ValueError as exc:
            raise ValueError(f"non-numeric total-event value for {key}: {raw_value!r}") from exc
        if value_float < 0 or not value_float.is_integer():
            raise ValueError(f"total-event value must be a non-negative integer for {key}: {raw_value!r}")
        by_year[year].append(row)
        source_snapshot_hashes.add(row["source_snapshot_sha256"])

    if set(by_year) != set(YEARS):
        raise ValueError("total-event matrix does not cover every year 2010-2024")
    if any(len(rows) != 19 for rows in by_year.values()):
        raise ValueError("each total-event year must contain exactly 19 geography rows")
    if len(source_snapshot_hashes) != 1:
        raise ValueError("total-event rows do not share one frozen source snapshot hash")

    metadata = resource_metadata(package_metadata)
    if metadata.get("datastore_active") is not True:
        raise ValueError("qualified total-event resource is no longer marked DataStore-active in frozen metadata")
    m44 = validate_m44(m44_path)

    snapshot_sha = next(iter(source_snapshot_hashes))
    provenance_id = stable_id("bnpbprov_total_", RESOURCE_ID, snapshot_sha)
    output_rows = []
    for row in source_rows:
        year = int(row["year"])
        geography_id = row["canonical_geography_id"]
        value = int(float(row["value_numeric"]))
        output_rows.append(
            {
                "observation_id": stable_id("bnpbtotalobs_", INDICATOR_ID, geography_id, str(year), snapshot_sha),
                "indicator_id": INDICATOR_ID,
                "geography_id": geography_id,
                "time_start": f"{year}-01-01",
                "time_end": f"{year}-12-31",
                "frequency": "annual",
                "value_numeric": value,
                "unit": "count",
                "claim_type": "observed",
                "provenance_id": provenance_id,
                "suppressed": "false",
                "comparable": "",
                "methodology_version": "BNPB/DIBI total-event matrix 2010-2024 release",
                "price_basis": "",
                "notes": (
                    f"source_record={SOURCE_RECORD_ID}; source_geography={row['source_geography_code']}:{row['source_geography_name']}; "
                    "mapping=explicit_current_Permendagri_entity_crosswalk; entity_set_continuity_2010_2024=qualified; "
                    "exact_polygon_harmonization=not_proven; release_revision_provenance=M44; "
                    "recorded-event counts may reflect reporting intensity, classification practice, and retrospective source revision."
                ),
            }
        )

    output_rows.sort(key=lambda row: (row["geography_id"], row["time_start"]))
    year_sums = {
        str(year): sum(int(float(row["value_numeric"])) for row in rows)
        for year, rows in sorted(by_year.items())
    }
    value_counts = Counter(int(float(row["value_numeric"])) for row in source_rows)
    provenance = {
        "provenance_id": provenance_id,
        "source_id": "bnpb_satu_data",
        "source_record_id": SOURCE_RECORD_ID,
        "resource_id": RESOURCE_ID,
        "resource_name": metadata.get("name"),
        "resource_url": metadata.get("url"),
        "resource_last_modified": metadata.get("last_modified"),
        "resource_metadata_modified": metadata.get("metadata_modified"),
        "source_snapshot_sha256": snapshot_sha,
        "frozen_processed_source": str(source.relative_to(ROOT)),
        "frozen_processed_source_sha256": sha256_file(source),
        "m44_manifest": str(m44_path.relative_to(ROOT)),
        "m44_exact_match_rate": m44["result"]["exact_match_rate"],
        "geography_interpretation": (
            "Canonical IDs identify the stable 19 district/city entities represented by the release. "
            "M45 does not claim that historical values were recomputed on exact 2024 polygons."
        ),
    }
    summary = {
        "schema": "ranah-observatory/milestone45-bnpb-total-events-candidate/v1",
        "milestone": 45,
        "indicator_id": INDICATOR_ID,
        "period": [2010, 2024],
        "observation_count": len(output_rows),
        "geography_count": len(canonical_ids),
        "years_count": len(list(YEARS)),
        "complete_geography_year_matrix": len(output_rows) == 19 * 15,
        "minimum_value": min(value_counts),
        "maximum_value": max(value_counts),
        "year_sums": year_sums,
        "provenance": provenance,
        "qualification": {
            "source_release_matrix_complete": True,
            "entity_identity_continuity_2010_2024_qualified": True,
            "exact_polygon_harmonization_proven": False,
            "within_source_longitudinal_use_authorized_with_caveat": True,
            "historical_release_revisions_explicit": True,
            "type_specific_interpretation_forbidden": True,
            "true_incidence_claim_forbidden": True,
            "global_panel_integration_authorized": False,
        },
    }
    return output_rows, provenance, summary


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--geographies", type=Path, default=DEFAULT_GEOGRAPHIES)
    parser.add_argument("--package-metadata", type=Path, default=DEFAULT_PACKAGE_METADATA)
    parser.add_argument("--m44", type=Path, default=DEFAULT_M44)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--provenance-output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    args = parser.parse_args()

    rows, provenance, summary = build(args.source, args.geographies, args.package_metadata, args.m44)
    write_csv(args.output, rows)
    args.provenance_output.parent.mkdir(parents=True, exist_ok=True)
    args.provenance_output.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary["candidate_artifact"] = {
        "path": str(args.output),
        "sha256": sha256_file(args.output),
    }
    summary["candidate_provenance_artifact"] = {
        "path": str(args.provenance_output),
        "sha256": sha256_file(args.provenance_output),
    }
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    args.summary_output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
