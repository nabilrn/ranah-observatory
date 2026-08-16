from __future__ import annotations

import argparse
import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

BASE = "https://wis2node.bmkg.go.id/oapi"
COLLECTION_ID = "urn:wmo:md:id-bmkg:climate-surface-based-observations"
COLLECTION_PATH = urllib.parse.quote(COLLECTION_ID, safe="")
COLLECTION_URL = f"{BASE}/collections/{COLLECTION_PATH}"
ITEMS_URL = f"{COLLECTION_URL}/items"
QUERYABLES_URL = f"{COLLECTION_URL}/queryables"
SCHEMA_URL = f"{COLLECTION_URL}/schema"
MINANGKABAU_WIGOS = "0-20000-0-96163"
MINANGKABAU_STATION_URL = f"{BASE}/collections/stations/items/{MINANGKABAU_WIGOS}"
MINANGKABAU_BBOX = (100.20, -0.90, 100.38, -0.68)
ANCHOR_YEARS = (1982, 1998, 2010, 2024, 2025)
USER_AGENT = "ranah-observatory/0.1 (+https://github.com/nabilrn/ranah-observatory)"


def fetch_json(url: str, timeout: float = 45.0) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json,application/geo+json,*/*"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            payload: Any = None
            try:
                payload = json.loads(body.decode("utf-8-sig"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                pass
            return {
                "url": url,
                "reachable": True,
                "http_status": int(getattr(response, "status", 200)),
                "content_type": response.headers.get("Content-Type", ""),
                "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "payload": payload,
                "body_prefix": body[:500].decode("utf-8", errors="replace") if payload is None else "",
            }
    except urllib.error.HTTPError as exc:
        body = exc.read()
        return {
            "url": url,
            "reachable": True,
            "http_status": int(exc.code),
            "content_type": exc.headers.get("Content-Type", "") if exc.headers else "",
            "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
            "payload": None,
            "body_prefix": body[:500].decode("utf-8", errors="replace"),
        }
    except (urllib.error.URLError, TimeoutError) as exc:
        return {
            "url": url,
            "reachable": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def public(result: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if key != "payload"}


def query_url(params: Mapping[str, Any]) -> str:
    encoded = urllib.parse.urlencode(params, doseq=True)
    return f"{ITEMS_URL}?{encoded}"


def feature_properties(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, Mapping):
        return []
    features = payload.get("features")
    if not isinstance(features, list):
        return []
    rows: list[dict[str, Any]] = []
    for feature in features:
        if not isinstance(feature, Mapping):
            continue
        props = feature.get("properties")
        if isinstance(props, Mapping):
            rows.append(dict(props))
    return rows


def inspect_feature_collection(result: Mapping[str, Any]) -> dict[str, Any]:
    out = public(result)
    payload = result.get("payload")
    rows = feature_properties(payload)
    out.update(
        {
            "is_feature_collection": isinstance(payload, Mapping) and payload.get("type") == "FeatureCollection",
            "number_matched": payload.get("numberMatched") if isinstance(payload, Mapping) else None,
            "number_returned": payload.get("numberReturned") if isinstance(payload, Mapping) else None,
            "feature_count": len(rows),
            "property_names": sorted({key for row in rows for key in row}),
            "sample_properties": rows[:5],
        }
    )
    return out


def station_filter_query(year: int) -> dict[str, Any]:
    params = {
        "f": "json",
        "limit": 100,
        "datetime": f"{year:04d}-01-01T00:00:00Z/{year:04d}-12-31T23:59:59Z",
        "filter-lang": "cql2-text",
        "filter": f"wigos_station_identifier = '{MINANGKABAU_WIGOS}'",
    }
    result = fetch_json(query_url(params))
    inspected = inspect_feature_collection(result)
    inspected["query_strategy"] = "datetime+cql2_station_filter"
    inspected["year"] = year
    return inspected


def bbox_query(year: int) -> dict[str, Any]:
    params = {
        "f": "json",
        "limit": 100,
        "datetime": f"{year:04d}-01-01T00:00:00Z/{year:04d}-12-31T23:59:59Z",
        "bbox": ",".join(str(value) for value in MINANGKABAU_BBOX),
    }
    result = fetch_json(query_url(params))
    inspected = inspect_feature_collection(result)
    inspected["query_strategy"] = "datetime+bbox"
    inspected["year"] = year
    return inspected


def normalize_property_name(value: Any) -> str:
    return str(value or "").strip().casefold().replace(" ", "_")


def precipitation_candidates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for row in rows:
        name = normalize_property_name(row.get("name"))
        description = normalize_property_name(row.get("description"))
        units = normalize_property_name(row.get("units"))
        if any(token in name or token in description for token in ("precip", "rain", "rainfall")):
            candidates.append(row)
        elif units in {"mm", "millimetres", "millimeters", "kg_m-2", "kg_m^-2", "kg_m-2"}:
            candidates.append(row)
    return candidates


def raw_rows_from_query(query: Mapping[str, Any]) -> list[dict[str, Any]]:
    samples = query.get("sample_properties")
    return [dict(row) for row in samples] if isinstance(samples, list) else []


def run_probe() -> dict[str, Any]:
    collection_result = fetch_json(f"{COLLECTION_URL}?f=json")
    queryables_result = fetch_json(f"{QUERYABLES_URL}?f=json")
    schema_result = fetch_json(f"{SCHEMA_URL}?f=json")
    station_result = fetch_json(f"{MINANGKABAU_STATION_URL}?f=json")

    collection_payload = collection_result.get("payload")
    queryables_payload = queryables_result.get("payload")
    station_payload = station_result.get("payload")

    queryable_properties: list[str] = []
    if isinstance(queryables_payload, Mapping):
        properties = queryables_payload.get("properties")
        if isinstance(properties, Mapping):
            queryable_properties = sorted(str(key) for key in properties)

    station_properties: dict[str, Any] = {}
    if isinstance(station_payload, Mapping):
        props = station_payload.get("properties")
        if isinstance(props, Mapping):
            station_properties = dict(props)

    collection_extent: Any = None
    if isinstance(collection_payload, Mapping):
        collection_extent = collection_payload.get("extent")

    anchors: list[dict[str, Any]] = []
    for year in ANCHOR_YEARS:
        primary = station_filter_query(year)
        chosen = primary
        if primary.get("http_status") != 200 or not primary.get("is_feature_collection"):
            fallback = bbox_query(year)
            fallback["fallback_from"] = primary
            chosen = fallback
        rows = raw_rows_from_query(chosen)
        chosen["precipitation_candidates_in_sample"] = precipitation_candidates(rows)
        chosen["sample_wigos_station_identifiers"] = sorted(
            {
                str(row.get("wigos_station_identifier") or "")
                for row in rows
                if row.get("wigos_station_identifier")
            }
        )
        anchors.append(chosen)

    successful_queries = [row for row in anchors if row.get("http_status") == 200 and row.get("is_feature_collection")]
    anchors_with_features = [row for row in successful_queries if int(row.get("feature_count") or 0) > 0]
    earliest_anchor_with_features = min((int(row["year"]) for row in anchors_with_features), default=None)
    recent = next((row for row in anchors if int(row["year"]) == 2025), {})

    station_identity_ok = (
        station_result.get("http_status") == 200
        and station_properties.get("traditional_station_identifier") == "96163"
        and str(station_properties.get("name") or "").upper().find("MINANGKABAU") >= 0
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe_version": 1,
        "authority": "Badan Meteorologi Klimatologi dan Geofisika",
        "source_family": "BMKG WIS2 DayCLI",
        "collection_id": COLLECTION_ID,
        "collection": {
            **public(collection_result),
            "extent": collection_extent,
            "title": collection_payload.get("title") if isinstance(collection_payload, Mapping) else None,
            "description": collection_payload.get("description") if isinstance(collection_payload, Mapping) else None,
            "keywords": collection_payload.get("keywords") if isinstance(collection_payload, Mapping) else None,
        },
        "queryables": {
            **public(queryables_result),
            "property_names": queryable_properties,
        },
        "schema": public(schema_result),
        "minangkabau_station": {
            **public(station_result),
            "wigos_station_identifier": MINANGKABAU_WIGOS,
            "traditional_station_identifier": station_properties.get("traditional_station_identifier"),
            "name": station_properties.get("name"),
            "status": station_properties.get("status"),
            "coordinates": station_payload.get("geometry", {}).get("coordinates") if isinstance(station_payload, Mapping) and isinstance(station_payload.get("geometry"), Mapping) else None,
            "identity_matches_expected": station_identity_ok,
        },
        "anchor_queries": anchors,
        "conclusions": {
            "official_daycli_collection_reachable": collection_result.get("http_status") == 200,
            "queryables_reachable": queryables_result.get("http_status") == 200,
            "schema_reachable": schema_result.get("http_status") == 200,
            "minangkabau_station_identity_qualified": station_identity_ok,
            "standard_station_filtered_query_supported": all(row.get("query_strategy") == "datetime+cql2_station_filter" and row.get("http_status") == 200 for row in anchors),
            "any_anchor_year_has_data": bool(anchors_with_features),
            "earliest_tested_anchor_year_with_data": earliest_anchor_with_features,
            "recent_2025_query_has_data": int(recent.get("feature_count") or 0) > 0,
            "recent_sample_contains_precipitation_candidate": bool(recent.get("precipitation_candidates_in_sample")),
            "historical_station_rainfall_overlap_qualified": False,
            "safe_to_mark_chirps_station_validation_complete": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe BMKG WIS2 DayCLI as a CHIRPS station-validation lane")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = run_probe()
    rendered = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
