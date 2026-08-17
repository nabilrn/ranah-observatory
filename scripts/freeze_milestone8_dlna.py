#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterator, Mapping

ROOT = Path(__file__).resolve().parents[1]
METADATA_DIR = ROOT / "data/snapshots/disaster/milestone8/dlna-2009"
RAW_PDF_PATH = ROOT / "data/raw/milestone8/disaster/dlna-2009/source.pdf"
MANIFEST_PATH = ROOT / "data/manifests/milestone8_source_freeze.json"
WORLD_BANK_RECORD_URL = "https://documents.worldbank.org/en/publication/documents-reports/documentdetail/177951468285048532/west-sumatra-and-jambi-natural-disasters-damage-loss-and-preliminary-needs-assessment"
WORLD_BANK_API_BASE = "https://search.worldbank.org/api/v3/wds"
WORLD_BANK_LEGACY_RECORD_ID = "177951468285048532"
REPORT_TITLE = "West Sumatra and Jambi Natural Disasters: Damage, Loss and Preliminary Needs Assessment"
GFDRR_CONTEXT_URL = "https://www.gfdrr.org/en/indonesia-2009-pdna-undertaken-after-earthquake-killed-1100-west-sumatra"
GFDRR_LEGACY_PDF_URL = "https://www.gfdrr.org/sites/gfdrr/files/documents/GFDRR_Indonesia_DLNA.2009.EN_.pdf"
BNPB_CATALOG_URL = "https://perpustakaan.bnpb.go.id/inlislite/opac/detail-opac?id=1663"
USER_AGENT = "ranah-observatory/0.1 (+https://github.com/nabilrn/ranah-observatory)"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_text_snapshot(path: Path, data: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    digest = sha256_bytes(data)
    path.with_suffix(path.suffix + ".sha256").write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return digest


def write_raw_pdf(path: Path, data: bytes, checksum_path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    digest = sha256_bytes(data)
    checksum_path.parent.mkdir(parents=True, exist_ok=True)
    checksum_path.write_text(f"{digest}  source.pdf\n", encoding="utf-8")
    return digest


def fetch_bytes(url: str, *, accept: str, timeout: float = 60.0, retries: int = 3) -> tuple[bytes, str, str]:
    errors: list[str] = []
    for attempt in range(retries + 1):
        try:
            request = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = response.read()
                final_url = response.geturl()
                content_type = str(response.headers.get("Content-Type", ""))
            return data, final_url, content_type
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            errors.append(f"attempt={attempt + 1} error={type(exc).__name__}: {exc}")
            if attempt >= retries:
                break
            time.sleep(1.0 * (2**attempt))
    raise RuntimeError(f"failed to fetch {url}; {' | '.join(errors)}")


def normalize_title(value: Any) -> str:
    return " ".join(str(value or "").lower().replace(":", " ").replace(",", " ").split())


def walk_mappings(value: Any) -> Iterator[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from walk_mappings(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_mappings(child)


def resolve_world_bank_pdf() -> tuple[str, dict[str, Any], str]:
    query = urllib.parse.urlencode(
        {
            "format": "json",
            "qterm": "West Sumatra and Jambi natural disasters damage loss preliminary needs assessment",
            "fl": "id,display_title,pdfurl,docdt,src_cit,authr,repnme,url",
            "rows": "20",
        }
    )
    api_url = f"{WORLD_BANK_API_BASE}?{query}"
    raw, final_api_url, content_type = fetch_bytes(api_url, accept="application/json,*/*;q=0.8", timeout=45.0, retries=3)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"World Bank D&R API did not return valid JSON; content_type={content_type}") from exc

    target_tokens = {"west", "sumatra", "jambi", "natural", "disasters", "damage", "loss", "preliminary", "needs", "assessment"}
    candidates: list[dict[str, Any]] = []
    for row in walk_mappings(payload):
        pdfurl = str(row.get("pdfurl", "") or "").strip()
        title = normalize_title(row.get("display_title") or row.get("repnme"))
        if not pdfurl or not title:
            continue
        if target_tokens.issubset(set(title.split())):
            candidates.append(dict(row))

    unique: dict[tuple[str, str], dict[str, Any]] = {}
    for row in candidates:
        unique[(str(row.get("id", "")), str(row.get("pdfurl", "")))] = row
    candidates = list(unique.values())
    if len(candidates) != 1:
        summary = [{"id": row.get("id"), "display_title": row.get("display_title"), "pdfurl": row.get("pdfurl")} for row in candidates]
        raise RuntimeError(f"expected one World Bank DLNA record, got {len(candidates)}; matches={summary}")

    record = candidates[0]
    pdf_url = str(record["pdfurl"]).strip()
    if pdf_url.startswith("http://"):
        pdf_url = "https://" + pdf_url[len("http://") :]
    return pdf_url, record, final_api_url


def validate_pdf(data: bytes, *, content_type: str) -> None:
    if not data.startswith(b"%PDF-"):
        raise RuntimeError(f"m8_damage_dlna: downloaded bytes are not a PDF; content_type={content_type}")
    if len(data) < 1_000_000:
        raise RuntimeError(f"m8_damage_dlna: PDF is implausibly small ({len(data)} bytes)")


def update_manifest(snapshot: dict[str, Any]) -> None:
    if not MANIFEST_PATH.exists():
        raise RuntimeError("Milestone 8 BPS source manifest is missing; run the BPS freezer first")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest.get("schema") != "ranah-observatory/milestone8-source-freeze/v1":
        raise RuntimeError("unexpected Milestone 8 source-freeze manifest schema")
    snapshots = [row for row in manifest.get("snapshots", []) if row.get("source_plan_id") != "m8_damage_dlna"]
    snapshots.append(snapshot)
    snapshots.sort(key=lambda row: str(row.get("source_plan_id", "")))
    manifest["snapshots"] = snapshots
    manifest["snapshot_count"] = len(snapshots)
    manifest["source_bytes_frozen"] = len(snapshots) == 3
    manifest["outcome_extracted"] = False
    manifest["exposure_extracted"] = False
    manifest["causal_effect_estimated"] = False
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    pdf_url, world_bank_record, api_url = resolve_world_bank_pdf()
    pdf_bytes, final_url, content_type = fetch_bytes(
        pdf_url,
        accept="application/pdf,application/octet-stream;q=0.9,*/*;q=0.8",
        timeout=90.0,
        retries=3,
    )
    validate_pdf(pdf_bytes, content_type=content_type)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)

    metadata_path = METADATA_DIR / "source-metadata.json"
    checksum_path = METADATA_DIR / "source.pdf.sha256"
    metadata = {
        "schema": "ranah-observatory/milestone8-disaster-publication-snapshot/v1",
        "source_plan_id": "m8_damage_dlna",
        "authority": "BNPB; Bappenas; Provincial and District/City Governments of West Sumatra and Jambi",
        "title": REPORT_TITLE,
        "publication_year": 2009,
        "authority_catalog_url": BNPB_CATALOG_URL,
        "world_bank_record_url": WORLD_BANK_RECORD_URL,
        "world_bank_legacy_record_id": WORLD_BANK_LEGACY_RECORD_ID,
        "world_bank_api_url": api_url,
        "world_bank_api_record": world_bank_record,
        "resolved_pdf_url": pdf_url,
        "final_download_url": final_url,
        "content_type": content_type,
        "gfdrr_context_url": GFDRR_CONTEXT_URL,
        "gfdrr_legacy_pdf_url": GFDRR_LEGACY_PDF_URL,
        "raw_storage_policy": "PDF bytes live under gitignored data/raw during acquisition and are uploaded as a GitHub Actions artifact; Git stores metadata, SHA-256, and derived text only.",
    }
    metadata_bytes = (json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    metadata_hash = write_text_snapshot(metadata_path, metadata_bytes)
    pdf_hash = write_raw_pdf(RAW_PDF_PATH, pdf_bytes, checksum_path)

    snapshot = {
        "source_plan_id": "m8_damage_dlna",
        "metadata_path": str(metadata_path.relative_to(ROOT)),
        "metadata_sha256": metadata_hash,
        "checksum_path": str(checksum_path.relative_to(ROOT)),
        "raw_pdf_runtime_path": str(RAW_PDF_PATH.relative_to(ROOT)),
        "raw_pdf_git_tracked": False,
        "pdf_sha256": pdf_hash,
        "pdf_bytes": len(pdf_bytes),
        "host": "World Bank Documents & Reports",
    }
    update_manifest(snapshot)
    print(json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
