#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from pathlib import Path

from pypdf import PdfReader

OUTDIR = Path("probe-output")
PDFDIR = OUTDIR / "yearbooks"

SOURCES = [
    {
        "label": "sumbar_dalam_angka_2004_2005",
        "title": "Sumatera Barat dalam angka 2004-2005",
        "publication_number": "13000.05.01",
        "page_url": "https://sumbar.bps.go.id/id/publication/2009/01/01/1e30e2b8601d3c946a5f7a0e/sumatera-barat-dalam-angka-2004-2005.html",
        "download_url": "https://web-api.bps.go.id/download.php?f=gpGSjN%2FAA+fIuZBP2arW1mFheUdNYjV4bUpteE1BSjVhbTJMWFNxdTFaTnZmdXBoQkhVRUtDZjV3QmtiRFptcHJXNitwYXlMT2VsS201KzBsK09ZYnEyOGpGRU1zR0pmTnc3UWxYQXFrR2Fnb1NhbjJFV2NNNmp0R0o0Ulg5WXAxYzRqTFRiazFnVXdVcGJweUJ6NExkV0tteFVpenhia0FHZ1VxSk50UDF6WUZQcitrbWRyK2dwS2ZKMlRBdWZQT0FEcGVLYXVreGF0UGEwYmQyWXJMRThUMzVKWSt3eWluNi8yWUZmYUxoMXR1OTJ4NVJ3OU42QnJtVGhYNVY4YkpQeEVObjRiOXk1dWRiMUQ%3D",
    },
    {
        "label": "sumbar_dalam_angka_2006",
        "title": "Sumatera Barat dalam Angka 2006",
        "publication_number": "13000.06.01",
        "page_url": "https://sumbar.bps.go.id/id/publication/2009/01/01/2fc351ad1102d8b47dd9adda/sumatera-barat-dalam-angka-2006.html",
        "download_url": "https://web-api.bps.go.id/download.php?f=iRibQZh%2FRqFK2sbLM91LpnBDSzdhSGdrbVEyVTEwbW5SUkU3Ny9seS9ZTmc0bHdVZmJaanpzNkdBL01sT0dRNC9leDBsOWd6L0k3UDNlRkhKNnlMa29HWmMzYlBFL0VhTUxSaW54N3NpaHBLSjJBWURranZSWCs0V1FLVmQ5WXVNNHU4NUJtUmJwdUJjajduL2ZiVHhlbHdsbGdmZm0yL0x1MEJ2cTh4WDJzZm8zdnJhRmJhcndiQ1VGODNWMmpiK3VDOU5BRUJXdG1hRmxncU8zT285Y0srdE5BODJWMGw5YWh6SzY3c1IyVk9NWTBhcXdWQzYzbS9SbXVSMCtidU83bkFJNTNrWnpSV2ZHM0E%3D",
    },
    {
        "label": "sumbar_dalam_angka_2007",
        "title": "Sumatera Barat dalam Angka 2007",
        "publication_number": "13000.07.01",
        "page_url": "https://sumbar.bps.go.id/id/publication/2009/01/01/bb5cb8d7b5350dbe35024032/sumatera-barat-dalam-angka-2007.html",
        "download_url": "https://web-api.bps.go.id/download.php?f=WUEkVjchMaty8+3T4i45ajFJRzNCT3htRnJ2SXd2bXFQUmxySjFGa1FoSUcwNy9BRkYwU1FJYThrT1VtN09vL1lZY3VtSmsvOVRpS0dxazlicDRCQlRBWlB5MUxDSVdjQWdjSTBYdk1BSzV3QVdkYlZGWnk4U29sK0Vac0U5ZE9PY1NidUl4dWRRSVowV3UrQXU1WG5nUis2U1JjYS9zUFQ5Q3ZJRXdaY0NGUWhSV2FURWxXMkNxMDNtSkwvV2M5T05XUVBhNGVvTzlPY1gzcSt5ekM2dXcrSWUyZFU2cEtMMm92emEyM1BSTi9zSlpJTUFGM2xxMFBzQnFKeENudEU3WDliNllYUE1ibW90ZXE%3D",
    },
]

KEYWORDS = (
    "konstruksi",
    "kualifikasi",
    "perusahaan konstruksi",
    "kode kualifikasi",
    "k1",
    "k2",
    "k3",
    "m1",
    "m2",
)


