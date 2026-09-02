#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data/processed/bpbd/disaster_events_2024"
SOURCE_OUT = OUT_DIR / "bpbd-disaster-events-2024-source-native.csv"
MANIFEST_OUT = ROOT / "data/manifests/milestone58_bpbd_events_2024_acquisition.json"

CKAN_BASES = (
    "https://data.sumbarprov.go.id/api/3/action",
    "https://data.sumbarprov.go.id/id/api/3/action",
)
PACKAGE_SLUG = "data-kejadian-bencana-dan-dampak-bencana-tahun-2024"
PACKAGE_ID = "24704fb3-6b59-4a67-94a3-ab585a33f303"
RESOURCE_ID = "9d99b5ed-a005-4b35-880c-7e9954c9ade5"
EXPECTED_FIELDS = ["Kode Wilayah", "Jenis Bencana", "Jumlah Kejadian"]


def fetch_json(url: str, timeout: int = 60) -> dict:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "RanahObservatory/1.0 (+https://github.com/nabilrn/ranah-observatory)"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


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
        raise RuntimeError(f"M58 package identity drift: {package.get('id')}")

    resources = [r for r in package.get("resources", []) if r.get("id") == RESOURCE_ID]
    if len(resources) != 1:
        raise RuntimeError(f"M58 resource identity drift: matches={len(resources)}")
    resource = resources[0]
    if resource.get("datastore_active") is not True:
        raise RuntimeError("M58 DataStore is not active")

    result = ckan_action("datastore_search", resource_id=RESOURCE_ID, limit="1000")
    fields = [f.get("id") for f in result.get("fields", []) if f.get("id") != "_id"]
    if fields != EXPECTED_FIELDS:
        raise RuntimeError(f"M58 schema drift: {fields}")
    records = result.get("records", [])
    if result.get("total") != len(records) or not records:
        raise RuntimeError(f"M58 incomplete DataStore fetch: total={result.get('total')} records={len(records)}")

    normalized: list[dict[str, str | int]] = []
    for record in records:
        code = str(record.get("Kode Wilayah", "")).strip()
        hazard = str(record.get("Jenis Bencana", "")).strip()
        raw_count = record.get("Jumlah Kejadian")
        if not code or not hazard or raw_count is None:
            raise RuntimeError(f"M58 blank required field: {record}")
        count = int(float(raw_count))
        if count < 0:
            raise RuntimeError(f"M58 negative count: {record}")
        normalized.append({"Kode Wilayah": code, "Jenis Bencana": hazard, "Jumlah Kejadian": count})

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with SOURCE_OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=EXPECTED_FIELDS)
        writer.writeheader()
        writer.writerows(normalized)

    codes = sorted({str(r["Kode Wilayah"]) for r in normalized})
    hazards = sorted({str(r["Jenis Bencana"]) for r in normalized})
    extras = {str(x.get("key", "")): str(x.get("value", "")) for x in package.get("extras", []) or []}
    manifest = {
        "schema": "ranah-observatory/milestone58-bpbd-events-2024-acquisition/v1",
        "milestone": 58,
        "depends_on": [57],
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "portal": "https://data.sumbarprov.go.id/",
            "package_slug": PACKAGE_SLUG,
            "package_id": package.get("id"),
            "package_title": package.get("title"),
            "organization": (package.get("organization") or {}).get("title"),
            "producer": extras.get("Produsen Data") or package.get("author"),
            "source_data": extras.get("Sumber Data"),
            "year": extras.get("Tahun Data") or extras.get("Tahun") or "2024",
            "resource_id": RESOURCE_ID,
            "resource_name": resource.get("name"),
            "resource_format": resource.get("format"),
            "resource_url": resource.get("url"),
            "datastore_active": True,
        },
        "source_native": {
            "record_count": len(normalized),
            "field_names": EXPECTED_FIELDS,
            "unique_code_count": len(codes),
            "source_codes": codes,
            "unique_hazard_count": len(hazards),
            "hazard_labels": hazards,
            "raw_event_count_sum": sum(int(r["Jumlah Kejadian"]) for r in normalized),
            "geography_semantics_interpreted": False,
            "hazard_taxonomy_harmonized": False,
            "missing_values_inferred": False,
        },
        "output": {
            "path": SOURCE_OUT.relative_to(ROOT).as_posix(),
            "sha256": sha256(SOURCE_OUT),
        },
        "result": {
            "source_native_acquisition_complete": True,
            "canonical_geography_mapping_authorized": False,
            "dashboard_promotion_authorized": False,
        },
    }
    MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest["source_native"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
