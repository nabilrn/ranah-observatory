from __future__ import annotations

import argparse
import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

USER_AGENT = "ranah-observatory/0.1 (+https://github.com/nabilrn/ranah-observatory)"
FORECAST_BASE = "https://api.bmkg.go.id/publik/prakiraan-cuaca"
NOWCAST_ID = "https://www.bmkg.go.id/alerts/nowcast/id"
EARTHQUAKE_LATEST = "https://data.bmkg.go.id/DataMKG/TEWS/autogempa.json"
DEFAULT_ADM4 = "13.71.01.1001"  # Belakang Pondok, Padang Selatan, Kota Padang


def fetch(url: str, timeout: float = 30.0) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json, application/xml, text/xml, */*",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            status = int(getattr(response, "status", 200))
            content_type = response.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        body = exc.read()
        status = exc.code
        content_type = exc.headers.get("Content-Type", "") if exc.headers else ""
    except (urllib.error.URLError, TimeoutError) as exc:
        return {
            "url": url,
            "reachable": False,
            "error": f"{type(exc).__name__}: {exc}",
        }

    return {
        "url": url,
        "reachable": True,
        "http_status": status,
        "content_type": content_type,
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "body_prefix": body[:240].decode("utf-8", errors="replace"),
        "body": body,
    }


def _public_transport(result: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if key != "body"}


def _json_body(result: Mapping[str, Any]) -> Any:
    if result.get("http_status") != 200:
        return None
    body = result.get("body")
    if not isinstance(body, (bytes, bytearray)):
        return None
    try:
        return json.loads(bytes(body).decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _first_text(element: ET.Element, name: str) -> str:
    for child in element.iter():
        if _local_name(child.tag) == name:
            return (child.text or "").strip()
    return ""


def inspect_forecast(result: Mapping[str, Any], adm4: str) -> dict[str, Any]:
    public = _public_transport(result)
    public.update(
        {
            "source_role": "prospective_forecast_only",
            "adm4_requested": adm4,
            "is_forecast_payload": False,
            "location": {},
            "forecast_record_count": 0,
            "forecast_days": 0,
            "record_keys": [],
            "analysis_dates": [],
        }
    )
    payload = _json_body(result)
    if not isinstance(payload, Mapping):
        return public

    location = payload.get("lokasi") if isinstance(payload.get("lokasi"), Mapping) else {}
    data = payload.get("data") if isinstance(payload.get("data"), list) else []
    daily_groups: list[list[Mapping[str, Any]]] = []
    if data and isinstance(data[0], Mapping):
        cuaca = data[0].get("cuaca")
        if isinstance(cuaca, list):
            for group in cuaca:
                if isinstance(group, list):
                    daily_groups.append([row for row in group if isinstance(row, Mapping)])

    records = [row for group in daily_groups for row in group]
    keys = sorted({str(key) for row in records for key in row.keys()})
    analysis_dates = sorted(
        {
            str(row.get("analysis_date"))
            for row in records
            if row.get("analysis_date") not in (None, "")
        }
    )

    public["is_forecast_payload"] = bool(location and records)
    public["location"] = {
        key: location.get(key)
        for key in (
            "adm1",
            "adm2",
            "adm3",
            "adm4",
            "provinsi",
            "kotkab",
            "kecamatan",
            "desa",
            "lon",
            "lat",
            "timezone",
        )
        if key in location
    }
    public["forecast_record_count"] = len(records)
    public["forecast_days"] = len(daily_groups)
    public["record_keys"] = keys
    public["analysis_dates"] = analysis_dates
    return public


def inspect_nowcast_feed(result: Mapping[str, Any]) -> tuple[dict[str, Any], str | None]:
    public = _public_transport(result)
    public.update(
        {
            "source_role": "active_nowcast_alert_feed",
            "is_rss_or_atom": False,
            "active_alert_count": 0,
            "sumatera_barat_alert_count": 0,
            "sample_item_keys": [],
        }
    )
    body = result.get("body")
    if not isinstance(body, (bytes, bytearray)) or result.get("http_status") != 200:
        return public, None
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return public, None

    root_name = _local_name(root.tag).lower()
    if root_name not in {"rss", "feed"}:
        return public, None

    items = [
        element
        for element in root.iter()
        if _local_name(element.tag).lower() in {"item", "entry"}
    ]
    sumbar_links: list[str] = []
    sample_keys: set[str] = set()
    for item in items:
        child_values: dict[str, str] = {}
        for child in item:
            key = _local_name(child.tag)
            sample_keys.add(key)
            text = (child.text or "").strip()
            if key.lower() == "link" and not text:
                text = child.attrib.get("href", "")
            child_values[key.lower()] = text
        haystack = " ".join(child_values.values()).lower()
        if "sumatera barat" in haystack or "sumbar" in haystack:
            link = child_values.get("link", "")
            if link:
                sumbar_links.append(link)

    public["is_rss_or_atom"] = True
    public["active_alert_count"] = len(items)
    public["sumatera_barat_alert_count"] = len(sumbar_links)
    public["sample_item_keys"] = sorted(sample_keys)
    return public, (sumbar_links[0] if sumbar_links else None)


def inspect_cap_alert(result: Mapping[str, Any]) -> dict[str, Any]:
    public = _public_transport(result)
    public.update(
        {
            "source_role": "active_nowcast_alert_detail",
            "is_cap_alert": False,
            "identifier": "",
            "sender": "",
            "sent": "",
            "status": "",
            "message_type": "",
            "scope": "",
            "events": [],
            "effective_times": [],
            "expiry_times": [],
            "area_count": 0,
            "polygon_count": 0,
            "geocode_names": [],
        }
    )
    body = result.get("body")
    if not isinstance(body, (bytes, bytearray)) or result.get("http_status") != 200:
        return public
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return public
    if _local_name(root.tag).lower() != "alert":
        return public

    infos = [
        element for element in root.iter() if _local_name(element.tag).lower() == "info"
    ]
    areas = [
        element for element in root.iter() if _local_name(element.tag).lower() == "area"
    ]
    polygons = [
        element
        for element in root.iter()
        if _local_name(element.tag).lower() == "polygon"
    ]
    events = sorted({value for info in infos if (value := _first_text(info, "event"))})
    effective = sorted(
        {value for info in infos if (value := _first_text(info, "effective"))}
    )
    expires = sorted(
        {value for info in infos if (value := _first_text(info, "expires"))}
    )
    geocode_names = sorted(
        {
            _first_text(geocode, "valueName")
            for geocode in root.iter()
            if _local_name(geocode.tag).lower() == "geocode"
            and _first_text(geocode, "valueName")
        }
    )

    public["is_cap_alert"] = True
    public["identifier"] = _first_text(root, "identifier")
    public["sender"] = _first_text(root, "sender")
    public["sent"] = _first_text(root, "sent")
    public["status"] = _first_text(root, "status")
    public["message_type"] = _first_text(root, "msgType")
    public["scope"] = _first_text(root, "scope")
    public["events"] = events
    public["effective_times"] = effective
    public["expiry_times"] = expires
    public["area_count"] = len(areas)
    public["polygon_count"] = len(polygons)
    public["geocode_names"] = geocode_names
    return public


def inspect_earthquake(result: Mapping[str, Any]) -> dict[str, Any]:
    public = _public_transport(result)
    public.update(
        {
            "source_role": "latest_event_feed_not_historical_archive",
            "is_earthquake_payload": False,
            "event_count": 0,
            "event_keys": [],
            "event_datetime": "",
            "magnitude": "",
            "coordinates": "",
        }
    )
    payload = _json_body(result)
    if not isinstance(payload, Mapping):
        return public
    info = payload.get("Infogempa")
    if not isinstance(info, Mapping):
        return public
    gempa = info.get("gempa")
    if isinstance(gempa, Mapping):
        records = [gempa]
    elif isinstance(gempa, list):
        records = [row for row in gempa if isinstance(row, Mapping)]
    else:
        records = []
    if not records:
        return public

    first = records[0]
    public["is_earthquake_payload"] = True
    public["event_count"] = len(records)
    public["event_keys"] = sorted(str(key) for key in first.keys())
    public["event_datetime"] = str(first.get("DateTime", ""))
    public["magnitude"] = str(first.get("Magnitude", ""))
    public["coordinates"] = str(
        first.get("Coordinates", first.get("coordinates", ""))
    )
    return public


def run_probe(adm4: str) -> dict[str, Any]:
    forecast_url = f"{FORECAST_BASE}?{urllib.parse.urlencode({'adm4': adm4})}"
    forecast = inspect_forecast(fetch(forecast_url), adm4)
    nowcast_feed, sumbar_cap_url = inspect_nowcast_feed(fetch(NOWCAST_ID))
    cap = None
    if sumbar_cap_url:
        cap = inspect_cap_alert(fetch(sumbar_cap_url))
    earthquake = inspect_earthquake(fetch(EARTHQUAKE_LATEST))

    conclusions = {
        "historical_climate_panel_supported": False,
        "forecast_usable_for_longitudinal_observed_climate": False,
        "nowcast_usable_for_historical_event_counts_without_archiving": False,
        "earthquake_latest_feed_is_complete_historical_archive": False,
        "operational_context_feeds_qualified_when_http_and_shape_checks_pass": all(
            [
                forecast.get("http_status") == 200
                and forecast.get("is_forecast_payload"),
                nowcast_feed.get("http_status") == 200
                and nowcast_feed.get("is_rss_or_atom"),
                earthquake.get("http_status") == 200
                and earthquake.get("is_earthquake_payload"),
            ]
        ),
    }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe_version": 1,
        "forecast": forecast,
        "nowcast_feed": nowcast_feed,
        "sumatera_barat_cap_detail": cap,
        "earthquake_latest": earthquake,
        "conclusions": conclusions,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Probe official BMKG open-data operational feeds"
    )
    parser.add_argument(
        "--adm4",
        default=DEFAULT_ADM4,
        help="Permendagri adm4 code used for forecast probe",
    )
    parser.add_argument(
        "--output", type=Path, help="Optional path to write JSON manifest"
    )
    args = parser.parse_args()

    manifest = run_probe(args.adm4)
    rendered = json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