def fetch_pdf(url: str, path: Path) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Ranah Observatory evidence probe; public BPS artifact)",
            "Accept": "application/pdf,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        data = response.read()
        final_url = response.geturl()
        content_type = response.headers.get("Content-Type", "")
    complete_pdf = data.startswith(b"%PDF-") and b"%%EOF" in data[-8192:]
    if complete_pdf:
        path.write_bytes(data)
    return {
        "http_final_url": final_url,
        "content_type": content_type,
        "byte_count": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "pdf_signature": data.startswith(b"%PDF-"),
        "pdf_eof": b"%%EOF" in data[-8192:],
        "complete_pdf": complete_pdf,
    }


def extract_text(pdf_path: Path, text_path: Path) -> dict[str, object]:
    try:
        reader = PdfReader(str(pdf_path), strict=False)
        page_texts: list[str] = []
        pages_with_text = 0
        for page_number, page in enumerate(reader.pages, start=1):
            extracted = page.extract_text() or ""
            if extracted.strip():
                pages_with_text += 1
            page_texts.append(f"\n===== PDF PAGE {page_number} =====\n{extracted}")
        text = "".join(page_texts)
        text_path.write_text(text, encoding="utf-8")
        return {
            "available": bool(text.strip()),
            "extractor": "pypdf",
            "page_count": len(reader.pages),
            "pages_with_text": pages_with_text,
            "character_count": len(text),
        }
    except Exception as exc:
        return {"available": False, "extractor": "pypdf", "error": f"{type(exc).__name__}: {exc}"}


def normalize(line: str) -> str:
    return " ".join(line.casefold().split())


def contexts(text: str, radius: int = 4) -> list[dict[str, object]]:
    lines = text.splitlines()
    hits: list[dict[str, object]] = []
    seen: set[tuple[int, int]] = set()
    for idx, line in enumerate(lines):
        folded = normalize(line)
        matched = [keyword for keyword in KEYWORDS if keyword in folded]
        if not matched:
            continue
        start = max(0, idx - radius)
        end = min(len(lines), idx + radius + 1)
        key = (start, end)
        if key in seen:
            continue
        seen.add(key)
        block = "\n".join(lines[start:end]).strip()
        hits.append({
            "line_number": idx + 1,
            "matched_keywords": matched,
            "context": block[:6000],
        })
        if len(hits) >= 80:
            break
    return hits


def qualification_signal(text: str) -> dict[str, object]:
    folded = normalize(text)
    categories = {
        token.upper(): bool(re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", folded))
        for token in ("b", "m1", "m2", "k1", "k2", "k3")
    }
    return {
        "qualification_word_present": "kualifikasi" in folded,
        "construction_word_present": "konstruksi" in folded,
        "old_category_tokens_present": categories,
        "all_old_category_tokens_present": all(categories.values()),
        "year_2005_present": bool(re.search(r"(?<!\d)2005(?!\d)", folded)),
        "target_total_2435_present": bool(re.search(r"(?<!\d)2[ .]?435(?!\d)", folded)),
    }


def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    PDFDIR.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": "ranah-observatory/sumbar-yearbooks-construction-qualification-probe/v2",
        "purpose": "Inspect official Sumatera Barat yearbook PDFs for source-native construction qualification evidence around 2005.",
        "sources": [],
        "bounds": {"keyword_context_limit_per_source": 80, "ocr_used": False, "embedded_text_extractor": "pypdf"},
    }

    for source in SOURCES:
        item = {key: value for key, value in source.items() if key != "download_url"}
        pdf_path = PDFDIR / f"{source['label']}.pdf"
        text_path = PDFDIR / f"{source['label']}.txt"
        try:
            item["fetch"] = fetch_pdf(source["download_url"], pdf_path)
        except Exception as exc:
            item["fetch"] = {"complete_pdf": False, "error": f"{type(exc).__name__}: {exc}"}
            report["sources"].append(item)
            continue

        if item["fetch"].get("complete_pdf"):
            item["text_extraction"] = extract_text(pdf_path, text_path)
            if item["text_extraction"].get("available"):
                text = text_path.read_text(encoding="utf-8", errors="replace")
                item["qualification_signal"] = qualification_signal(text)
                item["keyword_contexts"] = contexts(text)
                item["text_character_count"] = len(text)
        report["sources"].append(item)

    out = OUTDIR / "sumbar-yearbooks-construction-qualification-probe.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "sources": len(report["sources"]),
        "complete_pdfs": sum(1 for s in report["sources"] if s.get("fetch", {}).get("complete_pdf")),
        "text_sources": sum(1 for s in report["sources"] if s.get("text_extraction", {}).get("available")),
        "all_old_category_token_sources": [
            s["label"] for s in report["sources"]
            if s.get("qualification_signal", {}).get("all_old_category_tokens_present")
        ],
        "target_total_2435_sources": [
            s["label"] for s in report["sources"]
            if s.get("qualification_signal", {}).get("target_total_2435_present")
        ],
        "output": out.as_posix(),
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
