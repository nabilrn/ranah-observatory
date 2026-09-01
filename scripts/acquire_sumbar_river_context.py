#!/usr/bin/env python3
"""Acquire official river-context metadata and a source-native Padang river layer.

Primary source discovery is Satu Data Indonesia's CKAN backend. The script
keeps coverage semantics fail-closed:

* BIG ``Hidrografi_Sungai_25K`` is treated as the preferred national RBI
  reference/service metadata.
* ``sungai_padang_ln_25k`` is frozen only as a Padang-named local layer; it is
  never promoted as province-wide Sumatera Barat coverage.

No river-distance, basin, flood-risk, or causal indicator is derived here.
"""

from __future__ import annotations

import hashlib
import json
import math
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
CKAN_APIS = (
    "https://data.go.id/api/3/action",
    "https://katalog.data.go.id/api/3/action",
)
USER_AGENT = "ranah-observatory/1.0 (+https://github.com/nabilrn/ranah-observatory)"
MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024

OUT_DIR = ROOT / "data/processed/sumbarprov/river_context"
PADANG_GEOJSON = OUT_DIR / "sungai_padang_ln_25k.source.geojson"
MANIFEST = ROOT / "data/manifests/sumbar_river_context.json"

DATASETS = {
    "big_rbi_river_25k": {
        "id": "9d09415b-4d6b-4deb-8313-35b1d548b092",
        "expected_title": "Hidrografi_Sungai_25K",
        "expected_organization": "Badan Informasi Geospasial",
        "mode": "metadata_service_reference",
    },
    "sumbar_padang_river_25k": {
        "id": "00ae1bc2-5b5d-4efc-bb93-1166523188ab",
        "expected_title": "sungai_padang_ln_25k",
        "expected_organization": "Provinsi Sumatera Barat",
        "mode": "freeze_geojson",
    },
}


def normalize(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def request_bytes(url: str, *, timeout: int = 60, max_bytes: int | None = None) -> tuple[bytes, dict[str, str], str]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        final_url = response.geturl()
        headers = {str(k).lower(): str(v) for k, v in response.headers.items()}
        declared = response.headers.get("Content-Length")
        if max_bytes is not None and declared:
            try:
                if int(declared) > max_bytes:
                    raise RuntimeError(f"resource too large from Content-Length: {declared} > {max_bytes}")
            except ValueError:
                pass
        if max_bytes is None:
            data = response.read()
        else:
            data = response.read(max_bytes + 1)
            if len(data) > max_bytes:
                raise RuntimeError(f"resource exceeded download limit of {max_bytes} bytes")
        return data, headers, final_url


def ckan_package_show(dataset_id: str) -> tuple[dict[str, Any], str]:
    errors: list[str] = []
    for api in CKAN_APIS:
        url = f"{api}/package_show?{urllib.parse.urlencode({'id': dataset_id})}"
        try:
            raw, _, _ = request_bytes(url, timeout=60, max_bytes=10 * 1024 * 1024)
            payload = json.loads(raw.decode("utf-8"))
            if payload.get("success") is not True or not isinstance(payload.get("result"), dict):
                raise RuntimeError(f"invalid CKAN response: {payload!r}")
            return payload["result"], api
        except Exception as exc:
            errors.append(f"{api}: {type(exc).__name__}: {exc}")
    raise RuntimeError(f"all CKAN package_show transports failed for {dataset_id}: {' | '.join(errors)}")


def verify_package(package: dict[str, Any], spec: dict[str, str]) -> None:
    title = normalize(package.get("title"))
    if title.casefold() != spec["expected_title"].casefold():
        raise RuntimeError(f"dataset title mismatch: expected={spec['expected_title']!r} actual={title!r}")
    organization = normalize((package.get("organization") or {}).get("title"))
    if organization.casefold() != spec["expected_organization"].casefold():
        raise RuntimeError(
            f"dataset organization mismatch for {title}: expected={spec['expected_organization']!r} actual={organization!r}"
        )


def resource_record(resource: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": resource.get("id"),
        "name": resource.get("name"),
        "format": resource.get("format"),
        "url": resource.get("url"),
        "description": resource.get("description"),
        "mimetype": resource.get("mimetype"),
        "last_modified": resource.get("last_modified") or resource.get("resource_last_modified"),
        "created": resource.get("created"),
    }


def choose_geojson(resources: list[dict[str, Any]], expected_slug: str) -> dict[str, Any]:
    scored: list[tuple[int, dict[str, Any]]] = []
    slug = expected_slug.casefold()
    for resource in resources:
        url = normalize(resource.get("url"))
        name = normalize(resource.get("name"))
        fmt = normalize(resource.get("format")).casefold()
        haystack = f"{name} {url}".casefold()
        score = 0
        if fmt == "geojson":
            score += 100
        elif fmt == "json":
            score += 80
        if name.casefold().endswith(".json") or urllib.parse.urlparse(url).path.casefold().endswith(".json"):
            score += 60
        if slug in haystack:
            score += 30
        if url.startswith("https://"):
            score += 10
        if score:
            scored.append((score, resource))
    scored.sort(key=lambda item: (-item[0], normalize(item[1].get("url"))))
    if not scored:
        raise RuntimeError(f"no GeoJSON/JSON resource found for {expected_slug}")
    top_score = scored[0][0]
    tied = [item[1] for item in scored if item[0] == top_score]
    if len(tied) != 1:
        raise RuntimeError(
            f"ambiguous GeoJSON resource for {expected_slug}: {[normalize(item.get('url')) for item in tied]}"
        )
    return tied[0]


def iter_positions(value: Any) -> Iterable[tuple[float, float]]:
    if isinstance(value, (list, tuple)):
        if len(value) >= 2 and all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in value[:2]):
            x = float(value[0])
            y = float(value[1])
            if math.isfinite(x) and math.isfinite(y):
                yield x, y
            return
        for item in value:
            yield from iter_positions(item)


