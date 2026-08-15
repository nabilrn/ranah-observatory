from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    manifest_path = root / "bnpb-disaster-panel.manifest.json"
    source_path = root / "bnpb-disaster-source-native.csv"
    canonical_path = root / "bnpb-disaster-canonical-observations.csv"
    provenance_path = root / "bnpb-disaster-canonical-provenance.csv"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_rows = read_csv(source_path)
    canonical = read_csv(canonical_path)
    provenance = read_csv(provenance_path)

    if manifest.get("schema") != "ranah-observatory/bnpb-disaster-panel/v1":
        errors.append("unexpected BNPB disaster manifest schema")
    expected_counts = {
        "canonical_observation_count": 38,
        "canonical_provenance_count": 1,
        "source_native_count": 627,
        "mapped_geography_count": 19,
    }
    for field, expected in expected_counts.items():
        if manifest.get(field) != expected:
            errors.append(f"manifest {field}={manifest.get(field)!r}, expected {expected}")
    if set(manifest.get("canonical_indicators", [])) != {"flood_events", "landslide_events"}:
        errors.append("canonical BNPB indicators must be exactly flood_events and landslide_events")
    if manifest.get("official_crosscheck") != "passed":
        errors.append("official 2024 cross-check must pass")

    if len(canonical) != 38:
        errors.append(f"canonical CSV has {len(canonical)} rows, expected 38")
    indicator_counts = Counter(row["indicator_id"] for row in canonical)
    if indicator_counts != Counter({"flood_events": 19, "landslide_events": 19}):
        errors.append(f"unexpected canonical indicator counts: {dict(indicator_counts)}")
    geography_indicators: dict[str, set[str]] = defaultdict(set)
    for row in canonical:
        geography_indicators[row["geography_id"]].add(row["indicator_id"])
        if row["time_start"] != "2024-01-01" or row["time_end"] != "2024-12-31":
            errors.append(f"{row['observation_id']}: canonical event period must be calendar 2024")
        if row["unit"] != "count" or row["claim_type"] != "observed":
            errors.append(f"{row['observation_id']}: unexpected unit or claim type")
        try:
            if float(row["value_numeric"]) < 0:
                errors.append(f"{row['observation_id']}: negative event count")
        except ValueError:
            errors.append(f"{row['observation_id']}: nonnumeric event count")
        if "independent_official_crosscheck=passed" not in row["notes"]:
            errors.append(f"{row['observation_id']}: missing official cross-check provenance note")
    if len(geography_indicators) != 19:
        errors.append(f"canonical observations cover {len(geography_indicators)} geographies, expected 19")
    for geography_id, indicators in geography_indicators.items():
        if indicators != {"flood_events", "landslide_events"}:
            errors.append(f"{geography_id}: incomplete canonical indicator pair")

    if len(source_rows) != 627:
        errors.append(f"source-native CSV has {len(source_rows)} rows, expected 627")
    family_counts = Counter(row["metric_family"] for row in source_rows)
    expected_families = {
        "recorded_disaster_events_total": 285,
        "recorded_disaster_events_by_type": 171,
        "reported_affected_people_by_type": 171,
    }
    if dict(family_counts) != expected_families:
        errors.append(f"unexpected source-native family counts: {dict(family_counts)}")
    for row in source_rows:
        if not row["canonical_geography_id"] or not row["source_geography_code"] or not row["source_geography_name"]:
            errors.append(f"{row['source_row_id']}: incomplete geography provenance")
        if row["metric_family"] == "reported_affected_people_by_type" and row["promotion_status"] != "held_source_native":
            errors.append(f"{row['source_row_id']}: affected-person row escaped hold policy")
        if row["metric_family"] == "recorded_disaster_events_total" and row["promotion_status"] != "source_native_context":
            errors.append(f"{row['source_row_id']}: all-disaster total escaped context-only policy")

    if len(provenance) != 1:
        errors.append(f"provenance CSV has {len(provenance)} rows, expected 1")
    elif "5ff9f41f-8312-4b7c-aa18-fdbedac6ee7e" not in provenance[0]["notes"]:
        errors.append("canonical provenance does not retain independent official cross-check resource")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate generated BNPB disaster artifact.")
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    try:
        errors = validate(args.root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"BNPB disaster artifact validation FAILED: {exc}", file=sys.stderr)
        return 1
    if errors:
        print("BNPB disaster artifact validation FAILED", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("BNPB disaster artifact validation passed: 38 canonical observations, 627 source-native rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
