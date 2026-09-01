#!/usr/bin/env python3
"""Inspect official Kementerian Kehutanan land-cover publications for Sumbar tables.

Downloads current official PDFs from SIGAP, extracts text with pypdf, and
prints only pages relevant to Sumatera Barat / its districts. This is a
qualification probe; raw PDFs and extracted text are not committed.
"""

from __future__ import annotations

import json
import tempfile
import urllib.request
from pathlib import Path

from pypdf import PdfReader

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


def inspect_pdf(pdf_path: Path) -> tuple[int, int, list[dict[str, object]], list[str]]:
    reader = PdfReader(str(pdf_path), strict=False)
    occurrence_count = 0
    matches: list[dict[str, object]] = []
    district_terms: set[str] = set()

    for index, page in enumerate(reader.pages, start=1):
        # Layout mode preserves table columns better when the source PDF has an
        # actual text layer. Fall back to normal extraction for unusual pages.
        try:
            text = page.extract_text(extraction_mode="layout") or ""
        except Exception:
            text = page.extract_text() or ""
        lower = text.casefold()
        occurrence_count += lower.count("sumatera barat")
        hit_terms = [needle for needle in NEEDLES if needle in lower]
        if not hit_terms:
            continue
        district_terms.update(term for term in hit_terms if term != "sumatera barat")
        nonempty = [line.rstrip() for line in text.splitlines() if line.strip()]
        matches.append(
            {
                "pdf_page_index": index,
                "hit_terms": hit_terms,
                "preview_lines": nonempty[:120],
            }
        )

    return len(reader.pages), occurrence_count, matches, sorted(district_terms)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="ranah-klhk-") as tmp:
        root = Path(tmp)
        for key, url in PUBLICATIONS.items():
            pdf_path = root / f"{key}.pdf"
            source = download(url, pdf_path)
            page_count, occurrence_count, matches, district_terms = inspect_pdf(pdf_path)
            print(
                json.dumps(
                    {
                        "publication": key,
                        "source": source,
                        "page_count_extracted": page_count,
                        "sumbar_relevant_page_count": len(matches),
                        "sumatera_barat_occurrences": occurrence_count,
                        "district_needles_found": district_terms,
                    },
                    ensure_ascii=False,
                )
            )
            for item in matches[:16]:
                print(json.dumps({"publication": key, "relevant_page": item}, ensure_ascii=False))


if __name__ == "__main__":
    main()
