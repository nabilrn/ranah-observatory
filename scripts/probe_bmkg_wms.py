from __future__ import annotations

import argparse
import hashlib
import json
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SERVICE = "Peta_Curah_Hujan_dan_Hari_Hujan_"
REST_URL = f"https://gis.bmkg.go.id/arcgis/rest/services/{SERVICE}/MapServer?f=pjson"
WMS_STANDARD_URL = (
    f"https://gis.bmkg.go.id/arcgis/services/{SERVICE}/MapServer/WMSServer"
    "?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0"
)
WMS_REST_PATH_URL = (
    f"https://gis.bmkg.go.id/arcgis/rest/services/{SERVICE}/MapServer/WMSServer"
    "?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0"
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


def inspect_wms(result: dict[str, Any]) -> dict[str, Any]:
    public = {key: value for key, value in result.items() if key != "body"}
    body = result.get("body")
    public["is_wms_capabilities"] = False
    public["service_title"] = ""
    public["layer_count"] = 0
    public["layer_names"] = []
    if not isinstance(body, (bytes, bytearray)) or result.get("http_status") != 200:
        return public
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return public
    local_name = root.tag.rsplit("}", 1)[-1]
    if local_name not in {"WMS_Capabilities", "WMT_MS_Capabilities"}:
        return public
    public["is_wms_capabilities"] = True
    title = root.find(".//{*}Service/{*}Title")
    public["service_title"] = (title.text or "").strip() if title is not None else ""
    names = [
        (element.text or "").strip()
        for element in root.findall(".//{*}Layer/{*}Name")
        if (element.text or "").strip()
    ]
    public["layer_names"] = names
    public["layer_count"] = len(names)
    return public


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe the official BMKG rainfall/rainy-day ArcGIS/WMS service once.")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    rest = fetch(REST_URL)
    standard = inspect_wms(fetch(WMS_STANDARD_URL))
    rest_path = inspect_wms(fetch(WMS_REST_PATH_URL))
    usable = bool(standard.get("is_wms_capabilities") or rest_path.get("is_wms_capabilities"))
    payload = {
        "schema": "ranah-observatory/bmkg-wms-probe/v1",
        "retrieved_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "official_registry": "https://gis.bmkg.go.id/portal/dataapi",
        "service_name": SERVICE,
        "registry_declared_format": "WMS",
        "registry_declared_access": "Publik",
        "rest_endpoint": {key: value for key, value in rest.items() if key != "body"},
        "wms_standard_endpoint": standard,
        "wms_rest_path_endpoint": rest_path,
        "usable_wms_capabilities": usable,
        "classification": "wms_accessible" if usable else "wms_not_accessible_from_hosted_runner",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
