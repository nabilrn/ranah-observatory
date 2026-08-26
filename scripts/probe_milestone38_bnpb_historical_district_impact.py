#!/usr/bin/env python3
"""Milestone 38: qualify BNPB annual district/city disaster-impact dataset transport.

This probe is intentionally metadata-only. It discovers official BNPB Satu Data
packages and resource transport for annual datasets titled
"Jumlah kejadian dan Dampak Bencana Tahun YYYY". It does not download or parse
impact values and therefore cannot promote any numeric evidence.
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

API_BASE = "https://data.bnpb.go.id/api/3/action"
TITLE_RE = re.compile(r"^Jumlah kejadian dan Dampak Bencana Tahun (\d{4})$", re.I)
TARGET_START_YEAR = 2000
TARGET_END_YEAR = 2017
USER_AGENT = "ranah-observatory-m38/1.0 (+https://github.com/nabilrn/ranah-observatory)"


def _get_json(url: str, timeout: int = 30) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        payload = json.load(response)
    if not payload.get("success"):
        raise RuntimeError(f"CKAN action failed: {url}")
    return payload


def _package_search() -> list[dict[str, Any]]:
    params = urllib.parse.urlencode(
        {
            "q": '"Jumlah kejadian dan Dampak Bencana Tahun"',
            "rows": 100,
        }
    )
    payload = _get_json(f"{API_BASE}/package_search?{params}")
    return list(payload.get("result", {}).get("results", []))


def _package_show(package_id: str) -> dict[str, Any]:
    params = urllib.parse.urlencode({"id": package_id})
    payload = _get_json(f"{API_BASE}/package_show?{params}")
    return dict(payload.get("result", {}))


def _classify_resource(resource: dict[str, Any]) -> str:
    url = str(resource.get("url") or "").strip()
    fmt = str(resource.get("format") or "").strip().upper()
    name = str(resource.get("name") or "").strip()
    combined = f"{url} {name}".lower()
    if fmt in {"XLSX", "XLS", "CSV", "JSON"} or re.search(r"\.(xlsx|xls|csv|json)(?:$|[?#])", url, re.I):
        return "direct_file"
    if url:
        return "external_or_link_resource"
    return "missing_url"


def _resource_record(resource: dict[str, Any], year: int) -> dict[str, Any]:
    url = str(resource.get("url") or "").strip()
    name = str(resource.get("name") or "").strip()
    fmt = str(resource.get("format") or "").strip()
    combined = f"{name} {url}".lower()
    return {
        "id": resource.get("id"),
        "name": name,
        "format": fmt,
        "url": url,
        "url_type": resource.get("url_type"),
        "mimetype": resource.get("mimetype"),
        "datastore_active": bool(resource.get("datastore_active", False)),
        "transport_class": _classify_resource(resource),
        "sumbar_filename_candidate": bool(re.search(rf"stat_by_wil_13_{year}\.(xlsx|xls)(?:$|[?#])", combined, re.I)),
    }


def build_manifest() -> dict[str, Any]:
    search_results = _package_search()
    matched: dict[int, dict[str, Any]] = {}
    duplicates: dict[int, list[str]] = {}

    for item in search_results:
        title = str(item.get("title") or "").strip()
        match = TITLE_RE.match(title)
        if not match:
            continue
        year = int(match.group(1))
        if not (TARGET_START_YEAR <= year <= TARGET_END_YEAR):
            continue
        package_id = str(item.get("id") or item.get("name") or "")
        if year in matched:
            duplicates.setdefault(year, [str(matched[year].get("id") or matched[year].get("name"))]).append(package_id)
            continue
        matched[year] = _package_show(package_id)

    years = []
    for year in range(TARGET_START_YEAR, TARGET_END_YEAR + 1):
        package = matched.get(year)
        if not package:
            years.append({"year": year, "found": False, "resources": []})
            continue
        resources = [_resource_record(r, year) for r in package.get("resources", [])]
        counts = {
            "direct_file": sum(r["transport_class"] == "direct_file" for r in resources),
            "external_or_link_resource": sum(r["transport_class"] == "external_or_link_resource" for r in resources),
            "missing_url": sum(r["transport_class"] == "missing_url" for r in resources),
            "sumbar_filename_candidates": sum(r["sumbar_filename_candidate"] for r in resources),
        }
        years.append(
            {
                "year": year,
                "found": True,
                "id": package.get("id"),
                "name": package.get("name"),
                "title": package.get("title"),
                "notes": package.get("notes"),
                "metadata_created": package.get("metadata_created"),
                "metadata_modified": package.get("metadata_modified"),
                "organization": (package.get("organization") or {}).get("name"),
                "source": next((x.get("value") for x in package.get("extras", []) if x.get("key") == "source"), None),
                "resource_counts": counts,
                "resources": resources,
            }
        )

    found_years = [row["year"] for row in years if row["found"]]
    direct_years = [row["year"] for row in years if row.get("resource_counts", {}).get("direct_file", 0) > 0]
    sumbar_direct_years = [row["year"] for row in years if row.get("resource_counts", {}).get("sumbar_filename_candidates", 0) > 0]
    linked_years = [
        row["year"]
        for row in years
        if row.get("resource_counts", {}).get("external_or_link_resource", 0) > 0
        and row.get("resource_counts", {}).get("direct_file", 0) == 0
    ]

    return {
        "schema": "ranah-observatory/milestone38-bnpb-historical-district-impact-transport/v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_portal": "https://data.bnpb.go.id",
        "ckan_api_base": API_BASE,
        "target_title_pattern": "Jumlah kejadian dan Dampak Bencana Tahun YYYY",
        "target_years": [TARGET_START_YEAR, TARGET_END_YEAR],
        "scope": "metadata-and-resource-transport-only",
        "numeric_values_requested": False,
        "numeric_values_downloaded": False,
        "numeric_values_promoted": False,
        "district_impact_panel_authorized": False,
        "event_level_gate_resolved": False,
        "found_years": found_years,
        "missing_years": [y for y in range(TARGET_START_YEAR, TARGET_END_YEAR + 1) if y not in found_years],
        "direct_file_years": direct_years,
        "sumbar_direct_filename_years": sumbar_direct_years,
        "link_only_years": linked_years,
        "duplicate_year_candidates": duplicates,
        "years": years,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/m38_bnpb_historical_district_impact_transport.json")
    args = parser.parse_args()
    manifest = build_manifest()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "found_years": manifest["found_years"],
        "missing_years": manifest["missing_years"],
        "direct_file_years": manifest["direct_file_years"],
        "sumbar_direct_filename_years": manifest["sumbar_direct_filename_years"],
        "link_only_years": manifest["link_only_years"],
    }, indent=2))


if __name__ == "__main__":
    main()
