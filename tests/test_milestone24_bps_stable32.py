from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/probe_milestone24_bps_stable32.py"
GATE = ROOT / "data/manifests/milestone24_design_gate.json"
SERIES = ROOT / "data/registries/bps_comparative_panel_series.csv"
GEOS = ROOT / "data/registries/geographies.csv"

spec = importlib.util.spec_from_file_location("m24_probe", SCRIPT)
assert spec and spec.loader
m24 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m24)


def test_design_gate_is_locked_before_live_probe() -> None:
    gate = m24.validate_gate(GATE)
    assert gate["design_locked_before_probe"] is True
    assert gate["target_start_year"] == 2018
    assert gate["target_end_year"] == 2025
    assert gate["stable_geography_count"] == 32
    assert gate["candidate_count"] == 6
    assert gate["probe_candidate_year_count"] == 48
    assert gate["exact_selector_reuse_required"] is True
    assert gate["selector_search_after_probe_authorized"] is False
    assert gate["imputation_authorized"] is False
    assert gate["geographic_backcasting_authorized"] is False
    assert gate["province_district_model_pooling_authorized"] is False
    assert gate["credential_persistence_authorized"] is False


def test_stable32_geography_contract_excludes_exact_current_papua_codes() -> None:
    stable, excluded = m24.current_provinces(GEOS)
    assert len(stable) == 32
    assert len(excluded) == 6
    assert set(excluded) == {"9100", "9200", "9400", "9500", "9600", "9700"}
    assert set(stable).isdisjoint(excluded)
    assert "1300" in stable
    assert stable["1300"]["geography_id"] == "idn.13"


def test_reuses_exact_prequalified_six_series_contracts() -> None:
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    contracts = m24.load_contracts(SERIES, gate)
    assert [row["series_id"] for row in contracts] == gate["candidate_series_ids"]
    assert [row["indicator_id"] for row in contracts] == [
        "poverty_rate",
        "gini_ratio",
        "unemployment_rate",
        "underemployment_rate",
        "real_grdp_per_capita",
        "neet_rate",
    ]
    assert all(row["qualification_status"] == "qualified_current38" for row in contracts)


def test_exact_selector_matching_cannot_silently_change_reference_semantics() -> None:
    contract = {
        "selected_turvar_id": "434",
        "selected_turvar_label": "Jumlah",
        "selected_turth_id": "61",
        "selected_turth_label": "Semester 1 (Maret)",
    }
    exact = {
        "bps_turvar_id": "434",
        "bps_turvar_label": "Jumlah",
        "bps_turth_id": "61",
        "bps_turth_label": "Semester 1 (Maret)",
    }
    assert m24.exact_selector(exact, contract)
    changed_month = {**exact, "bps_turth_id": "62", "bps_turth_label": "Semester 2 (September)"}
    changed_label = {**exact, "bps_turvar_label": "Perkotaan"}
    assert not m24.exact_selector(changed_month, contract)
    assert not m24.exact_selector(changed_label, contract)


def test_value_transform_is_deterministic_and_rejects_unknown_transform() -> None:
    assert m24.transform_value("12.5", "identity") == 12.5
    assert m24.transform_value("12500", "divide_1000") == 12.5
    try:
        m24.transform_value("1", "made_up")
    except ValueError as exc:
        assert "unsupported transform" in str(exc)
    else:
        raise AssertionError("unknown transform must fail closed")


def test_period_map_rejects_ambiguous_same_label() -> None:
    rows = [
        {"th": "2024", "th_id": "1"},
        {"th": "2024", "th_id": "2"},
    ]
    try:
        m24.period_map(rows)
    except ValueError as exc:
        assert "ambiguous period label" in str(exc)
    else:
        raise AssertionError("ambiguous BPS period metadata must fail closed")
