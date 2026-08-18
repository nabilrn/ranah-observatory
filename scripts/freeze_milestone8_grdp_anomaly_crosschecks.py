#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from scripts.bps_client import BPSApiError, BPSClient

ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "ranah-observatory/0.1 (+https://github.com/nabilrn/ranah-observatory)"
MANIFEST = ROOT / "data/manifests/milestone8_grdp_anomaly_source_freeze.json"


@dataclass(frozen=True)
class Target:
    source_id: str
    domain: str
    publication_id: str
    title_tokens: tuple[str, ...]
    metadata_dir: Path
    raw_pdf_path: Path


TARGETS = (
    Target(
        source_id="m8_bukittinggi_grdp_crosscheck",
        domain="1375",
        publication_id="44d13f6979435a1a50fc1df9",
        title_tokens=("produk domestik regional bruto kota bukittinggi", "2011", "2013"),
        metadata_dir=ROOT / "data/snapshots/bps/milestone8/crosschecks/bukittinggi-grdp-2011-2013",
        raw_pdf_path=ROOT / "data/raw/milestone8/crosschecks/bukittinggi-grdp-2011-2013/source.pdf",
    ),
    Target(
        source_id="m8_solok_selatan_grdp_crosscheck",
        domain="1310",
        publication_id="b71346df5fc0c753641b0063",
        title_tokens=("solok selatan dalam angka", "2013"),
        metadata_dir=ROOT / "data/snapshots/bps/milestone8/crosschecks/solok-selatan-dalam-angka-2013",
        raw_pdf_path=ROOT / "data/raw/milestone8/crosschecks/solok-selatan-dalam-angka-2013/source.pdf",
    ),
)


def canonical_text(value: Any) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", str(value).lower()).split())


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch_bytes(url: str, timeout: float = 90.0, retries: int = 3) -> tuple[bytes, str]:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.8",
                    "User-Agent": USER_AGENT,
                },
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read(), response.geturl()
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt >= retries:
                break
            time.sleep(1.0 * (2**attempt))
    raise RuntimeError(f"failed to download {url}") from last_error


def normalize_detail(payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
    if str(payload.get("status", "")) != "OK" or str(payload.get("data-availability", "")) != "available":
        return None
    data = payload.get("data")
    return data if isinstance(data, Mapping) else None


def title_matches(row: Mapping[str, Any], target: Target) -> bool:
    title = canonical_text(row.get("title", ""))
    return all(canonical_text(token) in title for token in target.title_tokens)


def resolve(client: BPSClient, target: Target) -> Mapping[str, Any]:
    try:
        payload = client._request(  # noqa: SLF001
            "view",
            {"model": "publication", "domain": target.domain, "lang": "ind", "id": target.publication_id},
        )
        detail = normalize_detail(payload)
        if detail is not None and title_matches(detail, target):
            return detail
    except BPSApiError:
        pass
    raise RuntimeError(f"{target.source_id}: direct BPS publication lookup failed semantic qualification")


def freeze_one(client: BPSClient, target: Target) -> dict[str, Any]:
    publication = dict(resolve(client, target))
    pdf_url = str(publication.get("pdf", "")).strip()
    if not pdf_url:
        raise RuntimeError(f"{target.source_id}: publication has no PDF URL")
    if pdf_url.startswith("http://"):
        pdf_url = "https://" + pdf_url[len("http://") :]
    data, final_url = fetch_bytes(pdf_url)
    if not data.startswith(b"%PDF-") or len(data) < 100_000:
        raise RuntimeError(f"{target.source_id}: downloaded bytes fail PDF qualification ({len(data)} bytes)")

    target.metadata_dir.mkdir(parents=True, exist_ok=True)
    target.raw_pdf_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path = target.metadata_dir / "publication-metadata.json"
    checksum_path = target.metadata_dir / "source.pdf.sha256"
    metadata = {
        "schema": "ranah-observatory/milestone8-bps-anomaly-crosscheck-source/v1",
        "source_id": target.source_id,
        "domain": target.domain,
        "publication_id": target.publication_id,
        "publication": publication,
        "resolved_pdf_url": pdf_url,
        "final_download_url": final_url,
        "raw_storage_policy": "raw PDF is gitignored and uploaded as CI artifact; Git retains metadata, SHA-256 and deterministic derived text",
    }
    metadata_bytes = (json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    metadata_path.write_bytes(metadata_bytes)
    metadata_hash = sha256_bytes(metadata_bytes)
    (target.metadata_dir / "publication-metadata.json.sha256").write_text(
        f"{metadata_hash}  publication-metadata.json\n", encoding="utf-8"
    )
    target.raw_pdf_path.write_bytes(data)
    pdf_hash = sha256_bytes(data)
    checksum_path.write_text(f"{pdf_hash}  source.pdf\n", encoding="utf-8")
    return {
        "source_id": target.source_id,
        "domain": target.domain,
        "publication_id": target.publication_id,
        "title": publication.get("title"),
        "metadata_path": str(metadata_path.relative_to(ROOT)),
        "metadata_sha256": metadata_hash,
        "checksum_path": str(checksum_path.relative_to(ROOT)),
        "raw_pdf_runtime_path": str(target.raw_pdf_path.relative_to(ROOT)),
        "pdf_sha256": pdf_hash,
        "pdf_bytes": len(data),
        "raw_pdf_git_tracked": False,
    }


def main() -> int:
    api_key = os.environ.get("BPS_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("BPS_API_KEY is required")
    client = BPSClient(api_key, timeout=45.0, retries=3, retry_backoff_seconds=1.0)
    snapshots = [freeze_one(client, target) for target in TARGETS]
    manifest = {
        "schema": "ranah-observatory/milestone8-grdp-anomaly-source-freeze/v1",
        "criterion": "one focused causal or quasi-causal case study",
        "source_count": len(snapshots),
        "sources": snapshots,
        "all_source_bytes_frozen": len(snapshots) == 2,
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
