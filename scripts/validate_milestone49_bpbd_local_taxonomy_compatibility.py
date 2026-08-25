#!/usr/bin/env python3
from __future__ import annotations

import csv
import gzip
import io
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "manifests" / "milestone49_bpbd_local_taxonomy_compatibility.json"
TAXONOMY = ROOT / "data" / "registries" / "bpbd_sumbar_2015_incident_taxonomy.csv"
M42_ROWS = ROOT / "data" / "processed" / "bnpb_historical_source_native_rows_2000_2017.csv.gz"
M43 = ROOT / "data" / "manifests" / "milestone43_bnpb_historical_semantics_geography_gate.json"
M48 = ROOT / "data" / "manifests" / "milestone48_bnpb_annual_republication_lineage.json"

EXPECTED_LARGEST = {
    "Kebakaran": 285,
    "Longsor": 130,
    "Angin Kencang": 116,
    "Banjir": 68,
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def _read_m42_rows(path: Path) -> list[dict[str, str]]:
    payload = gzip.decompress(path.read_bytes()).decode("utf-8")
    return list(csv.DictReader(io.StringIO(payload)))


def validate() -> dict[str, Any]:
    manifest = _read_json(MANIFEST)
    taxonomy = _read_csv(TAXONOMY)
    m42_rows = _read_m42_rows(M42_ROWS)
    m43 = _read_json(M43)
    m48 = _read_json(M48)

    assert manifest["milestone"] == 49
    assert manifest["depends_on"] == [43, 48]

    m42_2015 = [row for row in m42_rows if int(row["source_year"]) == 2015]
    assert len(m42_2015) == 14
    m42_event_sum = sum(int(row["jumlah_kejadian_value"]) for row in m42_2015)
    assert m42_event_sum == 89

    assert len(taxonomy) == 21
    taxonomy_counts = {row["incident_category"]: int(row["reported_count"]) for row in taxonomy}
    assert sum(taxonomy_counts.values()) == 686
    for category, count in EXPECTED_LARGEST.items():
        assert taxonomy_counts[category] == count
    assert "Orang Hilang" in taxonomy_counts
    assert "Orang Gantung Diri" in taxonomy_counts
    assert "Penemuan Mayat" in taxonomy_counts
    assert all(row["comparison_to_m42"] == "not_directly_comparable" for row in taxonomy)

    sources = manifest["sources"]
    assert sources["m42_dibi_2015"]["explicit_geography_rows"] == 14
    assert sources["m42_dibi_2015"]["jumlah_kejadian_sum"] == 89
    assert sources["bpbd_sumbar_pusdalops_2015"]["reported_incident_total"] == 686
    assert sources["bpbd_sumbar_pusdalops_2015"]["reported_category_count"] == 21
    assert sources["perka_bnpb_7_2012"]["evidentiary_role"]

    profile = manifest["bpbd_2015_taxonomy_profile"]
    assert profile["category_count"] == 21
    assert profile["reported_total"] == 686
    assert profile["largest_categories"] == EXPECTED_LARGEST
    assert profile["taxonomy_scope_state"] == "broader_local_operational_incident_universe"

    comparison = manifest["comparison"]
    assert comparison["year"] == 2015
    assert comparison["m42_dibi_total"] == 89
    assert comparison["bpbd_pusdalops_reported_total"] == 686
    assert comparison["arithmetic_difference_bpbd_minus_m42"] == 597
    assert comparison["difference_interpretation"] == "not_interpretable_as_revision_undercount_or_error"
    assert comparison["direct_value_reconciliation_authorized"] is False
    assert comparison["district_row_reconciliation_authorized"] is False
    assert comparison["impact_metric_reconciliation_authorized"] is False

    q = manifest["qualification"]
    assert q["separate_local_publication_found"] is True
    assert q["separate_local_operational_taxonomy_found"] is True
    assert q["upstream_source_independence_from_dibi_proven"] is False
    assert q["same_event_taxonomy_as_m42_proven"] is False
    assert q["same_inclusion_threshold_as_m42_proven"] is False
    assert q["same_deduplication_rules_as_m42_proven"] is False
    assert q["same_victim_impact_schema_as_m42_proven"] is False
    assert q["independent_same_concept_crosscheck_qualified"] is False
    assert q["bpbd_686_vs_m42_89_may_be_interpreted_as_dibi_undercount"] is False
    assert q["bpbd_686_vs_m42_89_may_be_interpreted_as_release_revision"] is False
    assert q["operational_incident_layer_candidate"] is True
    assert q["canonical_historical_impact_promotion_authorized"] is False
    assert q["promotion_gate_fail_closed"] is True

    assert m43["qualification"]["canonical_historical_panel_promotion_authorized"] is False
    assert m43["qualification"]["absent_row_zero_inference_authorized"] is False
    assert m48["result"]["independent_same_grain_counterpart_found"] is False
    assert m48["result"]["canonical_historical_impact_promotion_authorized"] is False

    return {
        "schema": "ranah-observatory/milestone49-bpbd-local-taxonomy-compatibility-audit/v1",
        "milestone": 49,
        "m42_2015_explicit_geography_rows": len(m42_2015),
        "m42_2015_event_sum": m42_event_sum,
        "bpbd_operational_category_count": len(taxonomy),
        "bpbd_operational_incident_total": sum(taxonomy_counts.values()),
        "arithmetic_difference": 597,
        "independent_same_concept_crosscheck_qualified": False,
        "canonical_historical_impact_promotion_authorized": False,
        "complete": True,
    }


def main() -> int:
    try:
        report = validate()
    except (AssertionError, OSError, ValueError, csv.Error, json.JSONDecodeError) as exc:
        print(f"M49 validation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
