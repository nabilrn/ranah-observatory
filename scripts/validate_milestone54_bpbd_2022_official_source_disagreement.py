#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
M53 = ROOT / "data" / "manifests" / "milestone53_bpbd_dibi_2022_source_qualification.json"
M54 = ROOT / "data" / "manifests" / "milestone54_bpbd_2022_official_source_disagreement.json"
QUEUE = ROOT / "data" / "acquisition_requests" / "bpbd_publications.csv"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _allowed(url: str, allowed_host: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    host = parsed.hostname.lower().rstrip(".")
    allowed = allowed_host.lower().rstrip(".")
    return host == allowed or host.endswith("." + allowed)


def validate() -> dict[str, Any]:
    m53 = _read_json(M53)
    m54 = _read_json(M54)
    queue = _read_csv(QUEUE)

    assert m54["schema"] == "ranah-observatory/milestone54-bpbd-2022-official-source-disagreement/v1"
    assert m54["milestone"] == 54
    assert m54["depends_on"] == [53]

    dibi = m54["sources"]["dibi_2022"]
    lkj = m54["sources"]["lkj_2022"]
    audit = m54["reconciliation_audit"]

    m53_targets = m53["indexed_verification_targets"]
    assert dibi["event_total"] == m53_targets["province_totals"]["events"] == 1021
    assert dibi["hazard_counts"] == {
        "abrasi_pantai": 5,
        "angin_kencang": 674,
        "banjir": 123,
        "banjir_bandang": 5,
        "gempa_bumi": 2,
        "kebakaran_hutan_dan_lahan": 92,
        "longsor": 120,
    }
    assert sum(dibi["hazard_counts"].values()) == dibi["event_total"]
    assert dibi["raw_bytes_frozen"] is False

    assert lkj["event_total"] == 1047
    assert lkj["pdf_page_count_observed"] == 77
    assert lkj["table_locator"] == "Tabel 3.4.7, PDF pages 59-60"
    assert lkj["raw_bytes_frozen"] is False
    assert sum(lkj["hazard_counts"].values()) == lkj["event_total"]
    assert lkj["hazard_counts"] == {
        "angin_kencang": 108,
        "abrasi": 1,
        "abrasi_pantai": 4,
        "banjir": 122,
        "banjir_bandang": 6,
        "erosi_sungai": 3,
        "gempa_bumi": 6,
        "karhutla": 87,
        "kekeringan": 2,
        "longsor": 131,
        "pohon_tumbang": 549,
        "puting_beliung": 27,
        "tanah_bergerak": 1,
    }

    assert audit["raw_event_total_difference_lkj_minus_dibi"] == lkj["event_total"] - dibi["event_total"] == 26
    assert audit["dibi_hazard_category_count"] == len(dibi["hazard_counts"]) == 7
    assert audit["lkj_hazard_category_count"] == len(lkj["hazard_counts"]) == 13

    bridge = audit["obvious_taxonomy_bridge"]
    expected = {
        "dibi_abrasi_pantai": (["abrasi", "abrasi_pantai"], 5, 5, 0),
        "dibi_angin_kencang": (["angin_kencang", "pohon_tumbang", "puting_beliung"], 684, 674, 10),
        "dibi_banjir": (["banjir"], 122, 123, -1),
        "dibi_banjir_bandang": (["banjir_bandang"], 6, 5, 1),
        "dibi_gempa_bumi": (["gempa_bumi"], 6, 2, 4),
        "dibi_kebakaran_hutan_dan_lahan": (["karhutla"], 87, 92, -5),
        "dibi_longsor": (["longsor"], 131, 120, 11),
    }
    for key, (components, mapped_total, dibi_total, difference) in expected.items():
        row = bridge[key]
        assert row["lkj_components"] == components
        assert sum(lkj["hazard_counts"][component] for component in components) == row["lkj_mapped_total"] == mapped_total
        assert row["dibi_total"] == dibi_total
        assert row["difference"] == mapped_total - dibi_total == difference

    unmatched = audit["lkj_categories_without_obvious_dibi_counterpart"]
    assert unmatched == {"erosi_sungai": 3, "kekeringan": 2, "tanah_bergerak": 1, "total": 6}
    bridge_difference = sum(row["difference"] for row in bridge.values())
    assert bridge_difference == 20
    assert bridge_difference + unmatched["total"] == audit["mapped_difference_plus_unmatched_lkj_categories"] == 26
    assert audit["reconciles_to_raw_total_difference"] is True

    interpretation = m54["interpretation"]
    assert interpretation["same_agency_does_not_imply_same_event_universe"] is True
    assert interpretation["taxonomy_difference_is_material"] is True
    assert interpretation["event_level_equivalence_demonstrated"] is False
    assert interpretation["safe_to_average_totals"] is False
    assert interpretation["safe_to_concatenate_rows"] is False
    assert interpretation["safe_to_use_interchangeably_in_timeseries"] is False

    contract = m54["dashboard_contract"]
    assert contract["default_2022_event_total_source"] == "dibi_2022_after_raw_verification"
    assert contract["lkj_2022_role"] == "cross_publication_validation_and_disagreement_evidence"
    assert contract["show_source_family_on_proof_rows"] is True
    assert contract["preserve_native_hazard_labels"] is True
    assert contract["do_not_hide_1021_vs_1047_disagreement"] is True
    assert contract["cross_source_reconciliation_required_before_unified_series"] is True

    matching = [row for row in queue if row["request_id"] == "bpbd_lkj_2022"]
    assert len(matching) == 1
    request = matching[0]
    assert request["priority"] == "P1"
    assert request["anchor_year"] == "2022"
    assert request["exit_gate_candidate"].lower() == "no"
    assert request["output_filename"] == "bpbd-lkj-sumbar-2022.pdf"
    assert request["allowed_host"] == "sumbarprov.go.id"
    assert request["official_page_url"] == lkj["official_pdf_url"]
    assert _allowed(request["official_page_url"], request["allowed_host"])
    assert "1047" in request["purpose"]
    assert "1021" in request["purpose"]

    result = m54["result"]
    assert result["official_cross_publication_disagreement_confirmed"] is True
    assert result["taxonomy_bridge_attempted"] is True
    assert result["taxonomy_bridge_resolves_total_difference"] is False
    assert result["canonical_unified_2022_series_authorized"] is False
    assert result["dibi_2022_materialization_authorized"] is False
    assert result["lkj_2022_materialization_authorized"] is False

    return {
        "schema": "ranah-observatory/milestone54-bpbd-2022-official-source-disagreement-audit/v1",
        "milestone": 54,
        "dibi_events": dibi["event_total"],
        "lkj_events": lkj["event_total"],
        "event_gap": audit["raw_event_total_difference_lkj_minus_dibi"],
        "dibi_hazard_categories": len(dibi["hazard_counts"]),
        "lkj_hazard_categories": len(lkj["hazard_counts"]),
        "bridge_difference": bridge_difference,
        "unmatched_lkj_events": unmatched["total"],
        "unified_series_authorized": False,
        "complete": True,
    }


def main() -> int:
    try:
        report = validate()
    except (AssertionError, OSError, ValueError, KeyError, csv.Error, json.JSONDecodeError) as exc:
        print(f"M54 validation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
