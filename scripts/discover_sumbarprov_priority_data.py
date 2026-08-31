#!/usr/bin/env python3
"""Discover and optionally download priority Satu Data Sumbar datasets.

The portal is CKAN-backed. This script keeps UI scraping out of the research
pipeline: it uses CKAN package_search/package_show, records complete resource
metadata, and can freeze machine-readable source files under data/raw/
(which is gitignored by repository policy).

Default mode is discovery only. Use --download to freeze direct CSV/XLS/XLSX/
JSON/GeoJSON/ZIP resources after reviewing the manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PORTAL = "https://data.sumbarprov.go.id"
API_BASE = f"{PORTAL}/api/3/action"
USER_AGENT = "ranah-observatory-sumbarprov/1.0 (+https://github.com/nabilrn/ranah-observatory)"
DEFAULT_OUTPUT = ROOT / "data/manifests/sumbarprov-priority-discovery.json"
DEFAULT_RAW_DIR = ROOT / "data/raw/sumbarprov"
ALLOWED_HOST = "data.sumbarprov.go.id"
MACHINE_FORMATS = {"CSV", "XLS", "XLSX", "JSON", "GEOJSON", "ZIP"}

# Search terms are deliberately tied to product questions, not broad portal crawling.
PRIORITY_QUERIES: list[dict[str, str]] = [
    {"priority": "P0", "family": "disaster_casualties", "query": '"Jumlah Korban" bencana'},
    {"priority": "P0", "family": "disaster_housing", "query": '"Dampak Bencana" pemukiman'},
    {"priority": "P0", "family": "disaster_public_facilities", "query": '"Dampak Bencana" "Fasilitas Umum"'},
    {"priority": "P0", "family": "disaster_monetary_loss", "query": '"Kerugian" bencana'},
    {"priority": "P0", "family": "disaster_risk_capacity", "query": '"Indeks Risiko Bencana"'},
    {"priority": "P0", "family": "disaster_risk_capacity", "query": '"Indeks Ketangguhan Daerah"'},
    {"priority": "P0", "family": "land_cover", "query": '"Tutupan Lahan"'},
    {"priority": "P1", "family": "land_restoration", "query": 'reboisasi penghijauan'},
    {"priority": "P1", "family": "flood_mitigation", "query": 'drainase banjir'},
    {"priority": "P1", "family": "flood_mitigation", "query": 'tanggul banjir'},
    {"priority": "P1", "family": "flood_mitigation", "query": 'normalisasi sungai'},
    {"priority": "P1", "family": "tsunami_capacity", "query": '"Sirine Tsunami"'},
]


def _get_json(url: str, timeout: int = 45) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    if not payload.get("success"):
        raise RuntimeError(f"CKAN action failed: {url}")
    return payload


def _package_search(query: str, rows: int = 100) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode({"q": query, "rows": rows})
    payload = _get_json(f"{API_BASE}/package_search?{params}")
    return list(payload.get("result", {}).get("results", []))


def _package_show(package_id: str) -> dict[str, Any]:
    params = urllib.parse.urlencode({"id": package_id})
    payload = _get_json(f"{API_BASE}/package_show?{params}")
    return dict(payload.get("result", {}))


def _clean(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _safe_slug(value: str, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return (slug[:120] or fallback).strip("-")


def _resource_format(resource: dict[str, Any]) -> str:
    fmt = _clean(resource.get("format")).upper()
    if fmt:
        return fmt
    path = urllib.parse.urlsplit(_clean(resource.get("url"))).path.lower()
    suffix = Path(path).suffix.lstrip(".").upper()
    return suffix


def _resource_record(resource: dict[str, Any]) -> dict[str, Any]:
    fmt = _resource_format(resource)
    return {
        "id": _clean(resource.get("id")),
        "name": _clean(resource.get("name")),
        "description": _clean(resource.get("description")),
        "format": fmt,
        "url": _clean(resource.get("url")),
        "url_type": _clean(resource.get("url_type")),
        "mimetype": _clean(resource.get("mimetype")),
        "datastore_active": bool(resource.get("datastore_active", False)),
        "created": _clean(resource.get("created")),
        "last_modified": _clean(resource.get("last_modified")),
        "machine_readable": fmt in MACHINE_FORMATS,
    }


def _extras(package: dict[str, Any]) -> dict[str, str]:
    output: dict[str, str] = {}
    for item in package.get("extras", []):
        if isinstance(item, dict) and item.get("key"):
            output[_clean(item.get("key"))] = _clean(item.get("value"))
    return output


def discover() -> dict[str, Any]:
    candidates: dict[str, dict[str, Any]] = {}
    query_results: list[dict[str, Any]] = []

    for spec in PRIORITY_QUERIES:
        results = _package_search(spec["query"])
        package_ids: list[str] = []
        for result in results:
            package_id = _clean(result.get("id") or result.get("name"))
            if not package_id:
                continue
            package_ids.append(package_id)
            entry = candidates.setdefault(
                package_id,
                {
                    "matched_families": set(),
                    "priorities": set(),
                    "matched_queries": set(),
                },
            )
            entry["matched_families"].add(spec["family"])
            entry["priorities"].add(spec["priority"])
            entry["matched_queries"].add(spec["query"])
        query_results.append(
            {
                "priority": spec["priority"],
                "family": spec["family"],
                "query": spec["query"],
                "result_count": len(results),
                "package_ids": sorted(set(package_ids)),
            }
        )

    packages: list[dict[str, Any]] = []
    for package_id, match in candidates.items():
        package = _package_show(package_id)
        org = package.get("organization") or {}
        resources = [_resource_record(r) for r in package.get("resources", []) if isinstance(r, dict)]
        machine_count = sum(1 for r in resources if r["machine_readable"])
        packages.append(
            {
                "id": _clean(package.get("id")),
                "name": _clean(package.get("name")),
                "title": _clean(package.get("title")),
                "notes": _clean(package.get("notes")),
                "organization": _clean(org.get("title") or org.get("name")),
                "metadata_created": _clean(package.get("metadata_created")),
                "metadata_modified": _clean(package.get("metadata_modified")),
                "extras": _extras(package),
                "matched_families": sorted(match["matched_families"]),
                "matched_queries": sorted(match["matched_queries"]),
                "priority": "P0" if "P0" in match["priorities"] else "P1",
                "resource_count": len(resources),
                "machine_readable_resource_count": machine_count,
                "dataset_url": f"{PORTAL}/dataset/{_clean(package.get('name'))}",
                "resources": resources,
            }
        )

    packages.sort(key=lambda row: (row["priority"], row["title"].casefold(), row["id"]))
    return {
        "schema": "ranah-observatory/sumbarprov-priority-discovery/v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_portal": PORTAL,
        "ckan_api_base": API_BASE,
        "scope": "priority dashboard data gaps",
        "query_results": query_results,
        "package_count": len(packages),
        "machine_readable_package_count": sum(
            1 for package in packages if package["machine_readable_resource_count"] > 0
        ),
        "packages": packages,
        "downloads": [],
    }


def _download_resource(resource: dict[str, Any], raw_dir: Path, max_bytes: int) -> dict[str, Any]:
    url = resource["url"]
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != ALLOWED_HOST:
        return {"resource_id": resource["id"], "status": "skipped_untrusted_host", "url": url}
    if not resource["machine_readable"]:
        return {"resource_id": resource["id"], "status": "skipped_non_machine_format", "url": url}

    ext = resource["format"].casefold() or "bin"
    filename = f"{resource['id']}-{_safe_slug(resource['name'], 'resource')}.{ext}"
    target = raw_dir / "resources" / filename
    target.parent.mkdir(parents=True, exist_ok=True)

    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    digest = hashlib.sha256()
    size = 0
    try:
        with urllib.request.urlopen(request, timeout=90) as response, target.open("wb") as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    raise RuntimeError(f"resource exceeds max bytes ({max_bytes})")
                digest.update(chunk)
                output.write(chunk)
    except Exception:
        target.unlink(missing_ok=True)
        raise

    return {
        "resource_id": resource["id"],
        "status": "downloaded",
        "url": url,
        "path": target.relative_to(ROOT).as_posix(),
        "bytes": size,
        "sha256": digest.hexdigest(),
    }


def freeze_downloads(manifest: dict[str, Any], raw_dir: Path, max_bytes: int) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = raw_dir / "package-discovery.json"
    metadata_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    seen: set[str] = set()
    downloads: list[dict[str, Any]] = []
    for package in manifest["packages"]:
        for resource in package["resources"]:
            resource_id = resource["id"]
            if not resource_id or resource_id in seen:
                continue
            seen.add(resource_id)
            try:
                downloads.append(_download_resource(resource, raw_dir, max_bytes=max_bytes))
            except Exception as exc:
                downloads.append(
                    {
                        "resource_id": resource_id,
                        "status": "download_failed",
                        "url": resource["url"],
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
    manifest["downloads"] = downloads


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover priority data gaps from Satu Data Sumbar CKAN")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--download", action="store_true", help="freeze machine-readable resources under data/raw/sumbarprov")
    parser.add_argument("--max-resource-mb", type=int, default=50)
    args = parser.parse_args()

    manifest = discover()
    if args.download:
        freeze_downloads(manifest, args.raw_dir, max_bytes=args.max_resource_mb * 1024 * 1024)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "package_count": manifest["package_count"],
                "machine_readable_package_count": manifest["machine_readable_package_count"],
                "downloaded": sum(1 for d in manifest["downloads"] if d.get("status") == "downloaded"),
                "output": args.output.as_posix(),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
