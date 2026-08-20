from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from milestone25_djpk_period_semantics import (
    M25DJPKPeriodSemanticsError,
    annual_final_realization_matches,
    classify_annual_final_realization,
)


def test_december_is_calendar_year_end_semantics() -> None:
    text = "Keterangan: Data APBD Perubahan, realisasi APBD s.d Desember 2024"
    assert classify_annual_final_realization(text, 2024) == "calendar_year_end_december"
    assert annual_final_realization_matches(text, 2024)


def test_audited_is_final_accountability_semantics_only_for_same_year() -> None:
    text = "Keterangan: Data APBD Murni, realisasi APBD s.d Audited 2021"
    assert classify_annual_final_realization(text, 2021) == "final_accountability_audited"
    assert classify_annual_final_realization(text, 2022) is None


def test_perda_is_final_accountability_semantics_only_for_same_year() -> None:
    text = "Keterangan: Data APBD Murni/Perubahan, realisasi APBD s.d Perda 2021"
    assert classify_annual_final_realization(text, 2021) == "final_accountability_perda"
    assert classify_annual_final_realization(text, 2020) is None


def test_intermediate_months_and_nonfinal_statuses_fail_closed() -> None:
    for text in (
        "realisasi APBD s.d November 2021",
        "realisasi APBD s.d Oktober 2021",
        "realisasi APBD s.d Unaudited 2021",
        "realisasi APBD 2021",
    ):
        assert classify_annual_final_realization(text, 2021) is None
        assert not annual_final_realization_matches(text, 2021)


def test_whitespace_and_punctuation_variants_are_tolerated() -> None:
    assert classify_annual_final_realization("Realisasi   APBD s. d. Perda 2022", 2022) == "final_accountability_perda"
    assert classify_annual_final_realization("Realisasi APBD s.d. Audited 2022", 2022) == "final_accountability_audited"


def test_year_regime_remains_locked() -> None:
    for year in (2017, 2026):
        try:
            classify_annual_final_realization("realisasi APBD s.d Desember", year)
        except M25DJPKPeriodSemanticsError:
            pass
        else:
            raise AssertionError(year)
