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
OUT_DIR = ROOT / "data/processed/bpbd/disaster_events_2023"
OBS_OUT = OUT_DIR / "bpbd-disaster-events-2023-source-native.csv"
MANIFEST_OUT = ROOT / "data/manifests/milestone57_bpbd_events_2023.json"

CKAN_BASES = (
    "https://data.sumbarprov.go.id/api/3/action",
    "https://data.sumbarprov.go.id/id/api/3/action",
)
PACKAGE_SLUG = "jumlah-kejadian-bencana-tahun-2023"
PACKAGE_ID = "e953d109-88d4-4be7-a0ad-ffc720b3c4a4"
RESOURCE_ID = "e5d974eb-95a0-4570-93d1-9ca45c9fb77b"
EXPECTED_COLUMNS = [
    "Kabupaten/Kota", "Abrasi pantai", "Angin kencang", "Banjir",
    "Banjir Bandang", "Erupsi Gunung Api", "Gelombang Pasang", "Gempa Bumi",
    "Kebakaran Hutan & Lahan", "Kekeringan", "Longsor", "Jumlah",
]


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


def as_int(value) -> int:
    return int(float(value))


def main() -> int:
    package = ckan_action("package_show", id=PACKAGE_SLUG)
    if package.get("id") != PACKAGE_ID:
        raise RuntimeError("M57 package identity drift")
    if (package.get("organization") or {}).get("name") != "badan-penanggulangan-bencana-daerah":
        raise RuntimeError("M57 producer organization drift")

    resources = [r for r in package.get("resources", []) if r.get("id") == RESOURCE_ID]
    if len(resources) != 1:
        raise RuntimeError(f"M57 resource identity drift: matches={len(resources)}")
    resource = resources[0]
    if str(resource.get("format", "")).upper() != "XLSX":
        raise RuntimeError("M57 resource format drift")

    result = ckan_action("datastore_search", resource_id=RESOURCE_ID, limit="100")
    records = result.get("records", [])
    fields = [f.get("id") for f in result.get("fields", []) if f.get("id") != "_id"]
    if fields != EXPECTED_COLUMNS:
        raise RuntimeError(f"M57 schema drift: {fields}")
    if result.get("total") != 20 or len(records) != 20:
        raise RuntimeError(f"M57 row footprint drift: total={result.get('total')} records={len(records)}")

    labels = [str(record["Kabupaten/Kota"]).strip() for record in records]
    total_rows = [record for record in records if str(record["Kabupaten/Kota"]).strip() == "Jumlah"]
    district_rows = [record for record in records if str(record["Kabupaten/Kota"]).strip() != "Jumlah"]
    if len(total_rows) != 1 or len(district_rows) != 19:
        raise RuntimeError(f"M57 geography footprint drift: districts={len(district_rows)} totals={len(total_rows)}")
    if len(set(str(row["Kabupaten/Kota"]).strip() for row in district_rows)) != 19:
        raise RuntimeError("M57 duplicate district labels")

    total_row = total_rows[0]
    province_total = as_int(total_row["Jumlah"])
    district_sum = sum(as_int(row["Jumlah"]) for row in district_rows)
    if district_sum != province_total:
        raise RuntimeError(f"M57 district-total reconciliation failed: {district_sum} != {province_total}")

    hazard_columns = EXPECTED_COLUMNS[1:-1]
    hazard_total_sum = sum(as_int(total_row[column]) for column in hazard_columns)
    if hazard_total_sum != province_total:
        raise RuntimeError(f"M57 hazard-total reconciliation failed: {hazard_total_sum} != {province_total}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with OBS_OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=EXPECTED_COLUMNS)
        writer.writeheader()
        for record in records:
            writer.writerow({column: "" if record.get(column) is None else record.get(column) for column in EXPECTED_COLUMNS})

    extras = {str(item.get("key", "")): str(item.get("value", "")) for item in package.get("extras", []) or []}
    manifest = {
        "schema": "ranah-observatory/milestone57-bpbd-events-2023/v1",
        "milestone": 57,
        "depends_on": [54, 56],
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "portal": "https://data.sumbarprov.go.id/",
            "package_slug": PACKAGE_SLUG,
            "package_id": package.get("id"),
            "title": package.get("title"),
            "organization": (package.get("organization") or {}).get("title"),
            "producer": extras.get("Produsen Data") or package.get("author"),
            "source_data": extras.get("Sumber Data"),
            "year": extras.get("Tahun"),
            "resource_id": RESOURCE_ID,
            "resource_name": resource.get("name"),
            "resource_format": resource.get("format"),
            "resource_url": resource.get("url"),
            "datastore_active": resource.get("datastore_active"),
        },
        "source_native": {
            "row_count": len(records),
            "district_row_count": len(district_rows),
            "total_row_count": len(total_rows),
            "district_or_total_labels": labels,
            "columns": EXPECTED_COLUMNS,
            "province_total_events": province_total,
            "district_sum_events": district_sum,
            "hazard_total_sum_events": hazard_total_sum,
            "hazard_totals": {column: as_int(total_row[column]) for column in hazard_columns},
            "missing_values_inferred": False,
            "zero_values_reinterpreted": False,
            "geography_mapping_performed": False,
            "hazard_taxonomy_harmonized": False,
        },
        "outputs": {
            "observations": {
                "path": OBS_OUT.relative_to(ROOT).as_posix(),
                "sha256": sha256(OBS_OUT),
            }
        },
        "claim_boundary": {
            "classification": "source_native_official_operational_event_counts",
            "cross_source_equivalence_with_dibi_2022_authorized": False,
            "cross_source_equivalence_with_bnpb_authorized": False,
            "dashboard_use_authorized_after_geography_review": False,
        },
    }
    MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"district_rows": 19, "province_total_events": province_total, "manifest": MANIFEST_OUT.relative_to(ROOT).as_posix()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
