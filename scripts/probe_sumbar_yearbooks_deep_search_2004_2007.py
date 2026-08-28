#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import html
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import urlencode

OUTDIR = Path("probe-output")
BASE = "https://searchengine.web.bps.go.id/deep"

SOURCES = [
    ("sumbar_dalam_angka_2004_2005", "1e30e2b8601d3c946a5f7a0e", "13000.05.01"),
    ("sumbar_dalam_angka_2006", "2fc351ad1102d8b47dd9adda", "13000.06.01"),
    ("sumbar_dalam_angka_2007", "bb5cb8d7b5350dbe35024032", "13000.07.01"),
]
QUERIES = [
    "konstruksi",
    "kualifikasi",
    "perusahaan konstruksi",
    "M1 M2 K1 K2 K3",
    "2005 konstruksi",
]


def strip_html(raw: str) -> str:
    raw = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    return " ".join(html.unescape(raw).split())


def fetch(publication_id: str, query: str) -> dict[str, object]:
    url = BASE + "?" + urlencode({
        "content": "publication",
        "id": publication_id,
        "mfd": "1300",
        "page": "1",
        "q": query,
    })
    proc = subprocess.run(
        [
            "curl", "--location", "--http1.1", "--retry", "1", "--retry-all-errors",
            "--connect-timeout", "15", "--max-time", "45", "--silent", "--show-error",
            "--user-agent", "Mozilla/5.0 (Ranah Observatory evidence probe; public BPS Deep Search)",
            "--write-out", "\n__META__%{http_code}|%{content_type}|%{url_effective}",
            url,
        ],
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    body, _, meta = proc.stdout.rpartition("\n__META__")
    fields = meta.split("|", 2) if meta else []
    text = strip_html(body)
    relevant = []
    folded = text.casefold()
    for token in ("konstruksi", "kualifikasi", "m1", "m2", "k1", "k2", "k3", "2.435", "2435"):
        pos = folded.find(token)
        if pos >= 0:
            relevant.append({"token": token, "context": text[max(0, pos - 700): pos + 2200]})
    return {
        "query": query,
        "curl_returncode": proc.returncode,
        "http_status": int(fields[0]) if fields and fields[0].isdigit() else None,
        "content_type": fields[1] if len(fields) > 1 else "",
        "final_host_is_bps_search": "searchengine.web.bps.go.id" in (fields[2] if len(fields) > 2 else ""),
        "body_sha256": hashlib.sha256(body.encode("utf-8", errors="replace")).hexdigest(),
        "text_character_count": len(text),
        "no_result_marker": bool(re.search(r"Menampilkan\s+0\s+publikasi|0 publikasi", text, re.I)),
        "result_count_phrases": re.findall(r"Menampilkan.{0,100}", text, flags=re.I)[:5],
        "relevant_contexts": relevant[:12],
        "stderr": proc.stderr[-800:],
    }


def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": "ranah-observatory/sumbar-yearbooks-deep-search-probe/v1",
        "purpose": "Use the official BPS Cari Kata Kunci/Deep Search route for three verified Sumatera Barat yearbooks to find construction qualification evidence around 2005.",
        "official_route_only": True,
        "ocr_used": False,
        "sources": [],
    }
    for label, publication_id, publication_number in SOURCES:
        source = {
            "label": label,
            "publication_id": publication_id,
            "publication_number": publication_number,
            "queries": [],
        }
        for query in QUERIES:
            source["queries"].append(fetch(publication_id, query))
        report["sources"].append(source)

    path = OUTDIR / "sumbar-yearbooks-deep-search-probe.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "sources": len(report["sources"]),
        "successful_http_queries": sum(
            1 for source in report["sources"] for item in source["queries"] if item["http_status"] == 200
        ),
        "queries_with_kualifikasi_context": [
            f"{source['label']}::{item['query']}"
            for source in report["sources"] for item in source["queries"]
            if any(ctx["token"] == "kualifikasi" for ctx in item["relevant_contexts"])
        ],
        "queries_with_target_total_context": [
            f"{source['label']}::{item['query']}"
            for source in report["sources"] for item in source["queries"]
            if any(ctx["token"] in {"2.435", "2435"} for ctx in item["relevant_contexts"])
        ],
        "output": path.as_posix(),
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
