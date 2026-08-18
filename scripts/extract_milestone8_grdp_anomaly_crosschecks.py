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
OUT = ROOT / "data/processed/milestone8/anomaly_crosschecks"
MANIFEST = ROOT / "data/manifests/milestone8_grdp_anomaly_text.json"

SOURCES = {
    "m8_bukittinggi_grdp_crosscheck": {
        "pdf": ROOT / "data/raw/milestone8/crosschecks/bukittinggi-grdp-2011-2013/source.pdf",
        "checksum": ROOT / "data/snapshots/bps/milestone8/crosschecks/bukittinggi-grdp-2011-2013/source.pdf.sha256",
        "text": OUT / "bukittinggi-grdp-2011-2013.txt",
        "terms": [
            "1.039.252",
            "1.093.252",
            "1.163.140",
            "1.163.126",
            "Produk Domestik Regional Bruto Kota Bukittinggi Atas Dasar Harga Konstan 2000",
            "Jumlah",
        ],
    },
    "m8_solok_selatan_grdp_crosscheck": {
        "pdf": ROOT / "data/raw/milestone8/crosschecks/solok-selatan-dalam-angka-2013/source.pdf",
        "checksum": ROOT / "data/snapshots/bps/milestone8/crosschecks/solok-selatan-dalam-angka-2013/source.pdf.sha256",
        "text": OUT / "solok-selatan-dalam-angka-2013.txt",
        "terms": [
            "694.409",
            "695.409",
            "694.917",
            "740.174",
            "739.663",
            "Produk Domestik Regional Bruto",
            "harga konstan",
        ],
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_source(spec: dict[str, Any]) -> None:
    pdf: Path = spec["pdf"]
    checksum: Path = spec["checksum"]
    if not pdf.exists() or not checksum.exists():
        raise RuntimeError(f"missing raw/checksum for {pdf}")
    expected = checksum.read_text(encoding="utf-8").split()[0]
    actual = sha256(pdf)
    if actual != expected:
        raise RuntimeError(f"crosscheck source hash drift for {pdf.name}: expected={expected} actual={actual}")


def page_count(pdf: Path) -> int:
    completed = subprocess.run(["pdfinfo", str(pdf)], check=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
    match = re.search(r"^Pages:\s+(\d+)\s*$", completed.stdout, flags=re.MULTILINE)
    if not match:
        raise RuntimeError(f"could not read PDF page count for {pdf}")
    return int(match.group(1))


def hits(text: str, term: str) -> list[dict[str, Any]]:
    pages = text.split("\f")
    output: list[dict[str, Any]] = []
    needle = term.casefold()
    for page_no, page in enumerate(pages, start=1):
        lines = page.splitlines()
        for line_no, line in enumerate(lines, start=1):
            if needle not in line.casefold():
                continue
            start = max(0, line_no - 3)
            end = min(len(lines), line_no + 2)
            context = " ".join(" ".join(lines[start:end]).split())[:1200]
            output.append({"page": page_no, "line": line_no, "context": context})
            if len(output) >= 30:
                return output
    return output


def write_candidate_pages(source_id: str, raw_text: str, page_numbers: set[int], max_pages: int) -> list[dict[str, Any]]:
    pages = raw_text.split("\f")
    if pages and not pages[-1].strip():
        pages = pages[:-1]
    expanded: set[int] = set()
    for page_no in page_numbers:
        expanded.update(number for number in (page_no - 1, page_no, page_no + 1) if 1 <= number <= len(pages))
    selected = sorted(expanded)[:max_pages]
    if not selected:
        return []
    path = OUT / f"{source_id}-candidate-pages.txt"
    chunks = [f"===== PDF PAGE {page_no} =====\n{pages[page_no - 1].rstrip()}\n" for page_no in selected]
    path.write_text("\n".join(chunks), encoding="utf-8")
    return [{"path": str(path.relative_to(ROOT)), "pages": selected, "sha256": sha256(path)}]


def extract_one(source_id: str, spec: dict[str, Any]) -> dict[str, Any]:
    verify_source(spec)
    pdf: Path = spec["pdf"]
    text_path: Path = spec["text"]
    text_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["pdftotext", "-layout", "-enc", "UTF-8", str(pdf), str(text_path)], check=True)
    raw_text = text_path.read_text(encoding="utf-8", errors="replace")
    total_pages = page_count(pdf)
    extracted_pages = len(raw_text.split("\f")) - (1 if raw_text.endswith("\f") else 0)
    if extracted_pages != total_pages:
        raise RuntimeError(f"{source_id}: extracted page count mismatch {extracted_pages} != {total_pages}")
    term_hits = {term: hits(raw_text, term) for term in spec["terms"]}
    candidate_pages = {hit["page"] for term in term_hits.values() for hit in term}
    slices = write_candidate_pages(source_id, raw_text, candidate_pages, max_pages=30)
    return {
        "source_id": source_id,
        "pdf_sha256": sha256(pdf),
        "pdf_page_count": total_pages,
        "text_path": str(text_path.relative_to(ROOT)),
        "text_sha256": sha256(text_path),
        "text_bytes": text_path.stat().st_size,
        "visible_character_count": sum(1 for char in raw_text if not char.isspace()),
        "term_hits": {term: {"count": len(term_hits[term]), "hits": term_hits[term]} for term in spec["terms"]},
        "candidate_slices": slices,
        "extraction_method": "Poppler pdftotext -layout -enc UTF-8",
        "ocr_performed": False,
    }


def main() -> int:
    if shutil.which("pdftotext") is None or shutil.which("pdfinfo") is None:
        raise RuntimeError("Poppler tools are required")
    reports = [extract_one(source_id, spec) for source_id, spec in SOURCES.items()]
    manifest = {
        "schema": "ranah-observatory/milestone8-grdp-anomaly-text/v1",
        "criterion": "one focused causal or quasi-causal case study",
        "source_count": len(reports),
        "sources": reports,
        "anomalies_resolved": False,
        "outcome_model_fit": False,
        "causal_effect_estimated": False,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
