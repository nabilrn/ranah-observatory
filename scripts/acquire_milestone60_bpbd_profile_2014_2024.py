#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data/raw/bpbd/m60_profile_2014_2024"
PROCESSED_DIR = ROOT / "data/processed/bpbd/disaster_profile_2014_2024"
RAW_IMAGE = RAW_DIR / "profil-bencana-sumbar-2014-sd-2024.jpeg"
TABLE_CROP = PROCESSED_DIR / "annual-chart-table-audit-crop.png"
SUMMARY_CROP = PROCESSED_DIR / "hazard-summary-audit-crop.png"
MANIFEST = ROOT / "data/manifests/milestone60_bpbd_profile_2014_2024_acquisition.json"

CKAN_BASES = (
    "https://data.sumbarprov.go.id/api/3/action",
    "https://data.sumbarprov.go.id/id/api/3/action",
)
PACKAGE_SLUG = "profil-bencana-sumatera-barat-2014-2024"
PACKAGE_ID = "8acd9009-56df-43ba-b079-a477ab844edb"
RESOURCE_ID = "b15be1ad-80b9-4ffa-9e6b-a8e0118599cb"


def fetch_bytes(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "RanahObservatory/1.0 (+https://github.com/nabilrn/ranah-observatory)"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def fetch_json(url: str) -> dict:
    return json.loads(fetch_bytes(url).decode("utf-8"))


def ckan_action(action: str, **params: str) -> dict:
    query = urllib.parse.urlencode(params)
    errors: list[str] = []
    for base in CKAN_BASES:
        url = f"{base}/{action}?{query}"
        try:
            payload = fetch_json(url)
            if payload.get("success") is not True:
                raise RuntimeError(f"success=false: {payload}")
            return payload["result"]
        except Exception as exc:
            errors.append(f"{url}: {exc}")
    raise RuntimeError("all official CKAN endpoints failed:\n" + "\n".join(errors))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    package = ckan_action("package_show", id=PACKAGE_SLUG)
    if package.get("id") != PACKAGE_ID:
        raise RuntimeError(f"M60 package identity drift: {package.get('id')}")
    matches = [r for r in package.get("resources", []) if r.get("id") == RESOURCE_ID]
    if len(matches) != 1:
        raise RuntimeError(f"M60 resource identity drift: {len(matches)}")
    resource = matches[0]
    url = resource.get("url")
    if not url:
        raise RuntimeError("M60 resource URL missing")

    raw = fetch_bytes(url)
    if len(raw) < 50_000:
        raise RuntimeError(f"M60 artifact unexpectedly small: {len(raw)} bytes")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    RAW_IMAGE.write_bytes(raw)

    with Image.open(RAW_IMAGE) as image:
        if image.format not in {"JPEG", "JPG"}:
            raise RuntimeError(f"M60 unexpected image format: {image.format}")
        width, height = image.size
        if width < 900 or height < 500:
            raise RuntimeError(f"M60 image resolution unexpectedly small: {width}x{height}")
        rgb = image.convert("RGB")

        # Preserve the right-hand annual chart/table with context; crop is a visual aid only.
        table = rgb.crop((int(width * 0.49), int(height * 0.43), width, height))
        table = table.resize((table.width * 4, table.height * 4), Image.Resampling.LANCZOS)

        # Preserve the title and seven aggregate hazard totals for independent visual review.
        summary = rgb.crop((0, 0, width, int(height * 0.46)))
        summary = summary.resize((summary.width * 2, summary.height * 2), Image.Resampling.LANCZOS)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    table.save(TABLE_CROP, format="PNG", optimize=True)
    summary.save(SUMMARY_CROP, format="PNG", optimize=True)

    extras = {str(x.get("key", "")): str(x.get("value", "")) for x in package.get("extras", []) or []}
    manifest = {
        "schema": "ranah-observatory/milestone60-bpbd-profile-2014-2024-acquisition/v1",
        "milestone": 60,
        "depends_on": [59],
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "portal": "https://data.sumbarprov.go.id/",
            "package_slug": PACKAGE_SLUG,
            "package_id": package.get("id"),
            "package_title": package.get("title"),
            "organization": (package.get("organization") or {}).get("title"),
            "producer": extras.get("Produsen Data") or package.get("author"),
            "source_data": extras.get("Sumber Data"),
            "year_metadata": extras.get("Tahun"),
            "resource_id": RESOURCE_ID,
            "resource_name": resource.get("name"),
            "resource_format": resource.get("format"),
            "resource_url": url,
            "media_type": resource.get("mimetype") or resource.get("mimetype_inner"),
        },
        "raw_artifact": {
            "path": RAW_IMAGE.relative_to(ROOT).as_posix(),
            "sha256": sha256(RAW_IMAGE),
            "size_bytes": RAW_IMAGE.stat().st_size,
            "width_px": width,
            "height_px": height,
        },
        "audit_derivatives": {
            "annual_chart_table_crop": {
                "path": TABLE_CROP.relative_to(ROOT).as_posix(),
                "sha256": sha256(TABLE_CROP),
                "semantic_role": "lossless-content visual enlargement; no OCR and no numerical transformation",
            },
            "hazard_summary_crop": {
                "path": SUMMARY_CROP.relative_to(ROOT).as_posix(),
                "sha256": sha256(SUMMARY_CROP),
                "semantic_role": "lossless-content visual enlargement; no OCR and no numerical transformation",
            },
        },
        "qualification_boundary": {
            "raw_artifact_frozen": True,
            "ocr_used": False,
            "annual_timeseries_extracted": False,
            "hazard_totals_extracted": False,
            "dashboard_promotion_authorized": False,
            "required_next_gate": "manual visual transcription with arithmetic checks and 2023/2024 anchor reconciliation",
        },
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"artifact_bytes": RAW_IMAGE.stat().st_size, "width": width, "height": height}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
