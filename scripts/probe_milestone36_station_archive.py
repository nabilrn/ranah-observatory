from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

BMKG_BASE = "https://wis2node.bmkg.go.id/oapi"
WIGOS_ID = "0-20000-0-96163"
TRADITIONAL_ID = "96163"
BMKG_CURRENT_STATION_URL = f"{BMKG_BASE}/collections/stations/items/{WIGOS_ID}?f=json"

NCEI_DATA = "https://www.ncei.noaa.gov/access/services/data/v1"
NCEI_SEARCH = "https://www.ncei.noaa.gov/access/services/search/v1/data"
GHCN_ID = "IDM00096163"
GSOD_ID = "96163099999"
TARGET_YEARS = (1997, 1998)

# BMKG Regulation No. 20/2014 lists 96163 PADANG/TABING at 00 53 00 S,
# 100 21 00 E. The source coordinates are rounded to minutes, so a 0.04°
# guard covers that rounding while excluding the modern Minangkabau site.
HISTORICAL_LAT = -(53.0 / 60.0)
HISTORICAL_LON = 100.0 + 21.0 / 60.0
MAX_IDENTITY_DISTANCE_DEG = 0.04

# Closed PR #20 live-qualified this current WIS2 identity on 2026-08-16.
# It is retained as prior repository evidence because BMKG may return 403 to
# hosted runners intermittently. A fresh recheck is diagnostic, not required to
# re-establish the already-documented site-history break.
PRIOR_CURRENT_STATION_EVIDENCE = {
    "repository_pr": 20,
    "wigos_station_identifier": WIGOS_ID,
    "traditional_station_identifier": TRADITIONAL_ID,
    "name": "PADANG PARIAMAN/MINANGKABAU",
    "identity_qualified": True,
    "observation_transport_qualified": False,
}

USER_AGENT = "ranah-observatory-m36/1 (+https://github.com/nabilrn/ranah-observatory)"


