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
OUT_DIR = ROOT / "data/processed/bpbd/disaster_events_2024_hazard_totals"
SOURCE_OUT = OUT_DIR / "bpbd-disaster-events-2024-hazard-totals-source-native.csv"
MANIFEST_OUT = ROOT / "data/manifests/milestone59_bpbd_hazard_totals_2024_acquisition.json"

CKAN_BASES = (
    "https://data.sumbarprov.go.id/api/3/action",
    "https://data.sumbarprov.go.id/id/api/3/action",
)
PACKAGE_SLUG = "jumlah-kejadian-bencana-2024"
PACKAGE_ID = "fd77b7eb-a2e4-4ee7-8a6a-78df1b15e4c6"
RESOURCE_ID = "43fc1b1b-bd4e-4a8e-887d-754029f0b074"
EXPECTED_FIELDS = ["Jenis Bencana", "Jumlah Kejadian"]


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
        raise RuntimeError(f"M59 package identity drift: {package.get('id')}")

    resources = [r for r in package.get("resources", []) if r.get("id") == RESOURCE_ID]
    if len(resources) != 1:
        raise RuntimeError(f"M59 resource identity drift: matches={len(resources)}")
    resource = resources[0]
    if resource.get("datastore_active") is not True:
        raise RuntimeError("M59 DataStore is not active")

    result = ckan_action("datastore_search", resource_id=RESOURCE_ID, limit="1000")
    fields = [f.get("id") for f in result.get("fields", []) if f.get("id") != "_id"]
    if fields != EXPECTED_FIELDS:
        raise RuntimeError(f"M59 schema drift: {fields}")
    records = result.get("records", [])
    if result.get("total") != len(records) or not records:
        raise RuntimeError(f"M59 incomplete DataStore fetch: total={result.get('total')} records={len(records)}")

    normalized: list[dict[str, str | int]] = []
    for record in records:
        hazard = str(record.get("Jenis Bencana", "")).strip()
        raw_count = record.get("Jumlah Kejadian")
        if not hazard or raw_count is None:
            raise RuntimeError(f"M59 blank required field: {record}")
        count = int(float(raw_count))
        if count < 0:
            raise RuntimeError(f"M59 negative count: {record}")
        normalized.append({"Jenis Bencana": hazard, "Jumlah Kejadian": count})

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with SOURCE_OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=EXPECTED_FIELDS)
        writer.writeheader()
        writer.writerows(normalized)

    extras = {str(x.get("key", "")): str(x.get("value", "")) for x in package.get("extras", []) or []}
    labels = [str(r["Jenis Bencana"]) for r in normalized]
    manifest = {
        "schema": "ranah-observatory/milestone59-bpbd-hazard-totals-2024-acquisition/v1",
        "milestone": 59,
        "depends_on": [58],
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
            "labels_in_source_order": labels,
            "unique_label_count": len(set(labels)),
            "raw_count_sum_including_any_total_row": sum(int(r["Jumlah Kejadian"]) for r in normalized),
            "total_row_interpreted": False,
            "hazard_taxonomy_harmonized": False,
            "missing_values_inferred": False,
        },
        "output": {
            "path": SOURCE_OUT.relative_to(ROOT).as_posix(),
            "sha256": sha256(SOURCE_OUT),
        },
        "result": {
            "source_native_acquisition_complete": True,
            "monthly_crosscheck_performed": False,
            "dashboard_promotion_authorized": False,
        },
    }
    MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest["source_native"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
