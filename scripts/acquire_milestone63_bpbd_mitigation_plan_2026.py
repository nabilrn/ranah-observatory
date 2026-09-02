#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = "https://bpbd.sumbarprov.go.id/web-api/api/files/badan-perencanaan-pembangunan-daerah/2026/04/file-1776832372620-c55c479ab1ac4c7ea86c62bd6ce5270bRenja%20BPBD%202026.pdf"
RAW = ROOT / "data/raw/bpbd/m63_renja_2026/renja-bpbd-sumbar-2026.pdf"
EXCERPT = ROOT / "data/processed/bpbd/mitigation_plan_2026/renja-bpbd-2026-pages-51-64.txt"
MANIFEST = ROOT / "data/manifests/milestone63_bpbd_mitigation_plan_2026_acquisition.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch_bytes(url: str, attempts: int = 5) -> bytes:
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "RanahObservatory/1.0"})
            with urllib.request.urlopen(req, timeout=90) as response:
                payload = response.read()
                if not payload.startswith(b"%PDF"):
                    raise RuntimeError("M63 source response is not a PDF")
                return payload
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, RuntimeError) as exc:
            last = exc
            if attempt == attempts:
                break
            time.sleep(min(2 ** (attempt - 1), 8))
    raise RuntimeError(f"M63 source acquisition failed after {attempts} attempts: {last}")


def main() -> int:
    RAW.parent.mkdir(parents=True, exist_ok=True)
    EXCERPT.parent.mkdir(parents=True, exist_ok=True)
    payload = fetch_bytes(SOURCE_URL)
    RAW.write_bytes(payload)

    subprocess.run(
        ["pdftotext", "-layout", "-f", "51", "-l", "64", str(RAW), str(EXCERPT)],
        check=True,
    )
    text = EXCERPT.read_text(encoding="utf-8", errors="replace")
    if "Permasalahan" not in text or "Pelayanan Pencegahan" not in text:
        raise RuntimeError("M63 extracted text does not contain expected mitigation-plan anchors")

    manifest = {
        "schema": "ranah-observatory/milestone63-bpbd-mitigation-plan-2026-acquisition/v1",
        "milestone": 63,
        "depends_on": [62],
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "publisher": "Badan Penanggulangan Bencana Daerah Provinsi Sumatera Barat",
            "document": "Rencana Kerja BPBD Provinsi Sumatera Barat Tahun 2026",
            "legal_container": "Peraturan Gubernur Sumatera Barat Nomor 23 Tahun 2025",
            "source_url": SOURCE_URL,
            "plan_year": 2026,
            "document_type": "planning_document",
        },
        "raw_artifact": {
            "path": RAW.relative_to(ROOT).as_posix(),
            "sha256": sha256(RAW),
            "size_bytes": RAW.stat().st_size,
        },
        "text_excerpt": {
            "path": EXCERPT.relative_to(ROOT).as_posix(),
            "sha256": sha256(EXCERPT),
            "pdf_pages_one_based": [51, 64],
            "extraction_method": "pdftotext -layout",
            "ocr_used": False,
        },
        "qualification_boundary": {
            "planning_targets_are_actual_achievement": False,
            "qualitative_problem_statements_are_quantified_capacity": False,
            "dashboard_planning_context_authorized": True,
            "prediction_claim_authorized": False,
        },
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"raw_bytes": RAW.stat().st_size, "excerpt_chars": len(text)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
