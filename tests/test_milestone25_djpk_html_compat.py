from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from milestone25_djpk_html_compat import install_djpk_html_compat
from probe_milestone25_djpk_taxonomy import HTMLTableParser, find_postur_table, table_to_accounts


def test_djpk_self_closing_tr_is_treated_as_row_close() -> None:
    install_djpk_html_compat()
    html = """
    <table>
      <thead><tr><th></th><th>Akun</th><th>Anggaran/Pagu</th><th>Realisasi</th><th>%</th></tr></thead>
      <tbody>
        <tr><td></td><td>Pendapatan Daerah</td><td>2.520,90 M</td><td>2.531,28 M</td><td>100.41</td><tr/>
        <tr><td></td><td>PAD</td><td>706,84 M</td><td>662,55 M</td><td>93.73</td><tr/>
        <tr><td></td><td>Belanja Modal</td><td>243,96 M</td><td>227,29 M</td><td>93.17</td><tr/>
      </tbody>
    </table>
    """
    parser = HTMLTableParser()
    parser.feed(html)
    header, rows = find_postur_table(parser.tables)
    accounts = table_to_accounts(header, rows)
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
