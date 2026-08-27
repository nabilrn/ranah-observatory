from __future__ import annotations

import csv
import json
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "validation" / "historical" / "public_finance_2000"
MANIFEST = BASE / "bps_construction_financing_composition_manifest.json"
COMPOSITION = ROOT / "data" / "processed" / "bps" / "historical_construction_financing_2000_source_native.csv"
APBD_ANCHOR = ROOT / "data" / "processed" / "bps" / "historical_apbd_construction_2000_source_native.csv"
DJPK_CANONICAL = ROOT / "data" / "processed" / "djpk" / "public_finance" / "djpk-fiscal-canonical-observations.csv"

EXPECTED = {
    "total_construction_completed": ("14", 345_371_439, Decimal("100.000000")),
    "financed_by_central_government_budget": ("15.1", 207_997_331, Decimal("60.224242")),
    "financed_by_local_government_budget": ("15.2", 39_956_642, Decimal("11.569180")),
    "financed_by_foreign_loan": ("15.3", 76_727_103, Decimal("22.215822")),
    "financed_by_state_enterprises": ("15.4", 1_229_691, Decimal("0.356049")),
    "financed_by_other_sources": ("15.5", 19_460_672, Decimal("5.634708")),
}
EXPECTED_COMPONENT_IDS = set(EXPECTED) - {"total_construction_completed"}
EXPECTED_TOTAL = EXPECTED["total_construction_completed"][1]
EXPECTED_APBN_APBD = 247_953_973
EXPECTED_HISTORICAL_GEOGRAPHY = "idn.13.h1958"


