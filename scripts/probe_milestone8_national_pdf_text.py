#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "data/raw/milestone8/bps/grdp-kabkota-indonesia-2005-2009/source.pdf"
CHECKSUM = ROOT / "data/snapshots/bps/milestone8/grdp-kabkota-indonesia-2005-2009/source.pdf.sha256"
MANIFEST = ROOT / "data/manifests/milestone8_national_pdf_text_probe.json"

TERMS = (
    "sumatera barat",
    "kepulauan mentawai",
    "pesisir selatan",
    "padang pariaman",
    "kota padang",
    "harga konstan 2000",
    "atas dasar harga konstan",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize(value: str) -> str:
    return " ".join(value.split())


def require_binary(name: str) -> None:
    if shutil.which(name) is None:
        raise RuntimeError(f"required binary missing: {name}")


def verify_pdf() -> str:
    if not PDF.exists():
        raise RuntimeError(f"missing hydrated national BPS PDF: {PDF.relative_to(ROOT)}")
    expected = CHECKSUM.read_text(encoding="utf-8").split()[0]
    actual = sha256(PDF)
    if actual != expected:
        raise RuntimeError(f"national BPS PDF hash drift: expected={expected} actual={actual}")
    return actual


def extract_poppler_raw(tmp: Path) -> Path:
    target = tmp / "pdftotext-raw.txt"
    subprocess.run(["pdftotext", "-raw", "-enc", "UTF-8", str(PDF), str(target)], check=True)
    return target


def extract_mutool_text(tmp: Path) -> Path:
    target = tmp / "mutool-text.txt"
    subprocess.run(["mutool", "draw", "-q", "-F", "txt", "-o", str(target), str(PDF)], check=True)
    return target


def extract_outline() -> str:
    completed = subprocess.run(
        ["mutool", "show", str(PDF), "outline"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return completed.stdout


def term_report(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    pages = text.split("\f")
    report: dict[str, Any] = {
        "bytes": path.stat().st_size,
        "visible_character_count": sum(1 for char in text if not char.isspace()),
        "page_separator_count": text.count("\f"),
        "terms": {},
    }
    for term in TERMS:
        needle = term.casefold()
        hits: list[dict[str, Any]] = []
        for page_no, page in enumerate(pages, start=1):
            lines = page.splitlines()
            for line_no, line in enumerate(lines, start=1):
                if needle in line.casefold():
                    start = max(0, line_no - 3)
                    end = min(len(lines), line_no + 2)
                    context = normalize(" ".join(lines[start:end]))[:1000]
                    hits.append({"page": page_no, "line": line_no, "context": context})
                    if len(hits) >= 20:
                        break
            if len(hits) >= 20:
                break
        report["terms"][term] = {"hit_count_capped": len(hits), "hits": hits}
    return report


def outline_report(text: str) -> dict[str, Any]:
    folded = text.casefold()
    matches = [term for term in TERMS if term in folded]
    relevant_lines = [
        normalize(line)[:1000]
        for line in text.splitlines()
        if any(term in line.casefold() for term in TERMS)
    ][:50]
    return {
        "bytes": len(text.encode("utf-8")),
        "matched_terms": matches,
        "relevant_lines": relevant_lines,
        "outline_present": bool(text.strip()),
    }


def main() -> int:
    require_binary("pdftotext")
    require_binary("mutool")
    pdf_hash = verify_pdf()
    with tempfile.TemporaryDirectory(prefix="m8-national-pdf-") as tmp_dir:
        tmp = Path(tmp_dir)
        poppler = term_report(extract_poppler_raw(tmp))
        mutool = term_report(extract_mutool_text(tmp))
    outline = outline_report(extract_outline())

    recovered = any(
        payload["hit_count_capped"] > 0
        for decoder in (poppler, mutool)
        for payload in decoder["terms"].values()
    ) or bool(outline["matched_terms"])

    manifest = {
        "schema": "ranah-observatory/milestone8-national-pdf-text-probe/v1",
        "criterion": "one focused causal or quasi-causal case study",
        "source_plan_id": "m8_grdp_pre_national",
        "pdf_sha256": pdf_hash,
        "methods": {
            "poppler_raw": poppler,
            "mutool_text": mutool,
            "mutool_outline": outline,
        },
        "relevant_text_recovered_without_ocr": recovered,
        "ocr_performed": False,
        "outcome_values_extracted": False,
        "outcome_model_fit": False,
        "causal_effect_estimated": False,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
