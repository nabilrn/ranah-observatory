from __future__ import annotations

import csv
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "validation" / "historical" / "public_finance_2000"
MANIFEST = BASE / "bps_apbd_construction_anchor_manifest.json"
SOURCE_NATIVE = ROOT / "data" / "processed" / "bps" / "historical_apbd_construction_2000_source_native.csv"
DJPK_CANONICAL = ROOT / "data" / "processed" / "djpk" / "public_finance" / "djpk-fiscal-canonical-observations.csv"

EXPECTED_RAW_THOUSAND_IDR = 39_956_642
EXPECTED_NOMINAL_IDR = 39_956_642_000
EXPECTED_HISTORICAL_GEOGRAPHY = "idn.13.h1958"


def _official_bps_url(value: str) -> bool:
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower().rstrip(".")
    return parsed.scheme == "https" and (host == "bps.go.id" or host.endswith(".bps.go.id"))


def validate() -> dict[str, object]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    with SOURCE_NATIVE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    with DJPK_CANONICAL.open(encoding="utf-8", newline="") as handle:
        djpk_rows = list(csv.DictReader(handle))

    assert manifest["schema"] == "ranah-observatory/bps-apbd-construction-anchor-2000/v1"
    assert manifest["source_native_indicator_id"] == (
        "completed_construction_financed_by_local_government_budget"
    )
    assert manifest["source_year"] == 2000
    assert manifest["source_geography_name"] == "Sumatera Barat"
    assert manifest["canonical_historical_geography_id"] == EXPECTED_HISTORICAL_GEOGRAPHY
    assert manifest["source_unit_label"] == "000 Rupiah"
    assert manifest["raw_source_value_thousand_rupiah"] == EXPECTED_RAW_THOUSAND_IDR
    assert manifest["normalized_nominal_idr"] == EXPECTED_NOMINAL_IDR
    assert manifest["normalized_nominal_idr"] == manifest["raw_source_value_thousand_rupiah"] * 1000
    assert manifest["price_semantics"].startswith("nominal current rupiah")

    assert manifest["source_native_promotion_authorized"] is True
    assert manifest["canonical_indicator_mapping_authorized"] is False
    assert manifest["djpk_capital_expenditure_bridge_authorized"] is False
    assert manifest["panel_v3_integration_authorized"] is False
    assert manifest["interpolation_authorized"] is False
    assert manifest["deflation_authorized"] is False
    assert manifest["canonical_promotion_authorized"] is False

    blocked_equivalences = set(manifest["not_equivalent_to"])
    assert "total APBD expenditure" in blocked_equivalences
    assert "APBD capital expenditure / Belanja Modal" in blocked_equivalences
    assert "total public investment" in blocked_equivalences

    primary = manifest["primary_evidence"]
    crosscheck = manifest["crosscheck_evidence"]
    for evidence in (primary, crosscheck):
        assert evidence["publisher"] == "Badan Pusat Statistik"
        assert evidence["current_catalog_number"] == "6301003"
        assert evidence["source_native_catalog_number"] == "6513"
        assert evidence["table_number"] == "15.2"
        assert evidence["printed_page"] == 63
        assert evidence["table_title_id"] == (
            "NILAI KONSTRUKSI YANG DISELESAIKAN DARI SUMBER DANA APBD"
        )
        assert evidence["table_title_en"] == (
            "VALUE OF COMPLETED CONSTRUCTION FINANCED BY LOCAL GOVERNMENT BUDGET"
        )
        assert evidence["table_note"] == "Angka Sementara/Preliminary Figures"
        assert evidence["pdf_sha256_available_in_repository"] is False
        assert _official_bps_url(evidence["publication_page_url"])
        assert _official_bps_url(evidence["deep_search_url"])

    assert primary["publication_title"] == "Statistik Konstruksi 2002"
    assert primary["publication_number"] == "05230.0307"
    assert primary["release_date"] == "2003-09-15"
    assert primary["table_year_headers"] == [1998, 1999, 2000, 2001, 2002]
    assert primary["sumatera_barat_row_thousand_rupiah"] == {
        "1998": 47_227_148,
        "1999": 26_004_489,
        "2000": EXPECTED_RAW_THOUSAND_IDR,
        "2001": 46_038_043,
        "2002": 53_045_033,
    }

    assert crosscheck["publication_title"] == "Statistik Konstruksi 2003"
    assert crosscheck["publication_number"] == "05230.0407"
    assert crosscheck["release_date"] == "2004-07-19"
    assert crosscheck["table_year_headers"] == ["1999 R", "2000 R", "2001 R", "2002", "2003"]
    assert crosscheck["sumatera_barat_row_thousand_rupiah"] == {
        "1999": 26_004_489,
        "2000": EXPECTED_RAW_THOUSAND_IDR,
        "2001": 46_038_043,
        "2002": 53_045_032,
        "2003": 54_260_376,
    }
    assert crosscheck["year_header_marker_R_interpretation"].startswith("not asserted")

    reconciliation = manifest["cross_publication_reconciliation"]
    assert reconciliation["year_2000_exact_match"] is True
    assert reconciliation["primary_value_thousand_rupiah"] == EXPECTED_RAW_THOUSAND_IDR
    assert reconciliation["crosscheck_value_thousand_rupiah"] == EXPECTED_RAW_THOUSAND_IDR
    assert reconciliation["difference_thousand_rupiah"] == 0
    assert reconciliation["adjacent_year_revision_detected"] is True
    assert primary["sumatera_barat_row_thousand_rupiah"]["2002"] - crosscheck[
        "sumatera_barat_row_thousand_rupiah"
    ]["2002"] == 1

    boundary = manifest["source_boundary"]
    assert boundary["sumbar2000_yearbook_public_finance_zero_hit_resolved"] is False
    assert boundary["raw_pdf_committed"] is False
    assert boundary["allstats_text_treated_as_numeric_evidence"] is True
    assert boundary["allstats_text_treated_as_artifact_sha_equivalent"] is False

    assert len(rows) == 1
    row = rows[0]
    assert row["source_record_id"] == "bps_construction_2000_apbd_sumbar"
    assert row["source_year"] == "2000"
    assert row["source_geography_name"] == "Sumatera Barat"
    assert row["canonical_historical_geography_id"] == EXPECTED_HISTORICAL_GEOGRAPHY
    assert row["source_table_number"] == "15.2"
    assert row["source_unit"] == "000 Rupiah"
    assert int(row["raw_value_thousand_rupiah"]) == EXPECTED_RAW_THOUSAND_IDR
    assert int(row["normalized_nominal_idr"]) == EXPECTED_NOMINAL_IDR
    assert row["source_native_indicator_id"] == (
        "completed_construction_financed_by_local_government_budget"
    )
    assert row["canonical_indicator_id"] == ""
    assert row["canonical_mapping_status"] == "not_authorized"
    assert row["cross_publication_status"] == "exact_2000_value_match"
    assert row["release_status"] == "preliminary"
    assert "not DJPK Belanja Modal" in row["notes"]
    assert "No deflation, interpolation, or Panel v3 bridge is authorized" in row["notes"]

    assert djpk_rows
    assert any(r["fiscal_account_id"] == "capital_expenditure" for r in djpk_rows)
    assert all(r["fiscal_account_id"] != row["source_native_indicator_id"] for r in djpk_rows)

    return {
        "source_native_row_count": len(rows),
        "source_year": 2000,
        "raw_value_thousand_rupiah": EXPECTED_RAW_THOUSAND_IDR,
        "normalized_nominal_idr": EXPECTED_NOMINAL_IDR,
        "cross_publication_exact_match": True,
        "canonical_promotion_authorized": False,
        "djpk_capital_expenditure_bridge_authorized": False,
        "yearbook_public_finance_zero_hit_preserved": True,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
