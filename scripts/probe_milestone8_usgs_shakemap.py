#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data/snapshots/usgs/milestone8/padang-2009"
MANIFEST_PATH = ROOT / "data/manifests/milestone8_usgs_shakemap_probe.json"
FDSN_QUERY = "https://earthquake.usgs.gov/fdsnws/event/1/query"
USER_AGENT = "ranah-observatory/0.1 (+https://github.com/nabilrn/ranah-observatory)"

EXPECTED_START = "2009-09-30T10:15:00"
EXPECTED_END = "2009-09-30T10:17:30"
EXPECTED_PLACE_TOKEN = "Pariaman"
EXPECTED_MAG_MIN = 7.4
EXPECTED_MAG_MAX = 7.8


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch_bytes(url: str, *, accept: str, timeout: float = 60.0, retries: int = 3) -> tuple[bytes, str, str]:
    errors: list[str] = []
    for attempt in range(retries + 1):
        try:
            request = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read()
                return body, response.geturl(), str(response.headers.get("Content-Type", ""))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            errors.append(f"attempt={attempt + 1} {type(exc).__name__}: {exc}")
            if attempt >= retries:
                break
            time.sleep(1.0 * (2**attempt))
    raise RuntimeError(f"failed to fetch {url}; {' | '.join(errors)}")


def fetch_json(url: str) -> tuple[dict[str, Any], bytes, str]:
    body, final_url, content_type = fetch_bytes(url, accept="application/json,*/*;q=0.8")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"USGS endpoint did not return JSON: content_type={content_type}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("USGS JSON payload is not an object")
    return payload, body, final_url


