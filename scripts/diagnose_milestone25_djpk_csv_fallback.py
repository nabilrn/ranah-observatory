#!/usr/bin/env python3
from __future__ import annotations

import csv
import io
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from milestone25_djpk_html_compat import install_djpk_html_compat
install_djpk_html_compat()

import probe_milestone25_djpk_stage1 as stage1

CSV_BASE = "https://djpk.kemenkeu.go.id/portal/csv_apbd"
LOCKED = ("pendapatan daerah", "pad", "belanja daerah", "belanja modal")


def csv_url(pemda: str, year: int) -> str:
    return CSV_BASE + "?" + urllib.parse.urlencode({
        "type": "apbd",
        "periode": "12",
        "tahun": str(year),
        "provinsi": "03",
        "pemda": pemda,
    })


def fetch(url: str) -> tuple[int, str, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": "ranah-observatory/0.1", "Accept": "text/csv,*/*"})
    with urllib.request.urlopen(req, timeout=45) as response:
        return int(response.status), str(response.headers.get("Content-Type", "")), response.read()


def parse_csv(body: bytes) -> dict[str, object]:
    text = body.decode("utf-8-sig", errors="replace")
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ","
    rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))
    normalized = [[stage1.normalize_space(cell) for cell in row] for row in rows]
    return {
        "text": text,
        "delimiter": delimiter,
        "rows": normalized,
        "row_count": len(normalized),
        "max_columns": max((len(row) for row in normalized), default=0),
    }


def main() -> int:
    out = []
    for pemda, year in (("01", 2018), ("01", 2024), ("12", 2018), ("12", 2024)):
        url = csv_url(pemda, year)
        status, content_type, body = fetch(url)
        parsed = parse_csv(body)
        text = str(parsed["text"])
        html_url = stage1.build_url(pemda, year)
        h_status, h_body, h_final = stage1.fetch_url(html_url)
        html_accounts = None
        html_error = None
        try:
            parser = stage1.HTMLTableParser()
            parser.feed(h_body.decode("utf-8", errors="replace"))
            header, table_rows = stage1.find_postur_table(parser.tables)
            accounts = stage1.table_to_accounts(header, table_rows)
            html_accounts = {
                row["account_label_normalized"]: row["realization_raw"]
                for row in accounts
                if row["account_label_normalized"] in LOCKED
            }
        except Exception as exc:  # diagnostic only
            html_error = f"{type(exc).__name__}: {exc}"
        out.append({
            "pemda": pemda,
            "year": year,
            "csv_url": url,
            "csv_status": status,
            "csv_content_type": content_type,
            "csv_bytes": len(body),
            "csv_delimiter": parsed["delimiter"],
            "csv_row_count": parsed["row_count"],
            "csv_max_columns": parsed["max_columns"],
            "csv_prefix": text[:2500],
            "html_status": h_status,
            "html_final_url": h_final,
            "html_accounts": html_accounts,
            "html_error": html_error,
        })
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