def geometry_audit(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("type") != "FeatureCollection" or not isinstance(payload.get("features"), list):
        raise RuntimeError("river GeoJSON is not a FeatureCollection")
    features = payload["features"]
    if not features:
        raise RuntimeError("river GeoJSON has no features")

    geometry_types: Counter[str] = Counter()
    property_keys: set[str] = set()
    xs: list[float] = []
    ys: list[float] = []
    null_geometry = 0
    for index, feature in enumerate(features):
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise RuntimeError(f"invalid GeoJSON feature at index {index}")
        properties = feature.get("properties")
        if isinstance(properties, dict):
            property_keys.update(str(key) for key in properties)
        geometry = feature.get("geometry")
        if geometry is None:
            null_geometry += 1
            continue
        if not isinstance(geometry, dict):
            raise RuntimeError(f"invalid geometry at feature {index}")
        geom_type = normalize(geometry.get("type")) or "UNKNOWN"
        geometry_types[geom_type] += 1
        for x, y in iter_positions(geometry.get("coordinates")):
            xs.append(x)
            ys.append(y)

    if null_geometry:
        raise RuntimeError(f"river GeoJSON contains {null_geometry} null geometries")
    if not xs or not ys:
        raise RuntimeError("river GeoJSON has no finite coordinate positions")

    bbox = [min(xs), min(ys), max(xs), max(ys)]
    if not (94 <= bbox[0] <= 110 and 94 <= bbox[2] <= 110 and -8 <= bbox[1] <= 7 and -8 <= bbox[3] <= 7):
        raise RuntimeError(f"river GeoJSON bounding box is outside broad western-Indonesia bounds: {bbox}")

    return {
        "feature_count": len(features),
        "geometry_types": dict(sorted(geometry_types.items())),
        "property_keys": sorted(property_keys),
        "bbox": bbox,
        "crs": payload.get("crs"),
        "null_geometry_count": null_geometry,
    }


def freeze_padang_geojson(package: dict[str, Any]) -> dict[str, Any]:
    resources = list(package.get("resources") or [])
    resource = choose_geojson(resources, DATASETS["sumbar_padang_river_25k"]["expected_title"])
    url = normalize(resource.get("url"))
    if not url.startswith("https://"):
        raise RuntimeError(f"Padang river GeoJSON resource is not HTTPS: {url!r}")
    raw, headers, final_url = request_bytes(url, timeout=120, max_bytes=MAX_DOWNLOAD_BYTES)
    try:
        payload = json.loads(raw.decode("utf-8-sig"))
    except Exception as exc:
        raise RuntimeError(f"Padang river resource did not decode as GeoJSON: {url}") from exc
    audit = geometry_audit(payload)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PADANG_GEOJSON.write_bytes(raw)
    return {
        "resource": resource_record(resource),
        "resolved_url": final_url,
        "content_type": headers.get("content-type"),
        "download_size_bytes": len(raw),
        "download_sha256": sha256_bytes(raw),
        "path": PADANG_GEOJSON.relative_to(ROOT).as_posix(),
        "path_sha256": sha256_path(PADANG_GEOJSON),
        "geometry_audit": audit,
        "coverage_contract": {
            "label": "Padang area as named by source dataset",
            "province_wide": False,
            "administrative_coverage_inferred": False,
            "note": "Dataset name is sungai_padang_ln_25k. It must not be represented as a Sumatera Barat-wide river network without separate coverage evidence.",
        },
    }


def package_manifest(key: str, package: dict[str, Any], spec: dict[str, str], catalog_api: str) -> dict[str, Any]:
    resources = [resource_record(item) for item in package.get("resources") or []]
    result: dict[str, Any] = {
        "key": key,
        "catalog_api": catalog_api,
        "dataset_id": package.get("id") or spec["id"],
        "name": package.get("name"),
        "title": package.get("title"),
        "organization": (package.get("organization") or {}).get("title"),
        "metadata_created": package.get("metadata_created"),
        "metadata_modified": package.get("metadata_modified"),
        "notes": package.get("notes"),
        "tags": [item.get("name") for item in package.get("tags") or [] if isinstance(item, dict)],
        "mode": spec["mode"],
        "resources": resources,
    }
    if key == "big_rbi_river_25k":
        service_resources = [
            item for item in resources
            if normalize(item.get("url")).startswith(("http://", "https://"))
            and any(
                token in f"{normalize(item.get('name'))} {normalize(item.get('description'))} {normalize(item.get('format'))}".casefold()
                for token in ("service", "wfs", "wms", "arcgis", "rbi sungai")
            )
        ]
        result["preferred_role"] = "official_national_rbi_river_reference"
        result["service_resources"] = service_resources
        result["coverage_contract"] = {
            "coverage_claim": "Indonesia reference dataset/service as described by BIG",
            "sumbar_subset_materialized": False,
            "note": "No Sumatera Barat subset is materialized until the service transport and spatial filter are verified reproducibly.",
        }
    elif key == "sumbar_padang_river_25k":
        result["frozen_geojson"] = freeze_padang_geojson(package)
    return result


def main() -> None:
    outputs: list[dict[str, Any]] = []
    for key, spec in DATASETS.items():
        package, catalog_api = ckan_package_show(spec["id"])
        verify_package(package, spec)
        outputs.append(package_manifest(key, package, spec, catalog_api))

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": "ranah-observatory/sumbar-river-context-acquisition/v1",
        "source_catalog": "Satu Data Indonesia",
        "source_api_candidates": list(CKAN_APIS),
        "missing_values_inferred": False,
        "geography_inferred": False,
        "promotion_state": "source_native_and_service_metadata_review_required",
        "datasets": outputs,
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    padang = next(item for item in outputs if item["key"] == "sumbar_padang_river_25k")["frozen_geojson"]
    big = next(item for item in outputs if item["key"] == "big_rbi_river_25k")
    print(json.dumps({
        "manifest": MANIFEST.relative_to(ROOT).as_posix(),
        "catalog_apis_used": sorted({item["catalog_api"] for item in outputs}),
        "big_service_resource_count": len(big.get("service_resources", [])),
        "padang_geojson_features": padang["geometry_audit"]["feature_count"],
        "padang_geojson_geometry_types": padang["geometry_audit"]["geometry_types"],
        "padang_geojson_bbox": padang["geometry_audit"]["bbox"],
        "padang_province_wide": padang["coverage_contract"]["province_wide"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
