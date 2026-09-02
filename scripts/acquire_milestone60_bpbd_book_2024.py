#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data/raw/bpbd/m60_book_2024"
MANIFEST = ROOT / "data/manifests/milestone60_bpbd_book_2024_acquisition.json"
CKAN_BASES = (
    "https://data.sumbarprov.go.id/api/3/action",
    "https://data.sumbarprov.go.id/id/api/3/action",
)
PACKAGE_SLUG = "buku-data-dan-informasi-bencana-tahun-2024"


def fetch_bytes(url: str, timeout: int = 120) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "RanahObservatory/1.0 (+https://github.com/nabilrn/ranah-observatory)"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def ckan_action(action: str, **params: str) -> dict:
    query = urllib.parse.urlencode(params)
    errors: list[str] = []
    for base in CKAN_BASES:
        url = f"{base}/{action}?{query}"
        try:
            payload = json.loads(fetch_bytes(url).decode("utf-8"))
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
    pdfs = [r for r in package.get("resources", []) if str(r.get("format", "")).upper() == "PDF"]
    if len(pdfs) != 1:
        raise RuntimeError(f"M60 expected one official PDF resource, found {len(pdfs)}")
    resource = pdfs[0]
    url = resource.get("url")
    if not url:
        raise RuntimeError("M60 official book resource URL missing")

    raw = fetch_bytes(url)
    if not raw.startswith(b"%PDF"):
        raise RuntimeError(f"M60 official book did not return PDF bytes: prefix={raw[:16]!r}")
    if len(raw) < 100_000:
        raise RuntimeError(f"M60 official book unexpectedly small: {len(raw)}")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out = RAW_DIR / "data-dan-informasi-bencana-sumatera-barat-2024.pdf"
    out.write_bytes(raw)

    extras = {str(x.get("key", "")): str(x.get("value", "")) for x in package.get("extras", []) or []}
    manifest = {
        "schema": "ranah-observatory/milestone60-bpbd-book-2024-acquisition/v1",
        "milestone": 60,
        "depends_on": [59],
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "portal": "https://data.sumbarprov.go.id/",
            "package_slug": PACKAGE_SLUG,
            "package_id": package.get("id"),
            "package_title": package.get("title"),
            "organization": (package.get("organization") or {}).get("title"),
            "author": package.get("author"),
            "maintainer": package.get("maintainer"),
            "source_metadata": extras.get("Sumber"),
            "year_metadata": extras.get("Tahun"),
            "release_date_metadata": extras.get("Tanggal Rilis"),
            "region_metadata": extras.get("Wilayah"),
            "resource_id": resource.get("id"),
            "resource_name": resource.get("name"),
            "resource_format": resource.get("format"),
            "resource_url": url,
        },
        "raw_artifact": {
            "path": out.relative_to(ROOT).as_posix(),
            "sha256": sha256(out),
            "size_bytes": out.stat().st_size,
        },
        "qualification_boundary": {
            "raw_artifact_frozen": True,
            "pdf_text_extraction_authorized_for_diagnostic_search": True,
            "historical_profile_presence_confirmed": False,
            "historical_timeseries_extraction_authorized": False,
            "dashboard_promotion_authorized": False,
        },
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"package_id": package.get("id"), "resource_id": resource.get("id"), "bytes": out.stat().st_size}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
