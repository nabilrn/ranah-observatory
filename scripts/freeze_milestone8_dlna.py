#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data/snapshots/disaster/milestone8/dlna-2009"
MANIFEST_PATH = ROOT / "data/manifests/milestone8_source_freeze.json"
PDF_URL = "https://www.gfdrr.org/sites/gfdrr/files/documents/GFDRR_Indonesia_DLNA.2009.EN_.pdf"
GFDRR_CONTEXT_URL = "https://www.gfdrr.org/en/indonesia-2009-pdna-undertaken-after-earthquake-killed-1100-west-sumatra"
BNPB_CATALOG_URL = "https://perpustakaan.bnpb.go.id/inlislite/opac/detail-opac?id=1663"
USER_AGENT = "ranah-observatory/0.1 (+https://github.com/nabilrn/ranah-observatory)"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_bytes_with_hash(path: Path, data: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    digest = sha256_bytes(data)
    path.with_suffix(path.suffix + ".sha256").write_text(
        f"{digest}  {path.name}\n", encoding="utf-8"
    )
    return digest


def fetch_pdf(timeout: float = 90.0, retries: int = 3) -> tuple[bytes, str, str]:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            request = urllib.request.Request(
                PDF_URL,
                headers={
                    "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.8",
                    "User-Agent": USER_AGENT,
                },
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = response.read()
                final_url = response.geturl()
                content_type = str(response.headers.get("Content-Type", ""))
            return data, final_url, content_type
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt >= retries:
                break
            time.sleep(1.0 * (2**attempt))
    raise RuntimeError(f"failed to download GFDRR DLNA PDF from {PDF_URL}") from last_error


def validate_pdf(data: bytes) -> None:
    if not data.startswith(b"%PDF-"):
        raise RuntimeError("m8_damage_dlna: GFDRR bytes are not a PDF")
    if len(data) < 1_000_000:
        raise RuntimeError(f"m8_damage_dlna: PDF is implausibly small ({len(data)} bytes)")


def update_manifest(snapshot: dict[str, Any]) -> None:
    if not MANIFEST_PATH.exists():
        raise RuntimeError(
            "Milestone 8 BPS source manifest is missing; run the BPS freezer with --skip-dlna first"
        )
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest.get("schema") != "ranah-observatory/milestone8-source-freeze/v1":
        raise RuntimeError("unexpected Milestone 8 source-freeze manifest schema")

    snapshots = [
        row
        for row in manifest.get("snapshots", [])
        if row.get("source_plan_id") != "m8_damage_dlna"
    ]
    snapshots.append(snapshot)
    snapshots.sort(key=lambda row: str(row.get("source_plan_id", "")))
    manifest["snapshots"] = snapshots
    manifest["snapshot_count"] = len(snapshots)
    manifest["source_bytes_frozen"] = len(snapshots) == 3
    manifest["outcome_extracted"] = False
    manifest["exposure_extracted"] = False
    manifest["causal_effect_estimated"] = False
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    pdf_bytes, final_url, content_type = fetch_pdf()
    validate_pdf(pdf_bytes)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    pdf_path = OUTPUT_DIR / "source.pdf"
    metadata_path = OUTPUT_DIR / "source-metadata.json"

    metadata = {
        "schema": "ranah-observatory/milestone8-disaster-publication-snapshot/v1",
        "source_plan_id": "m8_damage_dlna",
        "authority": "BNPB; Bappenas; Provincial and District/City Governments of West Sumatra and Jambi",
        "title": "West Sumatra and Jambi Natural Disasters: Damage, Loss and Preliminary Needs Assessment",
        "publication_year": 2009,
        "authority_catalog_url": BNPB_CATALOG_URL,
        "official_partner_context_url": GFDRR_CONTEXT_URL,
        "official_partner_pdf_url": PDF_URL,
        "final_download_url": final_url,
        "content_type": content_type,
        "note": "PDF bytes are frozen from the official GFDRR-hosted full PDNA link. Report authority remains the joint government-led assessment.",
    }
    metadata_bytes = (
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    metadata_hash = write_bytes_with_hash(metadata_path, metadata_bytes)
    pdf_hash = write_bytes_with_hash(pdf_path, pdf_bytes)

    snapshot = {
        "source_plan_id": "m8_damage_dlna",
        "metadata_path": str(metadata_path.relative_to(ROOT)),
        "metadata_sha256": metadata_hash,
        "pdf_path": str(pdf_path.relative_to(ROOT)),
        "pdf_sha256": pdf_hash,
        "pdf_bytes": len(pdf_bytes),
        "host": "GFDRR",
    }
    update_manifest(snapshot)
    print(json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
