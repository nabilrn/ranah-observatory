from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import milestone25_djpk_export as export


def workbook(rows: list[tuple[str, str, str, str]]) -> bytes:
    body = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">',
        '<Worksheet ss:Name="Data APBD"><Table>',
        '<Row><Cell><Data ss:Type="String">Akun</Data></Cell><Cell><Data ss:Type="String">Anggaran</Data></Cell><Cell><Data ss:Type="String">Realisasi</Data></Cell><Cell><Data ss:Type="String">Persentase</Data></Cell></Row>',
    ]
    for label, budget, realization, pct in rows:
        body.append(
            '<Row>'
            f'<Cell><Data ss:Type="String"> {label}</Data></Cell>'
            f'<Cell><Data ss:Type="Number">{budget}</Data></Cell>'
            f'<Cell><Data ss:Type="Number">{realization}</Data></Cell>'
            f'<Cell><Data ss:Type="String">{pct}</Data></Cell>'
            '</Row>'
        )
    body.extend(['</Table></Worksheet>', '</Workbook>'])
    return ''.join(body).encode()


def test_same_selector_export_link_is_exact_not_fuzzy() -> None:
    html = b'''<a href="/portal/csv_apbd?type=apbd&amp;periode=12&amp;tahun=2024&amp;provinsi=03&amp;pemda=12">CSV</a>'''
    url = export.find_same_selector_export_url(html, "12", 2024)
    assert url == export.build_export_url("12", 2024)

    wrong = b'''<a href="/portal/csv_apbd?type=apbd&amp;periode=12&amp;tahun=2024&amp;provinsi=03&amp;pemda=11">CSV</a>'''
    try:
        export.find_same_selector_export_url(wrong, "12", 2024)
    except export.M25DJPKExportError:
        pass
    else:
        raise AssertionError("wrong pemda export link must fail closed")


def test_spreadsheetml_exact_values_and_canonical_conversion() -> None:
    rows = export.parse_spreadsheetml(
        workbook([
            ("Pendapatan Daerah", "2520903337942", "2531277365408.8", "100.41"),
            ("PAD", "706838011883", "662552174238.82", "93.73"),
        ])
    )
    by_label = {row["account_label_normalized"]: row for row in rows}
    exact = export.parse_exact_rupiah(by_label["pad"]["realization_rupiah_raw"])
    assert exact == Decimal("662552174238.82")
    assert export.rupiah_to_idr_billion(exact) == Decimal("662.55217423882")
    assert export.html_display_matches_exact(Decimal("662.55"), exact)
    assert not export.html_display_matches_exact(Decimal("662.50"), exact)


def test_identical_exact_duplicate_is_collapsed_but_conflict_is_disambiguated() -> None:
    rows = export.parse_spreadsheetml(
        workbook([
            ("Belanja Modal", "243960000000", "227290000000", "93.17"),
            ("Belanja Modal", "243960000000", "227290000000", "93.17"),
            ("Belanja Lainnya", "56130000000", "204560000000", "364.47"),
            ("Belanja Lainnya", "0", "0", "0"),
        ])
    )
    by_label = {row["account_label_normalized"]: row for row in rows}
    assert by_label["belanja modal"]["duplicate_occurrence_count"] == "2"
    assert by_label["belanja modal"]["duplicate_resolution"] == "identical_exact_values_collapsed"
    assert "belanja lainnya" not in by_label
    assert "belanja lainnya [hierarchy-conflict-1]" in by_label
    assert "belanja lainnya [hierarchy-conflict-2]" in by_label


def test_export_year_and_selector_contracts_are_locked() -> None:
    assert "periode=12" in export.build_export_url("01", 2018)
    assert "provinsi=03" in export.build_export_url("19", 2025)
    for selector, year in [("1", 2024), ("01", 2017), ("01", 2026)]:
        try:
            export.build_export_url(selector, year)
        except export.M25DJPKExportError:
            pass
        else:
            raise AssertionError((selector, year))
