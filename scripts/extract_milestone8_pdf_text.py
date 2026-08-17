#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data/processed/milestone8/source_text"
MANIFEST_PATH = ROOT / "data/manifests/milestone8_pdf_text_extraction.json"

SOURCES = {
    "m8_grdp_pre": {
        "pdf": ROOT / "data/snapshots/bps/milestone8/grdp-2005-2009/source.pdf",
        "text": OUT_DIR / "bps-grdp-2005-2009.txt",
        "slices": [
            (OUT_DIR / "candidate-pages/bps-grdp-2005-2009-pages-35-55.txt", 35, 55),
            (OUT_DIR / "candidate-pages/bps-grdp-2005-2009-pages-84-92.txt", 84, 92),
        ],
        "patterns": ["harga konstan", "kabupaten/kota", "2005", "2009", "produk domestik regional bruto", "pertumbuhan ekonomi"],
    },
    "m8_grdp_post": {
        "pdf": ROOT / "data/snapshots/bps/milestone8/grdp-2009-2013/source.pdf",
        "text": OUT_DIR / "bps-grdp-2009-2013.txt",
        "slices": [(OUT_DIR / "candidate-pages/bps-grdp-2009-2013-pages-410-415.txt", 410, 415)],
        "patterns": ["13.1.2", "harga konstan", "kabupaten/kota", "2009", "2013", "produk domestik regional bruto"],
    },
    "m8_damage_dlna": {
        "pdf": ROOT / "data/snapshots/disaster/milestone8/dlna-2009/source.pdf",
        "text": OUT_DIR / "dlna-2009.txt",
        "slices": [(OUT_DIR / "candidate-pages/dlna-2009-pages-96-103.txt", 96, 103)],
        "patterns": ["housing", "heavily damaged", "moderately damaged", "lightly damaged", "Padang Pariaman", "Pariaman", "pre-disaster", "damage and loss"],
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_tools() -> None:
    missing = [name for name in ("pdftotext", "pdfinfo") if shutil.which(name) is None]
    if missing:
        raise RuntimeError(f"required Poppler tools missing: {', '.join(missing)}")


def page_count(pdf: Path) -> int:
    completed = subprocess.run(["pdfinfo", str(pdf)], check=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
    match = re.search(r"^Pages:\s+(\d+)\s*$", completed.stdout, flags=re.MULTILINE)
    if not match:
        raise RuntimeError(f"could not determine page count for {pdf}")
    return int(match.group(1))


def normalize_line(value: str) -> str:
    return " ".join(value.split())


def pattern_hits(text: str, patterns: list[str], max_hits_per_pattern: int = 12) -> dict[str, Any]:
    pages = text.split("\f")
    result: dict[str, Any] = {}
    for pattern in patterns:
        needle = pattern.casefold()
        hits: list[dict[str, Any]] = []
        for page_index, page in enumerate(pages, start=1):
            for line_index, line in enumerate(page.splitlines(), start=1):
                if needle not in line.casefold():
                    continue
                hits.append({"page": page_index, "line_on_page": line_index, "excerpt": normalize_line(line)[:400]})
                if len(hits) >= max_hits_per_pattern:
                    break
            if len(hits) >= max_hits_per_pattern:
                break
        result[pattern] = {"hit_count_capped": len(hits), "hits": hits}
    return result


def write_slice(raw_text: str, output: Path, start_page: int, end_page: int, expected_pages: int) -> dict[str, Any]:
    if start_page < 1 or end_page > expected_pages or start_page > end_page:
        raise RuntimeError(f"invalid candidate page slice {start_page}-{end_page} for {expected_pages}-page PDF")
    pages = raw_text.split("\f")
    chunks: list[str] = []
    for page_no in range(start_page, end_page + 1):
        chunks.append(f"===== PDF PAGE {page_no} =====\n{pages[page_no - 1].rstrip()}\n")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(chunks), encoding="utf-8")
    return {
        "path": str(output.relative_to(ROOT)),
        "pages": [start_page, end_page],
        "sha256": sha256(output),
    }


def extract_one(source_id: str, spec: dict[str, Any]) -> dict[str, Any]:
    pdf: Path = spec["pdf"]
    text_path: Path = spec["text"]
    if not pdf.exists():
        raise RuntimeError(f"missing frozen PDF for {source_id}: {pdf.relative_to(ROOT)}")
    expected_pages = page_count(pdf)
    text_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["pdftotext", "-layout", "-enc", "UTF-8", str(pdf), str(text_path)], check=True)
    raw_text = text_path.read_text(encoding="utf-8", errors="replace")
    extracted_pages = len(raw_text.split("\f")) - (1 if raw_text.endswith("\f") else 0)
    if extracted_pages != expected_pages:
        raise RuntimeError(f"{source_id}: text page count mismatch pdf={expected_pages} text={extracted_pages}")
    visible_chars = sum(1 for char in raw_text if not char.isspace())
    if visible_chars < max(1000, expected_pages * 100):
        raise RuntimeError(f"{source_id}: extracted text is unexpectedly sparse ({visible_chars} visible chars across {expected_pages} pages); OCR is not silently enabled")
    slice_reports = [write_slice(raw_text, path, start, end, expected_pages) for path, start, end in spec["slices"]]
    return {
        "source_plan_id": source_id,
        "pdf_path": str(pdf.relative_to(ROOT)),
        "pdf_sha256": sha256(pdf),
        "pdf_page_count": expected_pages,
        "text_path": str(text_path.relative_to(ROOT)),
        "text_sha256": sha256(text_path),
        "text_bytes": text_path.stat().st_size,
        "visible_character_count": visible_chars,
        "candidate_slices": slice_reports,
        "extraction_method": "Poppler pdftotext -layout -enc UTF-8",
        "ocr_performed": False,
        "pattern_hits": pattern_hits(raw_text, spec["patterns"]),
    }


def main() -> int:
    require_tools()
    outputs = [extract_one(source_id, spec) for source_id, spec in SOURCES.items()]
    manifest = {
        "schema": "ranah-observatory/milestone8-pdf-text-extraction/v1",
        "criterion": "one focused causal or quasi-causal case study",
        "source_count": len(outputs),
        "sources": outputs,
        "ocr_performed": False,
        "table_values_extracted": False,
        "causal_effect_estimated": False,
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
