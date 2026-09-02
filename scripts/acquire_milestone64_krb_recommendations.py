#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = "https://inarisk.bnpb.go.id/pdf/Sumatera%20Barat/Dokumen%20KRB%20Prov.%20Sumatera%20Barat_final%20draft.pdf"
OUT_DIR = ROOT / "data/processed/bnpb/krb_sumbar_2022_2026"
EXCERPT = OUT_DIR / "krb-recommendation-search-excerpt.txt"
INDEX = OUT_DIR / "krb-recommendation-page-index.json"
MANIFEST = ROOT / "data/manifests/milestone64_krb_recommendations_acquisition.json"
KEYWORDS = (
    "rekomendasi",
    "rekomendasi spesifik",
    "rekomendasi generik",
    "aksi mitigasi",
    "pengurangan risiko bencana",
    "pilihan tindakan",
)


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
    raise RuntimeError(f"M64 source acquisition failed after {attempts} attempts: {last}")


def norm(value: str) -> str:
    return " ".join(value.lower().split())


def main() -> int:
    payload = fetch_bytes(SOURCE_URL)
    raw_sha = hashlib.sha256(payload).hexdigest()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / "krb-sumbar.pdf"
        text_path = Path(tmpdir) / "krb-sumbar.txt"
        pdf_path.write_bytes(payload)
        subprocess.run(["pdftotext", "-layout", str(pdf_path), str(text_path)], check=True)
        text = text_path.read_text(encoding="utf-8", errors="replace")

    pages = text.split("\f")
    hits: list[dict[str, object]] = []
    selected_pages: list[int] = []
    for page_number, page in enumerate(pages, start=1):
        normalized = norm(page)
        matched = sorted({keyword for keyword in KEYWORDS if keyword in normalized})
        if not matched:
            continue
        selected_pages.append(page_number)
        compact = " ".join(page.split())
        hits.append({
            "pdf_page_one_based": page_number,
            "matched_keywords": matched,
            "preview": compact[:1200],
        })

    if not hits:
        raise RuntimeError("M64 no recommendation-related pages found")

    excerpt_parts: list[str] = []
    selected_set = set(selected_pages)
    # Include one adjacent page on each side so tables/actions that continue across a page boundary stay auditable.
    expanded = sorted({p for page in selected_set for p in (page - 1, page, page + 1) if 1 <= p <= len(pages)})
    for page_number in expanded:
        page = pages[page_number - 1].strip()
        if not page:
            continue
        excerpt_parts.append(f"===== PDF PAGE {page_number} =====\n{page}\n")
    EXCERPT.write_text("\n".join(excerpt_parts), encoding="utf-8")
    INDEX.write_text(json.dumps({
        "schema": "ranah-observatory/milestone64-krb-recommendation-page-index/v1",
        "keyword_hit_pages": selected_pages,
        "expanded_excerpt_pages": expanded,
        "hits": hits,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "schema": "ranah-observatory/milestone64-krb-recommendations-acquisition/v1",
        "milestone": 64,
        "depends_on": [63],
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "publisher": "Badan Nasional Penanggulangan Bencana / InaRISK",
            "document": "Kajian Risiko Bencana Provinsi Sumatera Barat 2022-2026",
            "source_url": SOURCE_URL,
            "document_type": "risk_assessment",
        },
        "raw_artifact": {
            "sha256": raw_sha,
            "size_bytes": len(payload),
            "committed_to_repository": False,
            "reason_not_committed": "Large official source PDF; retain checksum and deterministic non-OCR recommendation excerpt instead of duplicating the full publication in git.",
        },
        "text_extraction": {
            "method": "pdftotext -layout",
            "ocr_used": False,
            "source_page_count_from_text": len(pages),
            "keyword_hit_page_count": len(selected_pages),
            "expanded_excerpt_page_count": len(expanded),
            "excerpt_path": EXCERPT.relative_to(ROOT).as_posix(),
            "excerpt_sha256": hashlib.sha256(EXCERPT.read_bytes()).hexdigest(),
            "index_path": INDEX.relative_to(ROOT).as_posix(),
            "index_sha256": hashlib.sha256(INDEX.read_bytes()).hexdigest(),
        },
        "qualification_boundary": {
            "recommendation_extraction_authorized": True,
            "causal_prediction_authorized": False,
            "unmitigated_loss_forecast_authorized": False,
            "recommendations_are_observed_outcomes": False,
        },
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"raw_bytes": len(payload), "pages": len(pages), "hit_pages": selected_pages, "excerpt_pages": expanded}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
