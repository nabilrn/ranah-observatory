#!/usr/bin/env python3
"""Read-only qualification probe for the official KLHK 2022 land-cover MapServer.

This script intentionally does not materialize research data. It verifies the
remote service/layer contract and prints a compact machine-readable summary so
we can decide whether the source is safe to promote into the reproducible
research pipeline.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any

SERVICE = "https://geoportal.menlhk.go.id/server/rest/services/SIGAP_Interaktif/Penutupan_Lahan_2022/MapServer"
USER_AGENT = "ranah-observatory/1.0 (+https://github.com/nabilrn/ranah-observatory)"


def fetch_json(url: str, *, timeout: int = 90) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json,text/plain,*/*"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read(10 * 1024 * 1024 + 1)
        if len(raw) > 10 * 1024 * 1024:
            raise RuntimeError(f"response too large from {url}")
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"unexpected JSON payload from {url}")
    if payload.get("error"):
        raise RuntimeError(f"ArcGIS error from {url}: {payload['error']}")
    return payload


def query_count(layer_url: str) -> int:
    params = urllib.parse.urlencode({"where": "1=1", "returnCountOnly": "true", "f": "json"})
    payload = fetch_json(f"{layer_url}/query?{params}")
    count = payload.get("count")
    if not isinstance(count, int) or count <= 0:
        raise RuntimeError(f"invalid record count for {layer_url}: {count!r}")
    return count


def main() -> None:
    root = fetch_json(f"{SERVICE}?f=pjson")
    layers = root.get("layers") or []
    if not layers:
        raise RuntimeError("KLHK 2022 land-cover MapServer exposes no layers")

    root_summary = {
        "service": SERVICE,
        "map_name": root.get("mapName"),
        "service_description": root.get("serviceDescription"),
        "copyright_text": root.get("copyrightText"),
        "spatial_reference": (root.get("spatialReference") or {}).get("wkid"),
        "supported_query_formats": root.get("supportedQueryFormats"),
        "max_record_count": root.get("maxRecordCount"),
        "layer_count": len(layers),
    }
    print(json.dumps({"root": root_summary}, ensure_ascii=False))

    qualified = []
    for layer_ref in layers:
        layer_id = layer_ref.get("id")
        if not isinstance(layer_id, int):
            raise RuntimeError(f"invalid KLHK layer reference: {layer_ref!r}")
        layer_url = f"{SERVICE}/{layer_id}"
        layer = fetch_json(f"{layer_url}?f=pjson")
        fields = [
            {
                "name": field.get("name"),
                "alias": field.get("alias"),
                "type": field.get("type"),
            }
            for field in (layer.get("fields") or [])
        ]
        count = query_count(layer_url)
        renderer = ((layer.get("drawingInfo") or {}).get("renderer") or {})
        summary = {
            "id": layer_id,
            "name": layer.get("name"),
            "type": layer.get("type"),
            "geometry_type": layer.get("geometryType"),
            "display_field": layer.get("displayField"),
            "object_id_field": layer.get("objectIdField"),
            "max_record_count": layer.get("maxRecordCount"),
            "supports_statistics": layer.get("supportsStatistics"),
            "supports_advanced_queries": layer.get("supportsAdvancedQueries"),
            "supported_query_formats": layer.get("supportedQueryFormats"),
            "record_count": count,
            "renderer_type": renderer.get("type"),
            "renderer_field": renderer.get("field1") or renderer.get("field"),
            "fields": fields,
        }
        qualified.append(summary)
        print(json.dumps({"layer": summary}, ensure_ascii=False))

    if not any(item.get("geometry_type") == "esriGeometryPolygon" for item in qualified):
        raise RuntimeError("KLHK land-cover service has no polygon layer")

    print(json.dumps({"qualification": "transport_and_schema_probe_passed", "layers": len(qualified)}))


if __name__ == "__main__":
    main()