def fetch(url: str, *, headers: Mapping[str, str] | None = None, timeout: float = 45.0) -> dict[str, Any]:
    request_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json,text/csv,text/plain,*/*",
    }
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(url, headers=request_headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            return {
                "url": url,
                "reachable": True,
                "http_status": int(getattr(response, "status", 200)),
                "content_type": response.headers.get("Content-Type", ""),
                "content_range": response.headers.get("Content-Range"),
                "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "body": body,
            }
    except urllib.error.HTTPError as exc:
        body = exc.read()
        return {
            "url": url,
            "reachable": True,
            "http_status": int(exc.code),
            "content_type": exc.headers.get("Content-Type", "") if exc.headers else "",
            "content_range": exc.headers.get("Content-Range") if exc.headers else None,
            "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
            "body": body,
            "error": f"HTTPError: {exc}",
        }
    except (urllib.error.URLError, TimeoutError) as exc:
        return {
            "url": url,
            "reachable": False,
            "http_status": None,
            "error": f"{type(exc).__name__}: {exc}",
            "body": b"",
        }


def public(result: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if key != "body"}


def parse_json_body(result: Mapping[str, Any]) -> Any:
    body = result.get("body")
    if not isinstance(body, (bytes, bytearray)) or not body:
        return None
    try:
        return json.loads(bytes(body).decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def ncei_url(base: str, params: Mapping[str, Any]) -> str:
    return f"{base}?{urllib.parse.urlencode(params, doseq=True)}"


def as_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def normalize_name(value: Any) -> str:
    return " ".join(str(value or "").upper().replace("/", " ").replace("_", " ").split())


def historical_name_ok(value: Any) -> bool:
    # NCEI GSOD uses the shorter alias "TABING, ID" for the historical site.
    # Exact WMO/GSOD identifier plus tight coordinate agreement remain required.
    return "TABING" in normalize_name(value)


def coordinate_ok(lat: Any, lon: Any) -> bool:
    lat_f = as_float(lat)
    lon_f = as_float(lon)
    if lat_f is None or lon_f is None:
        return False
    return abs(lat_f - HISTORICAL_LAT) <= MAX_IDENTITY_DISTANCE_DEG and abs(lon_f - HISTORICAL_LON) <= MAX_IDENTITY_DISTANCE_DEG


def mapping_value(row: Mapping[str, Any], *names: str) -> Any:
    index = {str(key).upper(): value for key, value in row.items()}
    for name in names:
        if name.upper() in index:
            return index[name.upper()]
    return None


def probe_current_bmkg_station() -> dict[str, Any]:
    result = fetch(BMKG_CURRENT_STATION_URL)
    payload = parse_json_body(result)
    props: Mapping[str, Any] = {}
    geometry: Mapping[str, Any] = {}
    if isinstance(payload, Mapping):
        raw_props = payload.get("properties")
        raw_geometry = payload.get("geometry")
        if isinstance(raw_props, Mapping):
            props = raw_props
        if isinstance(raw_geometry, Mapping):
            geometry = raw_geometry
    coords = geometry.get("coordinates")
    current_name = props.get("name")
    traditional = props.get("traditional_station_identifier")
    live_identity_ok = (
        result.get("http_status") == 200
        and str(traditional) == TRADITIONAL_ID
        and "MINANGKABAU" in normalize_name(current_name)
    )
    return {
        **public(result),
        "wigos_station_identifier": WIGOS_ID,
        "traditional_station_identifier": traditional,
        "name": current_name,
        "status": props.get("status"),
        "coordinates": coords,
        "live_current_minangkabau_identity_qualified": live_identity_ok,
        "prior_repository_current_identity": PRIOR_CURRENT_STATION_EVIDENCE,
        "historical_padang_tabing_identity_expected": {
            "traditional_station_identifier": TRADITIONAL_ID,
            "name": "PADANG/TABING",
            "latitude": HISTORICAL_LAT,
            "longitude": HISTORICAL_LON,
            "source": "BMKG Regulation No. 20/2014 Data Policy, Annex II station list",
        },
        "station_history_break_guard_triggered": PRIOR_CURRENT_STATION_EVIDENCE["identity_qualified"],
    }


def probe_ghcn_search() -> dict[str, Any]:
    params = {
        "dataset": "daily-summaries",
        "stations": GHCN_ID,
        "startDate": "1997-01-01T00:00:00",
        "endDate": "1998-12-31T23:59:59",
        "dataTypes": "PRCP",
        "limit": 10,
        "offset": 0,
    }
    result = fetch(ncei_url(NCEI_SEARCH, params))
    payload = parse_json_body(result)
    results: Sequence[Any] = []
    if isinstance(payload, Mapping) and isinstance(payload.get("results"), list):
        results = payload["results"]
    serialized = json.dumps(payload, sort_keys=True) if payload is not None else ""
    return {
        **public(result),
        "candidate_station_id": GHCN_ID,
        "result_count": len(results),
        "candidate_id_present_in_metadata": GHCN_ID in serialized,
        "coverage_metadata_available": bool(results),
        "metadata_sample": list(results[:3]),
    }


def probe_ghcn_identity_sample() -> dict[str, Any]:
    params = {
        "dataset": "daily-summaries",
        "stations": GHCN_ID,
        "startDate": "1997-01-01",
        "endDate": "1997-01-31",
        "dataTypes": "PRCP",
        "includeStationName": "true",
        "includeStationLocation": 1,
        "units": "metric",
        "format": "json",
    }
    result = fetch(ncei_url(NCEI_DATA, params))
    payload = parse_json_body(result)
    rows = payload if isinstance(payload, list) else []
    identities: list[dict[str, Any]] = []
    for raw in rows:
        if not isinstance(raw, Mapping):
            continue
        identities.append(
            {
                "station": mapping_value(raw, "STATION"),
                "name": mapping_value(raw, "NAME"),
                "latitude": mapping_value(raw, "LATITUDE"),
                "longitude": mapping_value(raw, "LONGITUDE"),
                "date": mapping_value(raw, "DATE"),
            }
        )
    unique = {
        (str(row.get("station")), str(row.get("name")), str(row.get("latitude")), str(row.get("longitude")))
        for row in identities
    }
    qualified = bool(identities) and all(
        str(row.get("station")) == GHCN_ID
        and historical_name_ok(row.get("name"))
        and coordinate_ok(row.get("latitude"), row.get("longitude"))
        for row in identities
    )
    return {
        **public(result),
        "candidate_station_id": GHCN_ID,
        "row_count": len(rows),
        "identity_rows_examined": len(identities),
        "unique_station_identity_count": len(unique),
        "identity_sample": identities[:5],
        "precipitation_values_inspected": False,
        "historical_padang_tabing_identity_qualified": qualified,
    }


def probe_gsod_year(year: int) -> dict[str, Any]:
    url = f"https://www.ncei.noaa.gov/data/global-summary-of-the-day/access/{year}/{GSOD_ID}.csv"
    result = fetch(url, headers={"Range": "bytes=0-16383"})
    body = result.get("body")
    rows: list[dict[str, str]] = []
    if result.get("http_status") in {200, 206} and isinstance(body, (bytes, bytearray)) and body:
        text = bytes(body).decode("utf-8-sig", errors="replace")
        try:
            reader = csv.DictReader(io.StringIO(text))
            for raw in reader:
                if raw:
                    rows.append(dict(raw))
                if len(rows) >= 3:
                    break
        except csv.Error:
            rows = []
    identities: list[dict[str, Any]] = []
    for raw in rows:
        identities.append(
            {
                "station": mapping_value(raw, "STATION"),
                "name": mapping_value(raw, "NAME"),
                "latitude": mapping_value(raw, "LATITUDE"),
                "longitude": mapping_value(raw, "LONGITUDE"),
                "date": mapping_value(raw, "DATE"),
            }
        )
    qualified = bool(identities) and all(
        str(row.get("station")) == GSOD_ID
        and historical_name_ok(row.get("name"))
        and coordinate_ok(row.get("latitude"), row.get("longitude"))
        and str(row.get("date") or "").startswith(str(year))
        for row in identities
    )
    return {
        **public(result),
        "year": year,
        "candidate_station_id": GSOD_ID,
        "identity_sample": identities,
        "precipitation_values_inspected": False,
        "historical_padang_tabing_identity_qualified": qualified,
    }


def run_probe() -> dict[str, Any]:
    bmkg = probe_current_bmkg_station()
    ghcn_search = probe_ghcn_search()
    ghcn_identity = probe_ghcn_identity_sample()
    gsod = [probe_gsod_year(year) for year in TARGET_YEARS]

    gsod_identity_ok = all(row.get("historical_padang_tabing_identity_qualified") is True for row in gsod)
    ghcn_identity_ok = ghcn_identity.get("historical_padang_tabing_identity_qualified") is True
    ghcn_coverage_hint = ghcn_search.get("coverage_metadata_available") is True

    accepted_representation: str | None = None
    if ghcn_identity_ok and ghcn_coverage_hint:
        accepted_representation = "ncei_daily_summaries_ghcn_IDM00096163"
    elif gsod_identity_ok:
        accepted_representation = "ncei_gsod_96163099999"

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schema": "ranah-observatory/milestone36-stage0-station-archive-probe/v1",
        "target_station": {
            "traditional_wmo_identifier": TRADITIONAL_ID,
            "historical_identity_required": "PADANG/TABING (NCEI alias TABING accepted only with exact ID + coordinate guard)",
            "target_years": list(TARGET_YEARS),
        },
        "locked_candidate_order": [GHCN_ID, GSOD_ID],
        "bmkg_current_station": bmkg,
        "ncei_daily_summaries_search": ghcn_search,
        "ncei_daily_summaries_identity_sample": ghcn_identity,
        "ncei_gsod_identity_samples": gsod,
        "conclusions": {
            "station_history_break_guard_triggered": bmkg.get("station_history_break_guard_triggered") is True,
            "live_bmkg_current_identity_recheck_qualified": bmkg.get("live_current_minangkabau_identity_qualified") is True,
            "ghcn_historical_identity_qualified": ghcn_identity_ok,
            "ghcn_1997_1998_coverage_metadata_available": ghcn_coverage_hint,
            "gsod_historical_identity_qualified_both_years": gsod_identity_ok,
            "accepted_stage1_representation": accepted_representation,
            "stage1_numeric_inspection_authorized": accepted_representation is not None,
            "precipitation_values_inspected_in_stage0": False,
            "safe_to_mark_chirps_station_validation_complete": False,
            "safe_to_merge_96163_across_station_history": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="M36 Stage 0 historical Padang/Tabing archive probe")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run_probe()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload["conclusions"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
