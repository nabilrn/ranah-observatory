#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "manifests" / "milestone50_bpbd_historical_impact_source_qualification.json"
REGISTRY = ROOT / "data" / "registries" / "bpbd_historical_impact_source_candidates.csv"
M49 = ROOT / "data" / "manifests" / "milestone49_bpbd_local_taxonomy_compatibility.json"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def validate() -> dict[str, Any]:
    manifest = _read_json(MANIFEST)
    rows = _read_csv(REGISTRY)
    m49 = _read_json(M49)

    assert manifest["milestone"] == 50
    assert manifest["depends_on"] == [43, 48, 49]
    assert len(rows) == 2
    by_year = {int(row["year"]): row for row in rows}
    assert set(by_year) == {2015, 2017}

    row2015 = by_year[2015]
    assert row2015["authority_surface"] == "official_provincial_government_pdf"
    assert row2015["raw_official_acquired"] == "false"
    assert row2015["source_text_state"] == "official_pdf_search_indexed"
    assert row2015["completeness_state"] == "explicitly_incomplete_as_of_january_2016"
    assert row2015["upstream_independence_from_dibi"] == "not_proven"
    assert row2015["canonical_role"] == "source_family_qualification_only"

    row2017 = by_year[2017]
    assert row2017["authority_surface"] == "official_ppid_catalog_plus_indexed_mirror"
    assert row2017["raw_official_acquired"] == "false"
    assert "meninggal" in row2017["observed_or_indexed_impact_fields"]
    assert "mengungsi" in row2017["observed_or_indexed_impact_fields"]
    assert "perumahan_fasilitas_umum" in row2017["observed_or_indexed_impact_fields"]
    assert row2017["canonical_role"] == "schema_discovery_expected_values_only"

    e2015 = manifest["evidence"]["bpbd_2015"]
    assert e2015["table_4_1_year_label"] == 2015
    assert e2015["table_4_1_reported_event_total"] == 686
    assert e2015["following_graph_year_label"] == 2015
    assert e2015["following_narrative_year_label"] == 2015
    assert e2015["preceding_narrative_conflicting_year_label"] == 2014
    assert e2015["internal_year_label_inconsistency"] is True
    assert e2015["methodology_observed"]["same_event_same_date_counted_once"] is True
    assert e2015["methodology_observed"]["impact_and_loss_accumulated_for_event"] is True
    assert e2015["completeness_observed"]["2015_recap_complete_as_of_january_2016"] is False
    assert e2015["completeness_observed"]["report_explicitly_says_revision_needed"] is True

    e2017 = manifest["evidence"]["bpbd_2017"]
    assert e2017["official_ppid_catalog_record_id"] == 8604
    assert e2017["official_raw_artifact_acquired"] is False
    assert e2017["raw_verification_required_before_source_native_ingestion"] is True
    expected = e2017["indexed_expected_values_not_canonical"]
    assert expected == {
        "jumlah_kejadian": 725,
        "meninggal": 40,
        "hilang": 8,
        "mengungsi": 9387,
        "luka_sakit": 17,
        "taksiran_kerugian_rupiah": 20647693425,
    }

    result = manifest["result"]
    assert result["local_report_family_is_impact_capable"] is True
    assert result["official_2015_source_surface_found"] is True
    assert result["official_2017_archive_record_found"] is True
    assert result["official_2017_raw_artifact_acquired"] is False
    assert result["direct_bpbd_to_bnpb_value_reconciliation_authorized"] is False
    assert result["bpbd_source_native_impact_ingestion_authorized"] is False
    assert result["canonical_historical_impact_promotion_authorized"] is False

    q = manifest["qualification"]
    assert q["m49_2015_year_assignment_retained"] is True
    assert q["m49_686_total_retained"] is True
    assert q["m49_decision_invalidated"] is False
    assert q["internal_source_contradictions_must_be_preserved"] is True
    assert q["mirror_values_may_be_published_as_canonical_observations"] is False
    assert q["raw_official_artifact_required_for_source_native_ingestion"] is True
    assert q["promotion_gate_fail_closed"] is True

    assert m49["sources"]["bpbd_sumbar_pusdalops_2015"]["reported_incident_total"] == 686
    assert m49["qualification"]["canonical_historical_impact_promotion_authorized"] is False

    return {
        "schema": "ranah-observatory/milestone50-bpbd-historical-impact-source-qualification-audit/v1",
        "milestone": 50,
        "candidate_source_count": len(rows),
        "impact_capable_source_family": True,
        "official_2017_raw_artifact_acquired": False,
        "bpbd_source_native_impact_ingestion_authorized": False,
        "canonical_historical_impact_promotion_authorized": False,
        "complete": True,
    }


def main() -> int:
    try:
        report = validate()
    except (AssertionError, OSError, ValueError, csv.Error, json.JSONDecodeError) as exc:
        print(f"M50 validation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
