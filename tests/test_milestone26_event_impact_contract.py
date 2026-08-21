from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SCRIPT = ROOT / "scripts/probe_milestone26_event_impact_retrieval.py"

spec = importlib.util.spec_from_file_location("m26_event", SCRIPT)
assert spec and spec.loader
m26 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m26)


def test_event_impact_contract_is_retrieval_only() -> None:
    contract = m26.load_contract()
    assert contract["target_regime"]["year"] == 2024
    assert contract["target_regime"]["event_types"] == ["BANJIR", "TANAH LONGSOR"]
    assert contract["stage2a_retrieval_qualification"]["impact_aggregation_authorized"] is False
    assert contract["event_identity_rule"]["automatic_duplicate_collapse_authorized"] is False
    assert contract["missing_value_semantics"]["blank_cell"].startswith("not_reported_or_missing")
    assert contract["risk_synthesis_authorized"] is False


def test_frozen_surface_matches_post_form_and_exact_table_contract() -> None:
    contract = m26.load_contract()
    parser = m26.parse_html(m26.FROZEN_SURFACE.read_bytes())
    assert parser.form_action == "/databencana/tabel/pencarian.php"
    assert parser.form_method == "post"
    assert {"tgl_awal", "tgl_akhir", "submit"}.issubset(parser.input_names)
    assert "s_kejadian" in parser.select_names
    assert {"BANJIR", "TANAH LONGSOR"}.issubset(set(parser.select_options["s_kejadian"]))
    assert parser.headers == contract["expected_table_columns"]
    assert len(parser.headers) == 16
    assert parser.rows
    assert all(len(row) == 16 for row in parser.rows)


def test_blank_zero_and_positive_impacts_remain_distinct() -> None:
    assert m26.impact_cell_state("") == ("not_reported_or_missing", None)
    assert m26.impact_cell_state(" 0 ") == ("explicit_reported_zero", 0)
    assert m26.impact_cell_state("12") == ("reported_count", 12)


def test_noninteger_impact_fails_closed() -> None:
    for value in ("-1", "1.5", "unknown", "-"):
        try:
            m26.impact_cell_state(value)
        except m26.EventImpactContractError:
            pass
        else:
            raise AssertionError(f"impact value should fail closed: {value!r}")


def test_fallback_fingerprint_is_stable_but_not_called_event_id() -> None:
    contract = m26.load_contract()
    headers = contract["expected_table_columns"]
    row = [""] * len(headers)
    values = {
        "ID Kabupaten": "1371",
        "Tanggal Kejadian": "2024-01-02",
        "Kejadian": "BANJIR",
        "Lokasi": "Kec. X",
        "Meninggal": "",
        "Hilang": "0",
        "Terluka": "2",
        "Rumah Rusak": "0",
        "Rumah Terendam": "10",
        "Fasum Rusak": "",
    }
    for key, value in values.items():
        row[headers.index(key)] = value
    first = m26.source_row_fingerprint(headers, row, contract)
    second = m26.source_row_fingerprint(headers, row, contract)
    assert first == second
    assert len(first) == 64
    assert contract["event_identity_rule"]["fallback_fingerprint_role"].startswith("stable source-row identity only")
