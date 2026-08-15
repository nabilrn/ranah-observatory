from __future__ import annotations

import argparse
import hashlib
import json
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

SERVICE = "Peta_Curah_Hujan_dan_Hari_Hujan_"
BASE_REST = f"https://gis.bmkg.go.id/arcgis/rest/services/{SERVICE}/MapServer"
REST_URL = f"{BASE_REST}?f=pjson"
WMS_STANDARD_URL = (
    f"https://gis.bmkg.go.id/arcgis/services/{SERVICE}/MapServer/WMSServer"
    "?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0"
)
WMS_REST_PATH_URL = (
    f"{BASE_REST}/WMSServer?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0"
)


def fetch(url: str, timeout: float = 30.0) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json, application/xml, text/xml, */*",
            "User-Agent": "ranah-observatory/0.1 (+https://github.com/nabilrn/ranah-observatory)",
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


def _json_body(result: Mapping[str, Any]) -> dict[str, Any] | None:
    if result.get("http_status") != 200:
        return None
    body = result.get("body")
    if not isinstance(body, (bytes, bytearray)):
        return None
    try:
        payload = json.loads(bytes(body).decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _extent_summary(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    return {
        key: value.get(key)
        for key in ("xmin", "ymin", "xmax", "ymax", "spatialReference")
        if key in value
    }


def inspect_rest_service(result: Mapping[str, Any]) -> tuple[dict[str, Any], list[int]]:
    public = _public_transport(result)
    payload = _json_body(result)
    public["is_arcgis_map_service_json"] = False
    public["service_metadata"] = {}
    public["declared_layers"] = []
    if payload is None:
        return public, []

    layers = payload.get("layers") if isinstance(payload.get("layers"), list) else []
    declared_layers: list[dict[str, Any]] = []
    ids: list[int] = []
    for layer in layers:
        if not isinstance(layer, Mapping):
            continue
        layer_id = layer.get("id")
        if isinstance(layer_id, int):
            ids.append(layer_id)
        declared_layers.append(
            {
                "id": layer_id,
                "name": layer.get("name"),
                "parentLayerId": layer.get("parentLayerId"),
                "defaultVisibility": layer.get("defaultVisibility"),
                "subLayerIds": layer.get("subLayerIds"),
                "minScale": layer.get("minScale"),
                "maxScale": layer.get("maxScale"),
            }
        )

    public["is_arcgis_map_service_json"] = True
    public["service_metadata"] = {
        "currentVersion": payload.get("currentVersion"),
        "mapName": payload.get("mapName"),
        "serviceDescription": payload.get("serviceDescription"),
        "description": payload.get("description"),
        "copyrightText": payload.get("copyrightText"),
        "supportsDynamicLayers": payload.get("supportsDynamicLayers"),
        "supportedQueryFormats": payload.get("supportedQueryFormats"),
        "supportedImageFormatTypes": payload.get("supportedImageFormatTypes"),
        "capabilities": payload.get("capabilities"),
        "timeInfo": payload.get("timeInfo"),
        "initialExtent": _extent_summary(payload.get("initialExtent")),
        "fullExtent": _extent_summary(payload.get("fullExtent")),
        "units": payload.get("units"),
    }
    public["declared_layers"] = declared_layers
    return public, sorted(set(ids))


def inspect_rest_layer(layer_id: int) -> dict[str, Any]:
    result = fetch(f"{BASE_REST}/{layer_id}?f=pjson")
    public = _public_transport(result)
    public["layer_id"] = layer_id
    payload = _json_body(result)
    public["is_arcgis_layer_json"] = False
    public["metadata"] = {}
    if payload is None:
        return public

    fields = payload.get("fields") if isinstance(payload.get("fields"), list) else []
    public["is_arcgis_layer_json"] = True
    public["metadata"] = {
        "id": payload.get("id", layer_id),
        "name": payload.get("name"),
        "type": payload.get("type"),
        "description": payload.get("description"),
        "copyrightText": payload.get("copyrightText"),
        "geometryType": payload.get("geometryType"),
        "displayField": payload.get("displayField"),
        "defaultVisibility": payload.get("defaultVisibility"),
        "minScale": payload.get("minScale"),
        "maxScale": payload.get("maxScale"),
        "maxRecordCount": payload.get("maxRecordCount"),
        "capabilities": payload.get("capabilities"),
        "supportsStatistics": payload.get("supportsStatistics"),
        "supportsAdvancedQueries": payload.get("supportsAdvancedQueries"),
        "timeInfo": payload.get("timeInfo"),
        "extent": _extent_summary(payload.get("extent")),
        "source": payload.get("source"),
        "subLayers": payload.get("subLayers"),
        "renderer_type": (
            payload.get("drawingInfo", {}).get("renderer", {}).get("type")
            if isinstance(payload.get("drawingInfo"), Mapping)
            and isinstance(payload.get("drawingInfo", {}).get("renderer"), Mapping)
            else None
        ),
        "fields": [
            {
                "name": field.get("name"),
                "alias": field.get("alias"),
                "type": field.get("type"),
            }
            for field in fields
            if isinstance(field, Mapping)
        ],
    }
    return public


def _local_name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _child_text(layer: ET.Element, name: str) -> str:
    for child in layer:
        if _local_name(child) == name:
            return (child.text or "").strip()
    return ""


def _dimension_records(layer: ET.Element) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for child in layer:
        if _local_name(child) not in {"Dimension", "Extent"}:
            continue
        records.append(
            {
                "element": _local_name(child),
                "name": child.attrib.get("name", ""),
                "units": child.attrib.get("units", ""),
                "unitSymbol": child.attrib.get("unitSymbol", ""),
                "default": child.attrib.get("default", ""),
                "multipleValues": child.attrib.get("multipleValues", ""),
                "nearestValue": child.attrib.get("nearestValue", ""),
                "current": child.attrib.get("current", ""),
                "value": (child.text or "").strip(),
            }
        )
    return records


def inspect_wms(result: Mapping[str, Any]) -> dict[str, Any]:
    public = _public_transport(result)
    body = result.get("body")
    public["is_wms_capabilities"] = False
    public["service"] = {}
    public["operations"] = {}
    public["layers"] = []
    if not isinstance(body, (bytes, bytearray)) or result.get("http_status") != 200:
        return public
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return public
    if _local_name(root) not in {"WMS_Capabilities", "WMT_MS_Capabilities"}:
        return public

    service = root.find(".//{*}Service")
    service_data: dict[str, Any] = {}
    if service is not None:
        service_data = {
            "title": _child_text(service, "Title"),
            "abstract": _child_text(service, "Abstract"),
            "fees": _child_text(service, "Fees"),
            "access_constraints": _child_text(service, "AccessConstraints"),
            "max_width": _child_text(service, "MaxWidth"),
            "max_height": _child_text(service, "MaxHeight"),
        }

    operations: dict[str, list[str]] = {}
    request = root.find(".//{*}Capability/{*}Request")
    if request is not None:
        for operation in request:
            op_name = _local_name(operation)
            formats = [
                (child.text or "").strip()
                for child in operation
                if _local_name(child) == "Format" and (child.text or "").strip()
            ]
            operations[op_name] = formats

    layer_records: list[dict[str, Any]] = []
    for layer in root.findall(".//{*}Layer"):
        name = _child_text(layer, "Name")
        if not name:
            continue
        crs = [
            (child.text or "").strip()
            for child in layer
            if _local_name(child) in {"CRS", "SRS"} and (child.text or "").strip()
        ]
        bounding_boxes = [
            dict(child.attrib)
            for child in layer
            if _local_name(child) in {"BoundingBox", "LatLonBoundingBox"}
        ]
        layer_records.append(
            {
                "name": name,
                "title": _child_text(layer, "Title"),
                "abstract": _child_text(layer, "Abstract"),
                "queryable": layer.attrib.get("queryable", ""),
                "opaque": layer.attrib.get("opaque", ""),
                "cascaded": layer.attrib.get("cascaded", ""),
                "crs": crs,
                "dimensions": _dimension_records(layer),
                "bounding_boxes": bounding_boxes,
            }
        )

    public["is_wms_capabilities"] = True
    public["service"] = service_data
    public["operations"] = operations
    public["layers"] = layer_records
    return public


def classify_semantics(
    rest_service: Mapping[str, Any],
    rest_layers: list[Mapping[str, Any]],
    wms: Mapping[str, Any],
) -> dict[str, Any]:
    time_signals: list[dict[str, Any]] = []
    service_time = rest_service.get("service_metadata", {}).get("timeInfo")
    if service_time:
        time_signals.append({"source": "rest_service.timeInfo", "value": service_time})
    for layer in rest_layers:
        layer_time = layer.get("metadata", {}).get("timeInfo")
        if layer_time:
            time_signals.append(
                {
                    "source": f"rest_layer_{layer.get('layer_id')}.timeInfo",
                    "value": layer_time,
                }
            )
    for layer in wms.get("layers", []):
        for dimension in layer.get("dimensions", []):
            if str(dimension.get("name", "")).lower() == "time":
                time_signals.append(
                    {
                        "source": f"wms_layer_{layer.get('name')}.dimension_time",
                        "value": dimension,
                    }
                )

    layer_labels = []
    for layer in rest_layers:
        name = layer.get("metadata", {}).get("name")
        if name:
            layer_labels.append(str(name))
    for layer in wms.get("layers", []):
        title = layer.get("title")
        if title:
            layer_labels.append(str(title))

    if time_signals:
        classification = "accessible_time_dimension_present_needs_period_semantics"
        canonical_suitability = "not_yet_qualified"
        reason = "The service exposes an explicit time signal, but its observation period and aggregation semantics still require qualification."
    else:
        classification = "accessible_no_time_dimension_static_or_current_map"
        canonical_suitability = "not_suitable_as_historical_panel_without_separate_vintage_metadata"
        reason = (
            "The accessible service exposes no ArcGIS timeInfo or WMS TIME dimension. "
            "It may still be a valid map product, but the service itself does not provide a reproducible historical time axis."
        )
    return {
        "classification": classification,
        "canonical_suitability": canonical_suitability,
        "reason": reason,
        "time_signals": time_signals,
        "layer_labels": sorted(set(layer_labels)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Probe accessibility and temporal semantics of the official BMKG rainfall/rainy-day WMS service."
    )
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    raw_rest = fetch(REST_URL)
    rest_service, layer_ids = inspect_rest_service(raw_rest)
    rest_layers = [inspect_rest_layer(layer_id) for layer_id in layer_ids]
    standard = inspect_wms(fetch(WMS_STANDARD_URL))
    rest_path = inspect_wms(fetch(WMS_REST_PATH_URL))
    usable = bool(standard.get("is_wms_capabilities") or rest_path.get("is_wms_capabilities"))
    preferred_wms = standard if standard.get("is_wms_capabilities") else rest_path
    semantics = (
        classify_semantics(rest_service, rest_layers, preferred_wms)
        if usable
        else {
            "classification": "wms_not_accessible_from_hosted_runner",
            "canonical_suitability": "blocked",
            "reason": "No valid WMS GetCapabilities response was available from the hosted runner.",
            "time_signals": [],
            "layer_labels": [],
        }
    )

    payload = {
        "schema": "ranah-observatory/bmkg-wms-probe/v2",
        "retrieved_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "official_registry": "https://gis.bmkg.go.id/portal/dataapi",
        "service_name": SERVICE,
        "registry_declared_format": "WMS",
        "registry_declared_access": "Publik",
        "rest_service": rest_service,
        "rest_layers": rest_layers,
        "wms_standard_endpoint": standard,
        "wms_rest_path_endpoint": rest_path,
        "usable_wms_capabilities": usable,
        "semantics": semantics,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
