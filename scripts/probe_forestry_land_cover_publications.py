#!/usr/bin/env python3
"""Inspect official Kementerian Kehutanan land-cover publications for Sumbar tables.

Downloads current official PDFs from SIGAP, extracts text with Poppler's
pdftotext, and prints only pages relevant to Sumatera Barat / its districts.
This is a qualification probe; raw PDFs and extracted text are not committed.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path

USER_AGENT = "ranah-observatory/1.0 (+https://github.com/nabilrn/ranah-observatory)"
PUBLICATIONS = {
    "land_cover_2022": "https://sigap.kehutanan.go.id/sigap-admin-2026/files/download/rekal-pl-2022.pdf",
    "land_cover_2023": "https://sigap.kehutanan.go.id/sigap-admin-2026/files/download/buku-rekalkulasi-pl-indonesia-tahun-2023.pdf",
}
NEEDLES = (
    "sumatera barat",
    "pesisir selatan",
    "kepulauan mentawai",
    "kota padang",
    "padang pariaman",
    "solok selatan",
    "pasaman barat",
)
MAX_PDF_BYTES = 120 * 1024 * 1024


def download(url: str, path: Path) -> dict[str, object]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/pdf,*/*"})
    with urllib.request.urlopen(request, timeout=180) as response:
        raw = response.read(MAX_PDF_BYTES + 1)
        if len(raw) > MAX_PDF_BYTES:
            raise RuntimeError(f"PDF exceeds {MAX_PDF_BYTES} bytes: {url}")
        content_type = response.headers.get("Content-Type")
        final_url = response.geturl()
    if not raw.startswith(b"%PDF-"):
        raise RuntimeError(f"official publication is not PDF: {url}, prefix={raw[:30]!r}")
    path.write_bytes(raw)
    return {"url": url, "final_url": final_url, "bytes": len(raw), "content_type": content_type}


def extract(pdf_path: Path, txt_path: Path) -> None:
    executable = shutil.which("pdftotext")
    if not executable:
        raise RuntimeError("pdftotext is not installed on the GitHub Actions runner")
    subprocess.run([executable, "-layout", str(pdf_path), str(txt_path)], check=True, timeout=180)


def page_summary(text: str) -> list[dict[str, object]]:
    pages = text.split("\f")
    matches: list[dict[str, object]] = []
    for index, page in enumerate(pages, start=1):
        lower = page.casefold()
        hit_terms = [needle for needle in NEEDLES if needle in lower]
        if not hit_terms:
            continue
        lines = [line.rstrip() for line in page.splitlines()]
        nonempty = [line for line in lines if line.strip()]
        matches.append(
            {
                "pdf_page_index": index,
                "hit_terms": hit_terms,
                "preview_lines": nonempty[:100],
            }
        )
    return matches


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="ranah-klhk-") as tmp:
        root = Path(tmp)
        for key, url in PUBLICATIONS.items():
            pdf_path = root / f"{key}.pdf"
            txt_path = root / f"{key}.txt"
            source = download(url, pdf_path)
            extract(pdf_path, txt_path)
            text = txt_path.read_text(encoding="utf-8", errors="replace")
            pages = text.split("\f")
            matches = page_summary(text)
            print(
                json.dumps(
                    {
                        "publication": key,
                        "source": source,
                        "page_count_extracted": len(pages),
                        "sumbar_relevant_page_count": len(matches),
                        "sumatera_barat_occurrences": text.casefold().count("sumatera barat"),
                        "district_needles_found": sorted({term for item in matches for term in item["hit_terms"] if term != "sumatera barat"}),
                    },
                    ensure_ascii=False,
                )
            )
            for item in matches[:12]:
                print(json.dumps({"publication": key, "relevant_page": item}, ensure_ascii=False))


if __name__ == "__main__":
    main()
