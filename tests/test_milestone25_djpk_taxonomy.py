from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/probe_milestone25_djpk_taxonomy.py"
GATE = ROOT / "data/manifests/milestone25_design_gate.json"
CROSSWALK = ROOT / "data/registries/djpk_sumbar_pemda.csv"
sys.path.insert(0, str(ROOT / "scripts"))

spec = importlib.util.spec_from_file_location("m25_probe", SCRIPT)
assert spec and spec.loader
m25 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m25)


def test_design_gate_is_locked_before_taxonomy_probe() -> None:
    gate = m25.validate_gate(GATE)
    assert gate["design_locked_before_taxonomy_probe"] is True
    assert gate["djpk_province_selector"] == "03"
    assert gate["annual_realization_period_selector"] == "12"
    assert gate["taxonomy_reference_pemda_selector"] == "12"
    assert gate["target_year_count"] == 8
    assert gate["stage0_page_count"] == 8
    assert gate["stage1_jurisdiction_year_count"] == 152
    assert gate["conceptual_account_family_count"] == 5
    assert gate["cross_geography_values_inspected_before_taxonomy_lock"] is False
    assert gate["posthoc_account_family_search_authorized"] is False
    assert gate["derived_ratio_creation_authorized_before_component_qualification"] is False
    assert gate["statistical_model_fit_authorized"] is False


def test_crosswalk_maps_exact_19_current_sumbar_geographies() -> None:
    rows = m25.validate_crosswalk(CROSSWALK)
    assert len(rows) == 19
    assert {row["djpk_pemda_selector"] for row in rows} == {f"{value:02d}" for value in range(1, 20)}
    assert len({row["geography_id"] for row in rows}) == 19
    padang = next(row for row in rows if row["geography_id"] == "idn.13.1371")
    assert padang["djpk_pemda_selector"] == "12"
    assert padang["djpk_source_name"] == "Kota Padang"
    assert next(row for row in rows if row["djpk_pemda_selector"] == "16")["geography_id"] == "idn.13.1377"
    assert next(row for row in rows if row["djpk_pemda_selector"] == "17")["geography_id"] == "idn.13.1312"
    assert next(row for row in rows if row["djpk_pemda_selector"] == "18")["geography_id"] == "idn.13.1311"
    assert next(row for row in rows if row["djpk_pemda_selector"] == "19")["geography_id"] == "idn.13.1310"


def test_html_parser_extracts_postur_rows_without_values_semantic_inference() -> None:
    html = """
    <html><head><title>APBD Kota Padang</title></head><body>
    <p>Keterangan: Data APBD Murni 2020. Realisasi APBD s.d. Desember TA 2020</p>
    <table><tr><th>Akun</th><th>Anggaran/Pagu</th><th>Realisasi</th><th>%</th></tr>
    <tr><td>Pendapatan</td><td>2.000 M</td><td>1.900 M</td><td>95%</td></tr>
    <tr><td>PAD</td><td>500 M</td><td>450 M</td><td>90%</td></tr>
    <tr><td>Belanja Modal</td><td>300 M</td><td>250 M</td><td>83%</td></tr>
    </table></body></html>
    """
    parser = m25.HTMLTableParser()
    parser.feed(html)
    header, source_rows = m25.find_postur_table(parser.tables)
    accounts = m25.table_to_accounts(header, source_rows)
    assert parser.title == "APBD Kota Padang"
    assert "Realisasi APBD s.d. Desember TA 2020" in parser.all_text
    assert [row["account_label"] for row in accounts] == ["Pendapatan", "PAD", "Belanja Modal"]
    assert accounts[1]["realization_raw"] == "450 M"
    assert accounts[1]["account_label_normalized"] == "pad"


def test_postur_parser_rejects_duplicate_normalized_account_labels() -> None:
    header = ["Akun", "Anggaran/Pagu", "Realisasi", "%"]
    source_rows = [
        ["PAD", "1", "1", "100"],
        [" PAD ", "2", "2", "100"],
    ]
    try:
        m25.table_to_accounts(header, source_rows)
    except ValueError as exc:
        assert "duplicate normalized" in str(exc)
    else:
        raise AssertionError("duplicate account labels must fail closed")


def test_conceptual_classification_separates_exact_bridge_and_held() -> None:
    labels_by_year: dict[int, set[str]] = {}
    for year in range(2018, 2026):
        labels = {"pad", "belanja modal"}
        labels.add("pendapatan" if year <= 2020 else "pendapatan daerah")
        labels.add("belanja" if year <= 2020 else "belanja daerah")
        labels.add("dana perimbangan" if year <= 2020 else "pendapatan transfer pemerintah pusat")
        labels_by_year[year] = labels
    results = {row["conceptual_family"]: row for row in m25.classify_conceptual_families(labels_by_year)}
    assert results["own_source_revenue_pad"]["status"] == "exact_label_qualified"
    assert results["capital_expenditure"]["status"] == "exact_label_qualified"
    assert results["total_revenue"]["status"] == "explicit_bridge_candidate"
    assert results["total_expenditure"]["status"] == "explicit_bridge_candidate"
    assert results["central_transfer_revenue"]["status"] == "held_semantic_bridge_review"


def test_url_contract_uses_locked_reference_selectors() -> None:
    url = m25.build_url(2020)
    assert "pemda=12" in url
    assert "periode=12" in url
    assert "provinsi=03" in url
    assert "tahun=2020" in url
