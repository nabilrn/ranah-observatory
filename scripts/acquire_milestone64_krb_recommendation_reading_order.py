#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/manifests/milestone64_krb_recommendations_acquisition.json"
OUT = ROOT / "data/processed/bnpb/krb_sumbar_2022_2026/krb-recommendation-reading-order-pages-98-109.txt"
EXPECTED_FIRST_PAGE = 98
EXPECTED_LAST_PAGE = 109


def fetch_bytes(url: str, attempts: int = 5) -> bytes:
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "RanahObservatory/1.0"})
            with urllib.request.urlopen(req, timeout=120) as response:
                payload = response.read()
            if not payload.startswith(b"%PDF"):
                raise RuntimeError("M64 source response is not a PDF")
            return payload
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, RuntimeError) as exc:
            last = exc
            if attempt == attempts:
                break
            time.sleep(min(2 ** (attempt - 1), 8))
    raise RuntimeError(f"M64 reading-order acquisition failed after {attempts} attempts: {last}")


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    source_url = manifest["source"]["source_url"]
    expected_sha = manifest["raw_artifact"]["sha256"]
    payload = fetch_bytes(source_url)
    raw_sha = hashlib.sha256(payload).hexdigest()
    if raw_sha != expected_sha:
        raise RuntimeError(f"M64 upstream PDF checksum changed: expected {expected_sha}, got {raw_sha}")

    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / "krb-sumbar.pdf"
        text_path = Path(tmpdir) / "recommendations-raw.txt"
        pdf_path.write_bytes(payload)
        subprocess.run([
            "pdftotext", "-raw",
            "-f", str(EXPECTED_FIRST_PAGE),
            "-l", str(EXPECTED_LAST_PAGE),
            str(pdf_path), str(text_path),
        ], check=True)
        text = text_path.read_text(encoding="utf-8", errors="replace")

    pages = text.split("\f")
    if pages and not pages[-1].strip():
        pages = pages[:-1]
    expected_count = EXPECTED_LAST_PAGE - EXPECTED_FIRST_PAGE + 1
    if len(pages) != expected_count:
        raise RuntimeError(f"M64 reading-order page count drift: {len(pages)} != {expected_count}")

    parts = []
    for offset, page in enumerate(pages):
        page_number = EXPECTED_FIRST_PAGE + offset
        parts.append(f"===== PDF PAGE {page_number} =====\n{page.strip()}\n")
    OUT.write_text("\n".join(parts), encoding="utf-8")

    manifest["text_extraction"]["reading_order_excerpt"] = {
        "method": "pdftotext -raw",
        "ocr_used": False,
        "pdf_pages_one_based": [EXPECTED_FIRST_PAGE, EXPECTED_LAST_PAGE],
        "path": OUT.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
        "purpose": "Preserve reading order for Chapter 4 recommendation section parsing and include the Chapter 5 boundary; replaces two-column -layout text as the canonical section-parsing input.",
    }
    manifest["qualification_boundary"]["layout_excerpt_authorized_for_section_materialization"] = False
    manifest["qualification_boundary"]["reading_order_excerpt_authorized_for_section_materialization"] = True
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "ok",
        "raw_sha256": raw_sha,
        "pages": [EXPECTED_FIRST_PAGE, EXPECTED_LAST_PAGE],
        "output_sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