def write_snapshot(path: Path, body: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    digest = sha256_bytes(body)
    path.with_suffix(path.suffix + ".sha256").write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return digest


def event_query_url() -> str:
    query = urllib.parse.urlencode(
        {
            "format": "geojson",
            "starttime": EXPECTED_START,
            "endtime": EXPECTED_END,
            "minmagnitude": str(EXPECTED_MAG_MIN),
            "orderby": "time-asc",
        }
    )
    return f"{FDSN_QUERY}?{query}"


def qualify_event(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    features = payload.get("features")
    if not isinstance(features, list) or len(features) != 1:
        raise RuntimeError(f"expected exactly one USGS event in locked window, got {0 if not isinstance(features, list) else len(features)}")
    event = features[0]
    if not isinstance(event, Mapping):
        raise RuntimeError("USGS event is not an object")
    props = event.get("properties") if isinstance(event.get("properties"), Mapping) else {}
    mag = float(props.get("mag"))
    place = str(props.get("place", ""))
    event_time_ms = int(props.get("time"))
    event_time = datetime.fromtimestamp(event_time_ms / 1000, tz=timezone.utc)
    if not (EXPECTED_MAG_MIN <= mag <= EXPECTED_MAG_MAX):
        raise RuntimeError(f"unexpected event magnitude {mag}")
    if EXPECTED_PLACE_TOKEN.casefold() not in place.casefold():
        raise RuntimeError(f"unexpected event place {place!r}")
    if event_time.date().isoformat() != "2009-09-30":
        raise RuntimeError(f"unexpected event date {event_time.isoformat()}")
    detail = str(props.get("detail", "")).strip()
    if not detail.startswith("https://earthquake.usgs.gov/"):
        raise RuntimeError("USGS event detail URL missing or unexpected")
    return event


def preferred_shakemap(detail: Mapping[str, Any]) -> Mapping[str, Any]:
    props = detail.get("properties") if isinstance(detail.get("properties"), Mapping) else {}
    products = props.get("products") if isinstance(props.get("products"), Mapping) else {}
    candidates = products.get("shakemap")
    if not isinstance(candidates, list) or not candidates:
        raise RuntimeError("USGS event detail has no ShakeMap product")
    valid = [row for row in candidates if isinstance(row, Mapping) and str(row.get("status", "")).upper() != "DELETE"]
    if not valid:
        raise RuntimeError("USGS event detail has no non-deleted ShakeMap product")
    return max(
        valid,
        key=lambda row: (
            float(row.get("preferredWeight", 0) or 0),
            int(row.get("updateTime", 0) or 0),
        ),
    )


def find_grid_content(product: Mapping[str, Any]) -> tuple[str, Mapping[str, Any]]:
    contents = product.get("contents") if isinstance(product.get("contents"), Mapping) else {}
    preferred_keys = [
        "download/grid.xml",
        "download/grid.xml.zip",
        "download/grid.xyz",
        "download/grid.xyz.zip",
    ]
    for key in preferred_keys:
        row = contents.get(key)
        if isinstance(row, Mapping) and str(row.get("url", "")).startswith("https://"):
            return key, row
    available = sorted(str(key) for key in contents if "grid" in str(key).lower())
    raise RuntimeError(f"preferred ShakeMap product lacks usable motion grid; grid-like contents={available}")


def main() -> int:
    query_url = event_query_url()
    query_payload, query_body, final_query_url = fetch_json(query_url)
    event = qualify_event(query_payload)
    props = event.get("properties") if isinstance(event.get("properties"), Mapping) else {}
    detail_url = str(props["detail"])
    detail_payload, detail_body, final_detail_url = fetch_json(detail_url)

    product = preferred_shakemap(detail_payload)
    content_key, grid_content = find_grid_content(product)
    grid_url = str(grid_content["url"])
    grid_body, final_grid_url, grid_content_type = fetch_bytes(
        grid_url,
        accept="application/xml,application/zip,text/plain,application/octet-stream;q=0.9,*/*;q=0.8",
        timeout=90.0,
        retries=3,
    )
    if len(grid_body) < 10_000:
        raise RuntimeError(f"USGS ShakeMap grid unexpectedly small: {len(grid_body)} bytes")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    query_path = OUT_DIR / "event-query.geojson"
    detail_path = OUT_DIR / "event-detail.geojson"
    extension = ".zip" if grid_body.startswith(b"PK\x03\x04") else ".xml" if grid_body.lstrip().startswith(b"<?xml") else ".dat"
    grid_path = OUT_DIR / f"shakemap-grid{extension}"

    query_hash = write_snapshot(query_path, query_body)
    detail_hash = write_snapshot(detail_path, detail_body)
    grid_hash = write_snapshot(grid_path, grid_body)

    geometry = event.get("geometry") if isinstance(event.get("geometry"), Mapping) else {}
    coordinates = geometry.get("coordinates") if isinstance(geometry.get("coordinates"), list) else []
    manifest = {
        "schema": "ranah-observatory/milestone8-usgs-shakemap-probe/v1",
        "criterion": "one focused causal or quasi-causal case study",
        "source_authority": "U.S. Geological Survey Earthquake Hazards Program",
        "query_url": final_query_url,
        "event_id": event.get("id"),
        "event_title": props.get("title"),
        "event_place": props.get("place"),
        "event_magnitude": props.get("mag"),
        "event_time_utc": datetime.fromtimestamp(int(props["time"]) / 1000, tz=timezone.utc).isoformat(),
        "event_coordinates_lon_lat_depth_km": coordinates,
        "detail_url": final_detail_url,
        "shakemap_source": product.get("source"),
        "shakemap_code": product.get("code"),
        "shakemap_status": product.get("status"),
        "shakemap_preferred_weight": product.get("preferredWeight"),
        "shakemap_update_time": product.get("updateTime"),
        "grid_content_key": content_key,
        "grid_url": final_grid_url,
        "grid_content_type": grid_content_type,
        "event_query_path": str(query_path.relative_to(ROOT)),
        "event_query_sha256": query_hash,
        "event_detail_path": str(detail_path.relative_to(ROOT)),
        "event_detail_sha256": detail_hash,
        "grid_path": str(grid_path.relative_to(ROOT)),
        "grid_sha256": grid_hash,
        "grid_bytes": len(grid_body),
        "physical_exposure_candidate_frozen": True,
        "design_amended": False,
        "exposure_aggregated_to_geographies": False,
        "causal_effect_estimated": False,
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
