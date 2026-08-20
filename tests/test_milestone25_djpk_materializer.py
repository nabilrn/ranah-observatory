from __future__ import annotations

import importlib.util
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/materialize_milestone25_djpk_exact_panel.py"
sys.path.insert(0, str(ROOT / "scripts"))

spec = importlib.util.spec_from_file_location("m25_materializer", SCRIPT)
assert spec and spec.loader
m25 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m25)


def test_stable_id_is_deterministic_and_domain_separated() -> None:
    a = m25.stable_id("m25obs_", "pad", "idn.13.1371", 2024)
    b = m25.stable_id("m25obs_", "pad", "idn.13.1371", 2024)
    c = m25.stable_id("m25prov_", "pad", "idn.13.1371", 2024)
    assert a == b
    assert a.startswith("m25obs_")
    assert c.startswith("m25prov_")
    assert a != c


def test_materializer_uses_exact_rupiah_conversion_not_rounded_html_display() -> None:
    exact = m25.parse_exact_rupiah("662552174238.82")
    assert exact == Decimal("662552174238.82")
    assert m25.rupiah_to_idr_billion(exact) == Decimal("662.55217423882")


def test_exact_panel_regime_is_dual_representation_current_sumbar_2018_2025() -> None:
    assert m25.REGIME_ID == "sumbar_current_kabkota_djpk_realization_2018_2025_v2"
    assert m25.YEARS == list(range(2018, 2026))


def test_materializer_paths_keep_source_and_outputs_separate() -> None:
    assert m25.RAW_ROOT == ROOT / "data/processed/djpk/public_finance/source"
    assert m25.OBS_OUT == ROOT / "data/processed/djpk/public_finance/djpk-fiscal-canonical-observations.csv"
    assert m25.PROV_OUT == ROOT / "data/processed/djpk/public_finance/djpk-fiscal-provenance.csv"
    assert m25.MANIFEST_OUT == ROOT / "data/processed/djpk/public_finance/djpk-fiscal-panel.manifest.json"
