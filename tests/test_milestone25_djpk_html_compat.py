from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import probe_milestone25_djpk_taxonomy as taxonomy
from milestone25_djpk_html_compat import install_djpk_html_compat


def parse_accounts(html: str) -> list[dict[str, str]]:
    install_djpk_html_compat()
    parser = taxonomy.HTMLTableParser()
    parser.feed(html)
    header, rows = taxonomy.find_postur_table(parser.tables)
    return taxonomy.table_to_accounts(header, rows)


def test_djpk_self_closing_tr_is_treated_as_row_close() -> None:
    accounts = parse_accounts(
        """
        <table>
          <thead><tr><th></th><th>Akun</th><th>Anggaran/Pagu</th><th>Realisasi</th><th>%</th></tr></thead>
          <tbody>
            <tr><td></td><td>Pendapatan Daerah</td><td>2.520,90 M</td><td>2.531,28 M</td><td>100.41</td><tr/>
            <tr><td></td><td>PAD</td><td>706,84 M</td><td>662,55 M</td><td>93.73</td><tr/>
            <tr><td></td><td>Belanja Modal</td><td>243,96 M</td><td>227,29 M</td><td>93.17</td><tr/>
          </tbody>
        </table>
        """
    )
    assert [row["account_label"] for row in accounts] == [
        "Pendapatan Daerah",
        "PAD",
        "Belanja Modal",
    ]
    assert [row["realization_raw"] for row in accounts] == [
        "2.531,28 M",
        "662,55 M",
        "227,29 M",
    ]


def test_identical_duplicate_display_values_are_collapsed() -> None:
    accounts = parse_accounts(
        """
        <table><thead><tr><th></th><th>Akun</th><th>Anggaran/Pagu</th><th>Realisasi</th><th>%</th></tr></thead><tbody>
          <tr><td></td><td style="text-indent:2em">Belanja Modal</td><td>243,96 M</td><td>227,29 M</td><td>93.17</td><tr/>
          <tr><td></td><td style="text-indent:4em">Belanja Modal</td><td>243,96 M</td><td>227,29 M</td><td>93.17</td><tr/>
        </tbody></table>
        """
    )
    assert len(accounts) == 1
    assert accounts[0]["account_label_normalized"] == "belanja modal"
    assert accounts[0]["duplicate_occurrence_count"] == "2"
    assert accounts[0]["duplicate_resolution"] == "identical_display_values_collapsed"


def test_nonidentical_duplicate_values_cannot_qualify_under_base_label() -> None:
    accounts = parse_accounts(
        """
        <table><thead><tr><th></th><th>Akun</th><th>Anggaran/Pagu</th><th>Realisasi</th><th>%</th></tr></thead><tbody>
          <tr><td></td><td style="text-indent:2em">Belanja Lainnya</td><td>56,13 M</td><td>204,56 M</td><td>364.47</td><tr/>
          <tr><td></td><td style="text-indent:4em">Belanja Lainnya</td><td>0,00 M</td><td>0,00 M</td><td>0</td><tr/>
        </tbody></table>
        """
    )
    normalized = {row["account_label_normalized"] for row in accounts}
    assert "belanja lainnya" not in normalized
    assert normalized == {
        "belanja lainnya [hierarchy-conflict-1]",
        "belanja lainnya [hierarchy-conflict-2]",
    }
    assert {row["duplicate_resolution"] for row in accounts} == {
        "nonidentical_hierarchy_values_disambiguated"
    }
