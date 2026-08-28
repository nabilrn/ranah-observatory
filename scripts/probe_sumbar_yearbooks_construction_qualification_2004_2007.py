#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

from pypdf import PdfReader

OUTDIR = Path("probe-output")
PDFDIR = OUTDIR / "yearbooks"
SOURCE = {
    "label": "sumbar_dalam_angka_2004_2005",
    "title": "Sumatera Barat dalam angka 2004-2005",
    "publication_number": "13000.05.01",
    "page_url": "https://sumbar.bps.go.id/id/publication/2009/01/01/1e30e2b8601d3c946a5f7a0e/sumatera-barat-dalam-angka-2004-2005.html",
    "download_url": "https://web-api.bps.go.id/download.php?f=gpGSjN%2FAA+fIuZBP2arW1mFheUdNYjV4bUpteE1BSjVhbTJMWFNxdTFaTnZmdXBoQkhVRUtDZjV3QmtiRFptcHJXNitwYXlMT2VsS201KzBsK09ZYnEyOGpGRU1zR0pmTnc3UWxYQXFrR2Fnb1NhbjJFV2NNNmp0R0o0Ulg5WXAxYzRqTFRiazFnVXdVcGJweUJ6NExkV0tteFVpenhia0FHZ1VxSk50UDF6WUZQcitrbWRyK2dwS2ZKMlRBdWZQT0FEcGVLYXVreGF0UGEwYmQyWXJMRThUMzVKWSt3eWluNi8yWUZmYUxoMXR1OTJ4NVJ3OU42QnJtVGhYNVY4YkpQeEVObjRiOXk1dWRiMUQ%3D",
}
KEYWORDS = ("konstruksi", "kualifikasi", "perusahaan konstruksi", "kode kualifikasi")
TARGET_PATTERNS = (
    ("2435_compact", re.compile(r"(?<!\d)2435(?!\d)")),
    ("2435_spaced_or_dotted", re.compile(r"(?<!\d)2[ .]435(?!\d)")),
)


def fetch_pdf(url: str, path: Path) -> dict[str, object]:
    path.unlink(missing_ok=True)
    proc = subprocess.run(
        [
            "curl", "--location", "--http1.1", "--tlsv1.2", "--retry", "1",
            "--retry-delay", "1", "--retry-all-errors", "--connect-timeout", "30",
            "--max-time", "90", "--silent", "--show-error",
            "--user-agent", "Mozilla/5.0 (Ranah Observatory evidence probe; public BPS artifact)",
            "--header", "Accept: application/pdf,*/*;q=0.8", "--output", str(path),
            "--write-out", "%{url_effective}\n%{http_code}\n%{content_type}\n", url,
        ],
        text=True, capture_output=True, timeout=110, check=False,
    )
    lines = proc.stdout.splitlines()
    data = path.read_bytes() if path.exists() else b""
    complete_pdf = data.startswith(b"%PDF-") and b"%%EOF" in data[-8192:]
    if not complete_pdf:
        path.unlink(missing_ok=True)
    return {
        "transport": "curl_http1_1_tls1_2_verified",
        "curl_returncode": proc.returncode,
        "curl_stderr": proc.stderr[-1200:],
        "http_status": int(lines[-2]) if len(lines) >= 2 and lines[-2].isdigit() else None,
        "content_type": lines[-1] if lines else "",
        "byte_count": len(data),
        "sha256": hashlib.sha256(data).hexdigest() if data else None,
        "pdf_signature": data.startswith(b"%PDF-"),
        "pdf_eof": b"%%EOF" in data[-8192:] if data else False,
        "complete_pdf": complete_pdf,
        "tls_verification_disabled": False,
    }


def extract_pages(pdf_path: Path) -> tuple[list[str], dict[str, object]]:
    reader = PdfReader(str(pdf_path), strict=False)
    pages: list[str] = []
    pages_with_text = 0
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)
        if text.strip():
            pages_with_text += 1
    return pages, {
        "extractor": "pypdf",
        "page_count": len(pages),
        "pages_with_text": pages_with_text,
        "character_count": sum(len(page) for page in pages),
        "available": pages_with_text > 0,
    }


def bounded_page_contexts(pages: list[str]) -> dict[str, list[dict[str, object]]]:
    result: dict[str, list[dict[str, object]]] = {key: [] for key in (*KEYWORDS, "2435")}
    for page_no, text in enumerate(pages, start=1):
        folded = " ".join(text.casefold().split())
        for keyword in KEYWORDS:
            start = 0
            while len(result[keyword]) < 20:
                pos = folded.find(keyword, start)
                if pos < 0:
                    break
                result[keyword].append({
                    "pdf_page": page_no,
                    "context": folded[max(0, pos - 550): pos + 1500],
                })
                start = pos + len(keyword)
        for label, pattern in TARGET_PATTERNS:
            for match in pattern.finditer(folded):
                if len(result["2435"]) >= 20:
                    break
                result["2435"].append({
                    "pdf_page": page_no,
                    "pattern": label,
                    "context": folded[max(0, match.start() - 700): match.end() + 1800],
                })
    return result


def old_category_table_signal(pages: list[str]) -> list[dict[str, object]]:
    hits = []
    category_patterns = [re.compile(rf"(?<![a-z0-9]){token.casefold()}(?![a-z0-9])") for token in ("m1", "m2", "k1", "k2", "k3")]
    for page_no, text in enumerate(pages, start=1):
        folded = " ".join(text.casefold().split())
        found = [bool(pattern.search(folded)) for pattern in category_patterns]
        if sum(found) >= 3 and "konstruksi" in folded:
            hits.append({"pdf_page": page_no, "category_token_count": sum(found), "context": folded[:5000]})
    return hits[:20]


def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    PDFDIR.mkdir(parents=True, exist_ok=True)
    pdf_path = PDFDIR / "sumbar_dalam_angka_2004_2005.pdf"
    report = {
        "schema": "ranah-observatory/sumbar-yearbook-2004-2005-targeted-context-probe/v1",
        "purpose": "Determine whether the 2,435 signal and qualification terminology in the acquired official Sumatera Barat 2004-2005 yearbook are construction-qualification evidence.",
        "ocr_used": False,
        "source": {key: value for key, value in SOURCE.items() if key != "download_url"},
    }
    report["fetch"] = fetch_pdf(SOURCE["download_url"], pdf_path)
    if report["fetch"]["complete_pdf"]:
        pages, extraction = extract_pages(pdf_path)
        report["text_extraction"] = extraction
        report["contexts"] = bounded_page_contexts(pages)
        report["construction_old_category_table_candidates"] = old_category_table_signal(pages)
        report["finding_summary"] = {
            "target_2435_occurrence_count": len(report["contexts"]["2435"]),
            "construction_context_count": len(report["contexts"]["konstruksi"]),
            "qualification_context_count": len(report["contexts"]["kualifikasi"]),
            "construction_old_category_table_candidate_count": len(report["construction_old_category_table_candidates"]),
        }
    out = OUTDIR / "sumbar-yearbook-2004-2005-targeted-context-probe.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report.get("finding_summary", {"complete_pdf": False}), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
