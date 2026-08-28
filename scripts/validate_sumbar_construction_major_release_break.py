from __future__ import annotations

import csv
import json
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "validation" / "historical" / "public_finance_2000"
MANIFEST = BASE / "bps_construction_financing_major_release_break_2002_2003.json"
REVISION_MANIFEST = BASE / "bps_construction_financing_revision_audit_1998_2003.json"
BREAK_CSV = ROOT / "data" / "processed" / "bps" / "historical_construction_financing_major_release_break_2002_2003.csv"

MEASURES = {
    "total_construction_completed": "14",
    "financed_by_central_government_budget": "15.1",
    "financed_by_local_government_budget": "15.2",
    "financed_by_foreign_loan": "15.3",
    "financed_by_state_enterprises": "15.4",
    "financed_by_other_sources": "15.5",
}
COMPONENTS = set(MEASURES) - {"total_construction_completed"}

EXPECTED = {
    2002: {
        "total_construction_completed": (458_502_968, 717_299_178, Decimal("56.443737"), Decimal("1.564437371")),
        "financed_by_central_government_budget": (291_959_524, 356_752_390, Decimal("22.192414"), Decimal("1.221924139")),
        "financed_by_local_government_budget": (53_045_032, 182_985_630, Decimal("244.962804"), Decimal("3.449628044")),
        "financed_by_foreign_loan": (101_860_202, 159_353_907, Decimal("56.443737"), Decimal("1.564437375")),
        "financed_by_state_enterprises": (4_507_982, 7_052_456, Decimal("56.443748"), Decimal("1.564437480")),
        "financed_by_other_sources": (7_130_228, 11_154_795, Decimal("56.443735"), Decimal("1.564437350")),
    },
    2003: {
        "total_construction_completed": (469_007_986, 844_516_928, Decimal("80.064509"), Decimal("1.800645092")),
        "financed_by_central_government_budget": (298_648_772, 303_268_240, Decimal("1.546790"), Decimal("1.015467896")),
        "financed_by_local_government_budget": (54_260_376, 108_161_492, Decimal("99.337896"), Decimal("1.993378962")),
        "financed_by_foreign_loan": (104_193_978, 161_858_669, Decimal("55.343593"), Decimal("1.553435929")),
        "financed_by_state_enterprises": (4_611_267, 1_256_000, Decimal("-72.762367"), Decimal("0.272376334")),
        "financed_by_other_sources": (7_293_593, 269_972_527, Decimal("3601.502497"), Decimal("37.015024968")),
    },
}


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _official_bps_url(value: str) -> bool:
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower().rstrip(".")
    return parsed.scheme == "https" and (host == "bps.go.id" or host.endswith(".bps.go.id"))


