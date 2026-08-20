from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import probe_milestone25_djpk_stage1 as stage1
from milestone25_djpk_html_compat import install_djpk_html_compat


def test_source_verified_jurisdiction_aliases_are_explicit_only() -> None:
    install_djpk_html_compat()
    assert stage1.jurisdiction_matches(
        "POSTUR APBD Kab. Limapuluh Kota Tahun 2024",
        "Kab. Lima Puluh Kota",
    )
    assert stage1.jurisdiction_matches(
        "POSTUR APBD Kota Bukit Tinggi Tahun 2024",
        "Kota Bukittinggi",
    )
    assert not stage1.jurisdiction_matches(
        "POSTUR APBD Kota Bukitttinggi Tahun 2024",
        "Kota Bukittinggi",
    )
    assert not stage1.jurisdiction_matches(
        "POSTUR APBD Kota Bukit Tinggi Tahun 2024",
        "Kota Padang",
    )
