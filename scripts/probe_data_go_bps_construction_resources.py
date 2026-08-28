#!/usr/bin/env python3
from __future__ import annotations

import csv
import io
import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

DATASET_ID = "95930772-cddb-412c-9d6e-e43b11e9ccd6"
API_URL = "https://data.go.id/api/action/package_show"
OUTDIR = Path("probe-output")
MAX_RESOURCE_BYTES = 8 * 1024 * 1024
TARGET_LABELS = ("kecil", "menengah", "besar", "jumlah")


def fetch_bytes(url: str, *, max_bytes: int = MAX_RESOURCE_BYTES) -> tuple[bytes, dict[str, str]]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "*/*",
            "User-Agent": "ranah-observatory/0.1 (+https://github.com/nabilrn/ranah-observatory)",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        raw = response.read(max_bytes + 1)
        headers = {k.casefold(): v for k, v in response.headers.items()}
    if len(raw) > max_bytes:
        raise RuntimeError(f"resource exceeds bounded probe limit {max_bytes} bytes")
    return raw, headers


def folded(value: Any) -> str:
    return " ".join(str(value).casefold().split())


def extract_csv_sumbar_2005(raw: bytes) -> list[dict[str, Any]]:
    text = None
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        return []
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    rows: list[dict[str, Any]] = []
    try:
        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
        for row in reader:
            haystack = folded(row)
            if "sumatera barat" in haystack and "2005" in haystack:
                rows.append({str(k): v for k, v in row.items()})
    except csv.Error:
        return []
    return rows[:20]


def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    package_url = API_URL + "?" + urllib.parse.urlencode({"id": DATASET_ID})
    package_raw, package_headers = fetch_bytes(package_url, max_bytes=2 * 1024 * 1024)
    package = json.loads(package_raw.decode("utf-8"))
    if not package.get("success") or not isinstance(package.get("result"), dict):
        raise RuntimeError("data.go.id package_show did not return a successful result")

    result = package["result"]
    resources = result.get("resources") or []
    report: dict[str, Any] = {
        "schema": "ranah-observatory/data-go-bps-construction-resources/v2",
        "dataset_id": DATASET_ID,
        "dataset_title": result.get("title"),
        "organization": (result.get("organization") or {}).get("title"),
        "source": result.get("url") or result.get("source") or result.get("notes"),
        "package_content_type": package_headers.get("content-type"),
        "resource_count": len(resources),
        "resources": [],
        "boundary": {
            "canonical_preference": "official BPS WebAPI/publication remains canonical; data.go.id is corroborative transport unless BPS provenance is explicit",
            "max_resource_bytes": MAX_RESOURCE_BYTES,
        },
    }

    for resource in resources:
        name = str(resource.get("name") or "")
        lname = folded(name)
        if not any(label in lname for label in TARGET_LABELS):
            continue
        item: dict[str, Any] = {
            "id": resource.get("id"),
            "name": name,
            "format": resource.get("format"),
            "url_type": resource.get("url_type"),
            "mimetype": resource.get("mimetype"),
            "size": resource.get("size"),
            "last_modified": resource.get("last_modified"),
            "created": resource.get("created"),
            "url": resource.get("url"),
            "sumbar_2005_rows": [],
            "fetch_error": None,
        }
        url = resource.get("url")
        if isinstance(url, str) and url.startswith("https://"):
            try:
                raw, headers = fetch_bytes(url)
                item["fetched_bytes"] = len(raw)
                item["content_type"] = headers.get("content-type")
                fmt = folded(resource.get("format"))
                ctype = folded(headers.get("content-type"))
                if "csv" in fmt or "csv" in ctype or url.casefold().endswith(".csv"):
                    item["sumbar_2005_rows"] = extract_csv_sumbar_2005(raw)
            except Exception as exc:
                item["fetch_error"] = f"{type(exc).__name__}: {exc}"
        report["resources"].append(item)

    path = OUTDIR / "data-go-bps-construction-resources.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "dataset_title": report["dataset_title"],
        "organization": report["organization"],
        "resource_count": report["resource_count"],
        "target_resources": [
            {
                "name": r["name"],
                "format": r["format"],
                "fetched_bytes": r.get("fetched_bytes"),
                "sumbar_2005_rows": len(r["sumbar_2005_rows"]),
                "fetch_error": r["fetch_error"],
            }
            for r in report["resources"]
        ],
        "output": path.as_posix(),
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