def validate() -> dict[str, object]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    revision_manifest = json.loads(REVISION_MANIFEST.read_text(encoding="utf-8"))
    rows = _read_rows(BREAK_CSV)

    assert manifest["schema"] == "ranah-observatory/bps-construction-financing-major-release-break-2002-2003/v1"
    assert manifest["source_geography_name"] == "Sumatera Barat"
    assert manifest["canonical_historical_geography_id"] == "idn.13.h1958"
    assert manifest["source_unit_label"] == "000 Rupiah"
    assert manifest["price_semantics"] == "nominal current rupiah as published"

    earlier = manifest["earlier_release"]
    later = manifest["later_release"]
    assert earlier["publication_title"] == "Statistik Konstruksi 2003"
    assert earlier["publication_number"] == "05230.0407"
    assert earlier["release_date"] == "2004-07-19"
    assert _official_bps_url(earlier["publication_page_url"])
    assert _official_bps_url(earlier["deep_search_url"])
    assert earlier["methodology_evidence"]["annual_survey_basis_for_2002"] is True
    assert "2002 Annual Construction Establishment Survey" in earlier["methodology_evidence"]["publication_explanation"]
    assert "Quarterly Construction Survey" in earlier["methodology_evidence"]["year_2003_preliminary_estimation"]

    assert later["publication_title"] == "Statistik Tahunan Perusahaan Konstruksi 2002-2006"
    assert later["publication_number"] == "05340.0704"
    assert later["catalog_number"] == "6301003"
    assert later["issn"] == "1978-9149"
    assert later["release_date"] == "2007-05-15"
    assert _official_bps_url(later["publication_page_url"])
    assert _official_bps_url(later["deep_search_url"])
    assert later["methodology_evidence"]["series_years"] == [2002, 2003, 2004, 2005, 2006]
    assert "Annual Construction Establishment Surveys" in later["methodology_evidence"]["annual_survey_series_statement"]
    assert later["methodology_evidence"]["only_explicit_preliminary_year_in_estimation_section"] == 2006
    assert later["table_pages_pdf_index"] == {
        "14_total": 63,
        "15_1_apbn": 80,
        "15_2_apbd": 81,
        "15_3_foreign_loan": 82,
        "15_4_bumn": 83,
        "15_5_other": 84,
    }

    revision_release = revision_manifest["releases"]["construction_statistics_2003"]
    assert "method_note" in revision_release
    assert "preliminary 2003 figures" in revision_release["method_note"]

    values = manifest["values_thousand_rupiah"]
    assert set(map(int, values)) == {2002, 2003}
    revision_values = revision_manifest["values_thousand_rupiah"]

    for year in (2002, 2003):
        year_values = values[str(year)]
        assert set(year_values) == set(MEASURES)
        for measure_id, table_number in MEASURES.items():
            block = year_values[measure_id]
            earlier_value, later_value, pct, ratio = EXPECTED[year][measure_id]
            assert block["earlier"] == earlier_value
            assert block["later"] == later_value
            assert block["delta"] == later_value - earlier_value
            assert Decimal(str(block["delta_percent"])) == pct
            assert Decimal(str(block["later_to_earlier_ratio"])) == ratio
            assert int(revision_values[measure_id]["construction_statistics_2003"][str(year)]) == earlier_value

        reconciliation = manifest["within_release_reconciliation"][str(year)]
        earlier_sum = sum(EXPECTED[year][measure][0] for measure in COMPONENTS)
        later_sum = sum(EXPECTED[year][measure][1] for measure in COMPONENTS)
        earlier_total = EXPECTED[year]["total_construction_completed"][0]
        later_total = EXPECTED[year]["total_construction_completed"][1]
        assert earlier_sum == earlier_total
        assert later_sum == later_total
        assert reconciliation["earlier_component_sum_thousand_rupiah"] == earlier_sum
        assert reconciliation["earlier_reported_total_thousand_rupiah"] == earlier_total
        assert reconciliation["earlier_residual"] == 0
        assert reconciliation["later_component_sum_thousand_rupiah"] == later_sum
        assert reconciliation["later_reported_total_thousand_rupiah"] == later_total
        assert reconciliation["later_residual"] == 0

    findings_2002 = manifest["break_findings"]["year_2002"]
    assert findings_2002["classification"] == "major_release_break_unexplained"
    assert findings_2002["earlier_status"] == "annual_survey_published"
    assert findings_2002["later_status"] == "annual_survey_series_published"
    assert Decimal(str(findings_2002["total_level_shift_percent"])) == Decimal("56.443737")
    assert findings_2002["available_methodology_text_explains_shift"] is False
    assert set(findings_2002["candidate_causes_not_asserted"]) == {
        "rebenchmarking", "reweighting", "coverage expansion", "frame revision", "reprocessing"
    }
    assert "descriptive only" in findings_2002["numerical_pattern_only"]

    findings_2003 = manifest["break_findings"]["year_2003"]
    assert findings_2003["classification"] == "major_release_break_status_transition"
    assert findings_2003["earlier_status"] == "preliminary_quarterly_growth_estimate"
    assert findings_2003["later_status"] == "annual_survey_series_published"
    assert Decimal(str(findings_2003["total_level_shift_percent"])) == Decimal("80.064509")
    assert findings_2003["status_transition_supported_by_source"] is True
    assert findings_2003["mechanical_bridge_or_revision_formula_available"] is False

    gate = manifest["gate"]
    assert gate["retain_both_vintages"] is True
    assert gate["silent_latest_value_overwrite_authorized"] is False
    assert gate["cross_release_longitudinal_bridge_authorized"] is False
    assert gate["single_continuous_1998_2006_trajectory_authorized"] is False
    assert gate["canonical_fiscal_mapping_authorized"] is False
    assert gate["panel_v3_integration_authorized"] is False
    assert gate["deflation_authorized"] is False
    assert gate["interpolation_authorized"] is False
    assert gate["causal_claim_authorized"] is False
    assert gate["release_break_resolution_required_before_longitudinal_use"] is True

    source_boundary = manifest["source_boundary"]
    assert source_boundary["later_pdf_text_layer_verified"] is True
    assert source_boundary["later_pdf_screenshot_attempt_status"].startswith("tool cache miss")
    assert source_boundary["later_pdf_sha256_available_in_repository"] is False
    assert source_boundary["earlier_pdf_sha256_available_in_repository"] is False
    assert source_boundary["allstats_text_treated_as_artifact_sha_equivalent"] is False

    assert len(rows) == 12
    by_key = {(int(row["year"]), row["source_measure_id"]): row for row in rows}
    assert len(by_key) == 12

    for year in (2002, 2003):
        for measure_id, table_number in MEASURES.items():
            row = by_key[(year, measure_id)]
            earlier_value, later_value, pct, ratio = EXPECTED[year][measure_id]
            assert row["source_geography_name"] == "Sumatera Barat"
            assert row["canonical_historical_geography_id"] == "idn.13.h1958"
            assert row["source_table_number"] == table_number
            assert int(row["construction_statistics_2003_value_thousand_rupiah"]) == earlier_value
            assert int(row["construction_statistics_2002_2006_release_value_thousand_rupiah"]) == later_value
            assert int(row["release_delta_thousand_rupiah"]) == later_value - earlier_value
            assert Decimal(row["release_delta_percent"]) == pct
            assert Decimal(row["later_to_earlier_ratio"]) == ratio
            assert row["longitudinal_bridge_authorized"] == "false"
            if year == 2002:
                assert row["earlier_release_status"] == "annual_survey_published"
                assert row["later_release_status"] == "annual_survey_series_published"
                assert row["break_classification"] == "major_release_break_unexplained"
            else:
                assert row["earlier_release_status"] == "preliminary_quarterly_growth_estimate"
                assert row["later_release_status"] == "annual_survey_series_published"
                assert row["break_classification"] == "major_release_break_status_transition"

    return {
        "rows": len(rows),
        "years": 2,
        "measures_per_year": len(MEASURES),
        "year_2002_total_shift_percent": 56.443737,
        "year_2003_total_shift_percent": 80.064509,
        "both_releases_reconcile_exactly": True,
        "year_2002_break_explained": False,
        "year_2003_status_transition_supported": True,
        "cross_release_longitudinal_bridge_authorized": False,
        "single_continuous_1998_2006_trajectory_authorized": False,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
