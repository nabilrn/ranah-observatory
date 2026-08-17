#!/usr/bin/env python3
from __future__ import annotations

import argparse
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


@dataclass(frozen=True)
class BPSPublicationTarget:
    source_id: str
    domain: str
    publication_id: str
    keyword: str
    release_year: int
    title_tokens: tuple[str, ...]
    metadata_dir: Path
    raw_pdf_path: Path


BPS_TARGETS = (
    BPSPublicationTarget(
        source_id="m8_grdp_pre",
        domain="1300",
        publication_id="c3fec3700a5c89b2412bba5a",
        keyword="Perkembangan Ekonomi Sumatera Barat",
        release_year=2010,
        title_tokens=("perkembangan ekonomi sumatera barat", "2005", "2009"),
        metadata_dir=ROOT / "data/snapshots/bps/milestone8/grdp-2005-2009",
        raw_pdf_path=ROOT / "data/raw/milestone8/bps/grdp-2005-2009/source.pdf",
    ),
    BPSPublicationTarget(
        source_id="m8_grdp_post",
        domain="1373",
        publication_id="09a8175fa67d4c80d2183354",
        keyword="Sawahlunto Dalam Angka 2014",
        release_year=2014,
        title_tokens=("sawahlunto", "dalam angka", "2014"),
        metadata_dir=ROOT / "data/snapshots/bps/milestone8/grdp-2009-2013",
        raw_pdf_path=ROOT / "data/raw/milestone8/bps/grdp-2009-2013/source.pdf",
    ),
)


def canonical_text(value: Any) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", str(value).lower()).split())


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_text_snapshot(path: Path, data: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    digest = sha256_bytes(data)
    path.with_suffix(path.suffix + ".sha256").write_text(
        f"{digest}  {path.name}\n", encoding="utf-8"
    )
    return digest


def write_raw_pdf(path: Path, data: bytes, checksum_path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    digest = sha256_bytes(data)
    checksum_path.parent.mkdir(parents=True, exist_ok=True)
    checksum_path.write_text(
        f"{digest}  source.pdf\n",
        encoding="utf-8",
    )
    return digest


def fetch_bytes(url: str, *, timeout: float = 90.0, retries: int = 3) -> tuple[bytes, str]:
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
                data = response.read()
                final_url = response.geturl()
            return data, final_url
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt >= retries:
                break
            time.sleep(1.0 * (2**attempt))
    raise RuntimeError(f"failed to download {url}") from last_error


def validate_pdf(data: bytes, *, source_id: str) -> None:
    if not data.startswith(b"%PDF-"):
        raise RuntimeError(f"{source_id}: downloaded bytes are not a PDF")
    if len(data) < 100_000:
        raise RuntimeError(f"{source_id}: PDF is implausibly small ({len(data)} bytes)")


def normalize_publication_payload(payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
    if str(payload.get("status", "")) != "OK":
        return None
    if str(payload.get("data-availability", "")) != "available":
        return None
    data = payload.get("data")
    return data if isinstance(data, Mapping) else None


def publication_matches(row: Mapping[str, Any], target: BPSPublicationTarget) -> bool:
    title = canonical_text(row.get("title", ""))
    return all(canonical_text(token) in title for token in target.title_tokens)


def resolve_bps_publication(client: BPSClient, target: BPSPublicationTarget) -> Mapping[str, Any]:
    try:
        payload = client._request(  # noqa: SLF001 - no public generic view helper exists yet
            "view",
            {
                "model": "publication",
                "domain": target.domain,
                "lang": "ind",
                "id": target.publication_id,
            },
        )
        detail = normalize_publication_payload(payload)
        if detail is not None and publication_matches(detail, target):
            return detail
    except BPSApiError:
        pass

    candidates = list(
        client.iter_list(
            "publication",
            domain=target.domain,
            lang="ind",
            year=target.release_year,
            keyword=target.keyword,
        )
    )
    matches = [row for row in candidates if publication_matches(row, target)]
    if len(matches) != 1:
        titles = [str(row.get("title", "")) for row in candidates]
        raise RuntimeError(
            f"{target.source_id}: expected one publication match, got {len(matches)}; candidates={titles}"
        )
    return matches[0]


def freeze_bps_target(client: BPSClient, target: BPSPublicationTarget) -> dict[str, Any]:
    publication = dict(resolve_bps_publication(client, target))
    pdf_url = str(publication.get("pdf", "")).strip()
    if not pdf_url:
        raise RuntimeError(f"{target.source_id}: BPS publication metadata has no pdf URL")
    if pdf_url.startswith("http://"):
        pdf_url = "https://" + pdf_url[len("http://") :]

    pdf_bytes, final_url = fetch_bytes(pdf_url)
    validate_pdf(pdf_bytes, source_id=target.source_id)

    target.metadata_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = target.metadata_dir / "publication-metadata.json"
    checksum_path = target.metadata_dir / "source.pdf.sha256"

    metadata = {
        "schema": "ranah-observatory/milestone8-bps-publication-snapshot/v1",
        "source_plan_id": target.source_id,
        "domain": target.domain,
        "requested_publication_id": target.publication_id,
        "retrieval_method": "BPS WebAPI publication metadata -> official pdf URL",
        "publication": publication,
        "resolved_pdf_url": pdf_url,
        "final_download_url": final_url,
        "raw_storage_policy": "PDF bytes live under gitignored data/raw during acquisition and are uploaded as a GitHub Actions artifact; Git stores metadata, SHA-256, and derived text only.",
    }
    metadata_bytes = (
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    metadata_hash = write_text_snapshot(metadata_path, metadata_bytes)
    pdf_hash = write_raw_pdf(target.raw_pdf_path, pdf_bytes, checksum_path)

    return {
        "source_plan_id": target.source_id,
        "metadata_path": str(metadata_path.relative_to(ROOT)),
        "metadata_sha256": metadata_hash,
        "checksum_path": str(checksum_path.relative_to(ROOT)),
        "raw_pdf_runtime_path": str(target.raw_pdf_path.relative_to(ROOT)),
        "raw_pdf_git_tracked": False,
        "pdf_sha256": pdf_hash,
        "pdf_bytes": len(pdf_bytes),
        "title": publication.get("title"),
        "release_date": publication.get("rl_date"),
        "updated_date": publication.get("updt_date"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze Milestone 8 BPS earthquake outcome publications")
    parser.add_argument("--skip-dlna", action="store_true", help="retained for workflow compatibility; DLNA is handled by a separate freezer")
    parser.parse_args()

    api_key = os.environ.get("BPS_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("BPS_API_KEY is required")

    client = BPSClient(api_key, timeout=45.0, retries=3, retry_backoff_seconds=1.0)
    snapshots = [freeze_bps_target(client, target) for target in BPS_TARGETS]

    manifest_path = ROOT / "data/manifests/milestone8_source_freeze.json"
    manifest = {
        "schema": "ranah-observatory/milestone8-source-freeze/v1",
        "criterion": "one focused causal or quasi-causal case study",
        "snapshot_count": len(snapshots),
        "snapshots": snapshots,
        "raw_pdf_policy": "gitignored data/raw plus workflow artifact; no raw PDF tracked in Git",
        "source_bytes_frozen": False,
        "outcome_extracted": False,
        "exposure_extracted": False,
        "causal_effect_estimated": False,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