def _official_bps_url(value: str) -> bool:
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower().rstrip(".")
    return parsed.scheme == "https" and (host == "bps.go.id" or host.endswith(".bps.go.id"))


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def validate() -> dict[str, object]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows = _read_rows(COMPOSITION)
    apbd_rows = _read_rows(APBD_ANCHOR)
    djpk_rows = _read_rows(DJPK_CANONICAL)

    assert manifest["schema"] == "ranah-observatory/bps-construction-financing-composition-2000/v1"
    assert manifest["source_year"] == 2000
    assert manifest["source_geography_name"] == "Sumatera Barat"
    assert manifest["source_geography_type"] == "province"
    assert manifest["canonical_historical_geography_id"] == EXPECTED_HISTORICAL_GEOGRAPHY
    assert manifest["source_unit_label"] == "000 Rupiah"
    assert manifest["price_semantics"].startswith("nominal current rupiah")
    measure_family = manifest["measure_family"].casefold()
    assert "construction value completed" in measure_family
    assert "financing source" in measure_family

    for publication_key, expected_title, expected_number, expected_release in (
        ("primary_publication", "Statistik Konstruksi 2002", "05230.0307", "2003-09-15"),
        ("crosscheck_publication", "Statistik Konstruksi 2003", "05230.0407", "2004-07-19"),
    ):
        publication = manifest[publication_key]
        assert publication["title"] == expected_title
        assert publication["publisher"] == "Badan Pusat Statistik"
        assert publication["current_catalog_number"] == "6301003"
        assert publication["source_native_catalog_number"] == "6513"
        assert publication["publication_number"] == expected_number
        assert publication["release_date"] == expected_release
        assert publication["table_note"] == "Angka Sementara/Preliminary Figures"
        assert _official_bps_url(publication["publication_page_url"])
        assert _official_bps_url(publication["deep_search_url"])

    crosscheck_publication = manifest["crosscheck_publication"]
    assert crosscheck_publication["year_header_marker_R_interpretation"].startswith("not asserted")

    manifest_components = manifest["components_thousand_rupiah"]
    assert set(manifest_components) == set(EXPECTED)
    for measure_id, (table_number, raw_value, expected_share) in EXPECTED.items():
        component = manifest_components[measure_id]
        assert component["table_number"] == table_number
        assert component["primary_2000"] == raw_value
        assert component["crosscheck_2000"] == raw_value
        assert Decimal(str(component["share_of_total_percent"])) == expected_share.normalize()

    financing_sum = sum(manifest_components[key]["primary_2000"] for key in EXPECTED_COMPONENT_IDS)
    assert financing_sum == EXPECTED_TOTAL
    assert manifest_components["total_construction_completed"]["primary_2000"] == EXPECTED_TOTAL

    arithmetic = manifest["arithmetic_reconciliation"]
    assert arithmetic["financing_component_sum_thousand_rupiah"] == EXPECTED_TOTAL
    assert arithmetic["reported_total_construction_thousand_rupiah"] == EXPECTED_TOTAL
    assert arithmetic["difference_thousand_rupiah"] == 0
    assert arithmetic["exact_identity_holds"] is True
    assert arithmetic["government_budget_sources_apbn_plus_apbd_thousand_rupiah"] == EXPECTED_APBN_APBD
    assert Decimal(str(arithmetic["government_budget_sources_share_percent"])) == Decimal("71.793422")
    assert Decimal(str(arithmetic["share_sum_percent_rounded_6dp"])) == Decimal("100.000001")

    cross_publication = manifest["cross_publication_reconciliation"]
    assert cross_publication["all_2000_component_values_exact_match"] is True
    assert cross_publication["all_2000_total_values_exact_match"] is True
    assert cross_publication["component_count"] == 5
    assert cross_publication["primary_and_crosscheck_use_same_table_family"] is True

    semantic = manifest["semantic_boundary"]
    assert semantic["source_native_composition_authorized"] is True
    assert semantic["canonical_fiscal_account_mapping_authorized"] is False
    assert semantic["djpk_capital_expenditure_bridge_authorized"] is False
    assert semantic["panel_v3_integration_authorized"] is False
    assert semantic["deflation_authorized"] is False
    assert semantic["interpolation_authorized"] is False
    assert semantic["causal_claim_authorized"] is False
    blocked = set(semantic["not_equivalent_to"])
    assert "APBD expenditure composition" in blocked
    assert "DJPK fiscal realization accounts" in blocked
    assert "public investment composition" in blocked

    source_boundary = manifest["source_boundary"]
    assert source_boundary["raw_pdf_committed"] is False
    assert source_boundary["pdf_sha256_available_in_repository"] is False
    assert source_boundary["allstats_text_treated_as_numeric_evidence"] is True
    assert source_boundary["allstats_text_treated_as_artifact_sha_equivalent"] is False
    assert source_boundary["sumbar2000_yearbook_public_finance_zero_hit_resolved"] is False

    assert len(rows) == 6
    by_measure = {row["source_measure_id"]: row for row in rows}
    assert set(by_measure) == set(EXPECTED)
    assert len(by_measure) == len(rows)

    for measure_id, (table_number, raw_value, expected_share) in EXPECTED.items():
        row = by_measure[measure_id]
        assert row["source_id"] == "bps_construction_statistics"
        assert row["source_year"] == "2000"
        assert row["source_geography_name"] == "Sumatera Barat"
        assert row["source_geography_type"] == "province"
        assert row["canonical_historical_geography_id"] == EXPECTED_HISTORICAL_GEOGRAPHY
        assert row["source_table_number"] == table_number
        assert row["source_unit"] == "000 Rupiah"
        assert int(row["raw_value_thousand_rupiah"]) == raw_value
        assert int(row["normalized_nominal_idr"]) == raw_value * 1000
        assert Decimal(row["share_of_total_percent"]) == expected_share
        assert row["primary_publication"] == "Statistik Konstruksi 2002"
        assert row["crosscheck_publication"] == "Statistik Konstruksi 2003"
        assert row["cross_publication_status"] == "exact_2000_value_match"
        assert row["canonical_indicator_id"] == ""
        assert row["canonical_mapping_status"] == "not_authorized"
        assert row["reconstruction_state"] == "observed_source_published_crosschecked_preliminary"

    row_component_sum = sum(int(by_measure[key]["raw_value_thousand_rupiah"]) for key in EXPECTED_COMPONENT_IDS)
    assert row_component_sum == int(by_measure["total_construction_completed"]["raw_value_thousand_rupiah"])

    rounded_share_sum = sum(Decimal(by_measure[key]["share_of_total_percent"]) for key in EXPECTED_COMPONENT_IDS)
    assert rounded_share_sum == Decimal("100.000001")

    assert len(apbd_rows) == 1
    apbd_anchor = apbd_rows[0]
    apbd_component = by_measure["financed_by_local_government_budget"]
    assert int(apbd_anchor["raw_value_thousand_rupiah"]) == int(apbd_component["raw_value_thousand_rupiah"])
    assert int(apbd_anchor["normalized_nominal_idr"]) == int(apbd_component["normalized_nominal_idr"])
    assert apbd_anchor["source_table_number"] == apbd_component["source_table_number"] == "15.2"

    assert djpk_rows
    assert any(row["fiscal_account_id"] == "capital_expenditure" for row in djpk_rows)
    assert all(row["fiscal_account_id"] not in EXPECTED_COMPONENT_IDS for row in djpk_rows)

    return {
        "source_native_rows": len(rows),
        "financing_components": len(EXPECTED_COMPONENT_IDS),
        "total_thousand_rupiah": EXPECTED_TOTAL,
        "component_sum_thousand_rupiah": row_component_sum,
        "exact_reconciliation": True,
        "all_2000_cross_publication_values_match": True,
        "apbd_anchor_consistent": True,
        "canonical_fiscal_mapping_authorized": False,
        "yearbook_public_finance_zero_hit_preserved": True,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
