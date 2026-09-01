#!/usr/bin/env python3
"""Read-only qualification probe for official forestry land-cover sources.

The legacy KLHK Geoportal MapServer is authoritative but may not resolve from
GitHub-hosted runners. This probe therefore separates source authority from
transport reproducibility and also tests the current Kementerian Kehutanan SIGAP
publication portal plus the historical NFMS download route.

Nothing is materialized or committed by this script.
"""

from __future__ import annotations

import json
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from html import unescape
from typing import Any

MAP_SERVICE = "https://geoportal.menlhk.go.id/server/rest/services/SIGAP_Interaktif/Penutupan_Lahan_2022/MapServer"
CURRENT_PORTAL = "https://sigap.kehutanan.go.id/dok-elektronik"
NFMS_2023_TABLE = "https://nfms.menlhk.go.id/download/tabel-luas-penutupan-lahan-tahun-2023-per-kabupaten"
USER_AGENT = "ranah-observatory/1.0 (+https://github.com/nabilrn/ranah-observatory)"
MAX_BYTES = 10 * 1024 * 1024


def request_bytes(url: str, *, timeout: int = 90, limit: int = MAX_BYTES) -> tuple[bytes, dict[str, str], str]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json,text/html,text/plain,*/*"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read(limit + 1)
        if len(raw) > limit:
            raise RuntimeError(f"response too large from {url}")
        headers = {str(k).lower(): str(v) for k, v in response.headers.items()}
        return raw, headers, response.geturl()


def fetch_json(url: str, *, timeout: int = 90) -> dict[str, Any]:
    raw, _, _ = request_bytes(url, timeout=timeout)
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"unexpected JSON payload from {url}")
    if payload.get("error"):
        raise RuntimeError(f"ArcGIS error from {url}: {payload['error']}")
    return payload


def transport_probe(url: str) -> dict[str, Any]:
    host = urllib.parse.urlparse(url).hostname or ""
    result: dict[str, Any] = {"url": url, "host": host}
    try:
        result["resolved_addresses"] = sorted({item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)})
    except OSError as exc:
        result["dns_error"] = repr(exc)
    try:
        raw, headers, final_url = request_bytes(url, timeout=60, limit=2 * 1024 * 1024)
        result.update(
            {
                "transport": "ok",
                "final_url": final_url,
                "status_bytes_read": len(raw),
                "content_type": headers.get("content-type"),
                "content_disposition": headers.get("content-disposition"),
                "preview": raw[:160].decode("utf-8", errors="replace").replace("\n", " "),
            }
        )
    except Exception as exc:  # qualification output, not silent fallback
        result["transport"] = "failed"
        result["transport_error"] = repr(exc)
    return result


def extract_candidate_links(html: str, base_url: str) -> list[str]:
    links = []
    for raw_href in re.findall(r"href\s*=\s*[\"']([^\"']+)[\"']", html, flags=re.I):
        href = unescape(raw_href).strip()
        if not href or href.startswith(("#", "javascript:", "mailto:")):
            continue
        absolute = urllib.parse.urljoin(base_url, href)
        lower = absolute.casefold()
        if any(token in lower for token in ("penutupan", "rekalkulasi", "deforestasi", "download", "dokumen")):
            links.append(absolute)
    return sorted(set(links))


def probe_current_portal() -> dict[str, Any]:
    raw, headers, final_url = request_bytes(CURRENT_PORTAL, timeout=90)
    html = raw.decode("utf-8", errors="replace")
    return {
        "url": CURRENT_PORTAL,
        "final_url": final_url,
        "content_type": headers.get("content-type"),
        "bytes": len(raw),
        "mentions_2022_recalculation": "Rekalkulasi Penutupan Lahan Tahun 2022".casefold() in html.casefold(),
        "mentions_2023_recalculation": "Rekalkulasi Penutupan Lahan Indonesia Tahun 2023".casefold() in html.casefold(),
        "candidate_links": extract_candidate_links(html, final_url)[:80],
    }


def query_count(layer_url: str) -> int:
    params = urllib.parse.urlencode({"where": "1=1", "returnCountOnly": "true", "f": "json"})
    payload = fetch_json(f"{layer_url}/query?{params}")
    count = payload.get("count")
    if not isinstance(count, int) or count <= 0:
        raise RuntimeError(f"invalid record count for {layer_url}: {count!r}")
    return count


def probe_map_service() -> dict[str, Any]:
    root = fetch_json(f"{MAP_SERVICE}?f=pjson")
    layers = root.get("layers") or []
    if not layers:
        raise RuntimeError("KLHK 2022 land-cover MapServer exposes no layers")

    output = {
        "root": {
            "service": MAP_SERVICE,
            "map_name": root.get("mapName"),
            "service_description": root.get("serviceDescription"),
            "copyright_text": root.get("copyrightText"),
            "spatial_reference": (root.get("spatialReference") or {}).get("wkid"),
            "supported_query_formats": root.get("supportedQueryFormats"),
            "max_record_count": root.get("maxRecordCount"),
            "layer_count": len(layers),
        },
        "layers": [],
    }
    for layer_ref in layers:
        layer_id = layer_ref.get("id")
        if not isinstance(layer_id, int):
            raise RuntimeError(f"invalid KLHK layer reference: {layer_ref!r}")
        layer_url = f"{MAP_SERVICE}/{layer_id}"
        layer = fetch_json(f"{layer_url}?f=pjson")
        renderer = ((layer.get("drawingInfo") or {}).get("renderer") or {})
        output["layers"].append(
            {
                "id": layer_id,
                "name": layer.get("name"),
                "geometry_type": layer.get("geometryType"),
                "display_field": layer.get("displayField"),
                "object_id_field": layer.get("objectIdField"),
                "max_record_count": layer.get("maxRecordCount"),
                "supports_statistics": layer.get("supportsStatistics"),
                "supports_advanced_queries": layer.get("supportsAdvancedQueries"),
                "supported_query_formats": layer.get("supportedQueryFormats"),
                "record_count": query_count(layer_url),
                "renderer_type": renderer.get("type"),
                "renderer_field": renderer.get("field1") or renderer.get("field"),
                "fields": [
                    {"name": field.get("name"), "alias": field.get("alias"), "type": field.get("type")}
                    for field in (layer.get("fields") or [])
                ],
            }
        )
    return output


def main() -> None:
    transports = [transport_probe(url) for url in (CURRENT_PORTAL, NFMS_2023_TABLE, MAP_SERVICE)]
    print(json.dumps({"transport_matrix": transports}, ensure_ascii=False))

    current_ok = next(item for item in transports if item["url"] == CURRENT_PORTAL).get("transport") == "ok"
    if current_ok:
        try:
            print(json.dumps({"current_portal": probe_current_portal()}, ensure_ascii=False))
        except Exception as exc:
            print(json.dumps({"current_portal_error": repr(exc)}, ensure_ascii=False))

    map_ok = next(item for item in transports if item["url"] == MAP_SERVICE).get("transport") == "ok"
    if map_ok:
        try:
            print(json.dumps({"map_service": probe_map_service()}, ensure_ascii=False))
        except Exception as exc:
            print(json.dumps({"map_service_error": repr(exc)}, ensure_ascii=False))

    reproducible_paths = [item["url"] for item in transports if item.get("transport") == "ok"]
    if not reproducible_paths:
        raise RuntimeError("no official forestry land-cover transport path is reproducible from GitHub Actions")
    print(json.dumps({"qualification": "at_least_one_official_transport_path_passed", "reproducible_paths": reproducible_paths}))


if __name__ == "__main__":
    main()
