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
    output_dir: Path


BPS_TARGETS = (
    BPSPublicationTarget(
        source_id="m8_grdp_pre",
        domain="1300",
        publication_id="c3fec3700a5c89b2412bba5a",
        keyword="Perkembangan Ekonomi Sumatera Barat",
        release_year=2010,
        title_tokens=("perkembangan ekonomi sumatera barat", "2005", "2009"),
        output_dir=ROOT / "data/snapshots/bps/milestone8/grdp-2005-2009",
    ),
    BPSPublicationTarget(
        source_id="m8_grdp_post",
        domain="1373",
        publication_id="09a8175fa67d4c80d2183354",
        keyword="Sawahlunto Dalam Angka 2014",
        release_year=2014,
        title_tokens=("sawahlunto", "dalam angka", "2014"),
        output_dir=ROOT / "data/snapshots/bps/milestone8/grdp-2009-2013",
    ),
)

DLNA_URL = "https://www.preventionweb.net/media/75466/download"
DLNA_OUTPUT_DIR = ROOT / "data/snapshots/disaster/milestone8/dlna-2009"


def canonical_text(value: Any) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", str(value).lower()).split())


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
    # First use the immutable publication identifier embedded in the official BPS
    # publication URL. Fall back to a constrained list query only if an older API
    # deployment does not accept that identifier in the detail endpoint.
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

    target.output_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = target.output_dir / "publication-metadata.json"
    source_path = target.output_dir / "source.pdf"

    metadata = {
        "schema": "ranah-observatory/milestone8-bps-publication-snapshot/v1",
        "source_plan_id": target.source_id,
        "domain": target.domain,
        "requested_publication_id": target.publication_id,
        "retrieval_method": "BPS WebAPI publication metadata -> official pdf URL",
        "publication": publication,
        "resolved_pdf_url": pdf_url,
        "final_download_url": final_url,
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    metadata_hash = write_bytes_with_hash(
        metadata_path,
        metadata_path.read_bytes(),
    )
    pdf_hash = write_bytes_with_hash(source_path, pdf_bytes)

    return {
        "source_plan_id": target.source_id,
        "metadata_path": str(metadata_path.relative_to(ROOT)),
        "metadata_sha256": metadata_hash,
        "pdf_path": str(source_path.relative_to(ROOT)),
        "pdf_sha256": pdf_hash,
        "pdf_bytes": len(pdf_bytes),
        "title": publication.get("title"),
        "release_date": publication.get("rl_date"),
        "updated_date": publication.get("updt_date"),
    }


def freeze_dlna() -> dict[str, Any]:
    pdf_bytes, final_url = fetch_bytes(DLNA_URL)
    validate_pdf(pdf_bytes, source_id="m8_damage_dlna")
    DLNA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    source_path = DLNA_OUTPUT_DIR / "source.pdf"
    metadata_path = DLNA_OUTPUT_DIR / "source-metadata.json"

    metadata = {
        "schema": "ranah-observatory/milestone8-disaster-publication-snapshot/v1",
        "source_plan_id": "m8_damage_dlna",
        "authority": "BNPB; Bappenas; Provincial and District/City Governments of West Sumatra and Jambi",
        "title": "West Sumatra and Jambi Natural Disasters: Damage, Loss and Preliminary Needs Assessment",
        "publication_year": 2009,
        "authority_catalog_url": "https://perpustakaan.bnpb.go.id/inlislite/opac/detail-opac?id=1663",
        "mirror_download_url": DLNA_URL,
        "final_download_url": final_url,
        "note": "Bytes are frozen from the PreventionWeb mirror; authority remains the joint government report, not the mirror.",
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    metadata_hash = write_bytes_with_hash(metadata_path, metadata_path.read_bytes())
    pdf_hash = write_bytes_with_hash(source_path, pdf_bytes)
    return {
        "source_plan_id": "m8_damage_dlna",
        "metadata_path": str(metadata_path.relative_to(ROOT)),
        "metadata_sha256": metadata_hash,
        "pdf_path": str(source_path.relative_to(ROOT)),
        "pdf_sha256": pdf_hash,
        "pdf_bytes": len(pdf_bytes),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze Milestone 8 earthquake source publications")
    parser.add_argument(
        "--skip-dlna",
        action="store_true",
        help="freeze only BPS publications",
    )
    args = parser.parse_args()

    api_key = os.environ.get("BPS_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("BPS_API_KEY is required")

    client = BPSClient(api_key, timeout=45.0, retries=3, retry_backoff_seconds=1.0)
    snapshots = [freeze_bps_target(client, target) for target in BPS_TARGETS]
    if not args.skip_dlna:
        snapshots.append(freeze_dlna())

    manifest_path = ROOT / "data/manifests/milestone8_source_freeze.json"
    manifest = {
        "schema": "ranah-observatory/milestone8-source-freeze/v1",
        "criterion": "one focused causal or quasi-causal case study",
        "snapshot_count": len(snapshots),
        "snapshots": snapshots,
        "source_bytes_frozen": True,
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
