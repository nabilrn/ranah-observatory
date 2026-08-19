from __future__ import annotations

import importlib.util
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/probe_milestone25_djpk_stage1.py"
sys.path.insert(0, str(ROOT / "scripts"))

spec = importlib.util.spec_from_file_location("m25_stage1", SCRIPT)
assert spec and spec.loader
m25 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m25)


def test_jurisdiction_normalization_bridges_only_abbreviation_form() -> None:
    assert m25.normalize_jurisdiction("Kab. Lima Puluh Kota") == "kabupaten lima puluh kota"
    assert m25.normalize_jurisdiction("Kabupaten Lima Puluh Kota") == "kabupaten lima puluh kota"
    assert m25.normalize_jurisdiction("Kota Solok") == "kota solok"
    assert m25.jurisdiction_matches("Data APBD Kabupaten Lima Puluh Kota 2024", "Kab. Lima Puluh Kota")
    assert not m25.jurisdiction_matches("Data APBD Kota Solok 2024", "Kab. Solok")


def test_scaled_money_parser_handles_portal_billion_and_trillion_units() -> None:
    assert m25.parse_djpk_money_to_idr_billion("450 M") == Decimal("450")
    assert m25.parse_djpk_money_to_idr_billion("1.25 T") == Decimal("1250.00")
    assert m25.parse_djpk_money_to_idr_billion("1,25 T") == Decimal("1250.00")
    assert m25.parse_djpk_money_to_idr_billion("1.234,56 M") == Decimal("1234.56")
    assert m25.parse_djpk_money_to_idr_billion("1,234.56 M") == Decimal("1234.56")


def test_unscaled_large_rupiah_is_converted_to_billions() -> None:
    assert m25.parse_djpk_money_to_idr_billion("1500000000") == Decimal("1.5")


def test_money_parser_fails_closed_on_missing_or_ambiguous_values() -> None:
    for raw in ["", "-", "N/A", "123"]:
        try:
            m25.parse_djpk_money_to_idr_billion(raw)
        except m25.M25Stage1Error:
            pass
        else:
            raise AssertionError(f"{raw!r} must fail closed")


def test_stage1_url_uses_locked_sumbar_and_december_selectors() -> None:
    url = m25.build_url("12", 2024)
    assert "pemda=12" in url
    assert "periode=12" in url
    assert "provinsi=03" in url
    assert "tahun=2024" in url
