from __future__ import annotations

import argparse
import csv
import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
GEOGRAPHIES = ROOT / "data" / "registries" / "geographies.csv"
BIG_CROSSWALK = ROOT / "data" / "registries" / "big_geography_map.csv"
SERVICE_ROOT = "https://geoservices.big.go.id/rbi/rest/services/BATASWILAYAH/BATAS_KABKOTA_AR/MapServer"
LAYER_URL = f"{SERVICE_ROOT}/0"
EXPECTED_EDITION = "Juni 2026"
USER_AGENT = "ranah-observatory/0.1 (+https://github.com/nabilrn/ranah-observatory)"


def normalize_code(value: Any) -> str:
    return "".join(character for character in str(value or "") if character.isdigit())


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [
            {key: (value or "").strip() for key, value in row.items()}
            for row in csv.DictReader(handle)
        ]


def canonical_sumbar_geographies(path: Path = GEOGRAPHIES) -> dict[str, dict[str, str]]:
    return {
        row["geography_id"]: row
        for row in read_csv(path)
        if row["parent_geography_id"] == "idn.13"
        and row["status"] == "current"
        and row["geography_level"] in {"regency", "city"}
    }


def big_crosswalk(path: Path = BIG_CROSSWALK) -> dict[str, dict[str, str]]:
    return {
        row["source_code_normalized"]: row
        for row in read_csv(path)
        if row["source_edition"] == EXPECTED_EDITION
        and row["mapping_status"] == "qualified_current_crosswalk"
        and row["source_system"] == "Permendagri"
    }


def fetch(url: str, timeout: float = 45.0) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json, application/geo+json, */*",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            return {
                "url": url,
                "reachable": True,
                "http_status": int(getattr(response, "status", 200)),
                "content_type": response.headers.get("Content-Type", ""),
                "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "body": body,
            }
    except urllib.error.HTTPError as exc:
        body = exc.read()
        return {
            "url": url,
            "reachable": True,
            "http_status": exc.code,
            "content_type": exc.headers.get("Content-Type", "") if exc.headers else "",
            "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
            "body_prefix": body[:400].decode("utf-8", errors="replace"),
        }
    except (urllib.error.URLError, TimeoutError) as exc:
        return {
            "url": url,
            "reachable": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def json_body(result: Mapping[str, Any]) -> Any:
    if result.get("http_status") != 200:
        return None
    body = result.get("body")
    if not isinstance(body, (bytes, bytearray)):
        return None
    try:
        return json.loads(bytes(body).decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def public_transport(result: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if key != "body"}


def inspect_service(result: Mapping[str, Any]) -> dict[str, Any]:
    public = public_transport(result)
    payload = json_body(result)
    public.update(
        {
            "is_arcgis_map_service": False,
            "service_description": "",
            "copyright_text": "",
            "spatial_reference_wkid": None,
            "supported_query_formats": "",
            "edition_matches_expected": False,
        }
    )
    if not isinstance(payload, Mapping):
        return public

    spatial_reference = payload.get("spatialReference")
    if not isinstance(spatial_reference, Mapping):
        full_extent = payload.get("fullExtent")
        spatial_reference = (
            full_extent.get("spatialReference", {})
            if isinstance(full_extent, Mapping)
            else {}
        )

    description = str(payload.get("serviceDescription", ""))
    public["is_arcgis_map_service"] = True
    public["service_description"] = description
    public["copyright_text"] = str(payload.get("copyrightText", ""))
    public["spatial_reference_wkid"] = (
        spatial_reference.get("wkid") if isinstance(spatial_reference, Mapping) else None
    )
    public["supported_query_formats"] = str(payload.get("supportedQueryFormats", ""))
    public["edition_matches_expected"] = EXPECTED_EDITION.lower() in description.lower()
    return public


def inspect_layer(result: Mapping[str, Any]) -> dict[str, Any]:
    public = public_transport(result)
    payload = json_body(result)
    public.update(
        {
            "is_polygon_feature_layer": False,
            "name": "",
            "geometry_type": "",
            "max_record_count": None,
            "supported_query_formats": "",
            "required_fields_present": False,
            "field_names": [],
        }
    )
    if not isinstance(payload, Mapping):
        return public

    fields = payload.get("fields") if isinstance(payload.get("fields"), list) else []
    field_names = sorted(
        str(field.get("name"))
        for field in fields
        if isinstance(field, Mapping) and field.get("name")
    )
    required_fields = {
        "KDBBPS",
        "KDPBPS",
        "KDPKAB",
        "KDPPUM",
        "WADMKK",
        "WADMPR",
        "NAMOBJ",
    }
    geometry_type = str(payload.get("geometryType", ""))
    public["is_polygon_feature_layer"] = (
        str(payload.get("type", "")) == "Feature Layer"
        and geometry_type == "esriGeometryPolygon"
    )
    public["name"] = str(payload.get("name", ""))
    public["geometry_type"] = geometry_type
    public["max_record_count"] = payload.get("maxRecordCount")
    public["supported_query_formats"] = str(payload.get("supportedQueryFormats", ""))
    public["required_fields_present"] = required_fields.issubset(set(field_names))
    public["field_names"] = field_names
    return public


def _coordinate_pair_count(value: Any) -> int:
    if not isinstance(value, list):
        return 0
    if len(value) >= 2 and all(isinstance(item, (int, float)) for item in value[:2]):
        return 1
    return sum(_coordinate_pair_count(item) for item in value)


def inspect_geojson(
    result: Mapping[str, Any],
    crosswalk: Mapping[str, Mapping[str, str]],
    canonical: Mapping[str, Mapping[str, str]],
) -> dict[str, Any]:
    public = public_transport(result)
    payload = json_body(result)
    expected_source_codes = set(crosswalk)
    expected_canonical_ids = set(canonical)
    public.update(
        {
            "is_geojson_feature_collection": False,
            "raw_source_feature_count": 0,
            "excluded_non_kabkota_artifact_count": 0,
            "selected_kabkota_count": 0,
            "expected_kabkota_count": len(expected_source_codes),
            "source_permendagri_codes": [],
            "missing_source_codes": sorted(expected_source_codes),
            "unexpected_source_codes": [],
            "duplicate_source_codes": [],
            "mapped_canonical_geography_ids": [],
            "missing_canonical_geography_ids": sorted(expected_canonical_ids),
            "unexpected_canonical_geography_ids": [],
            "name_mismatches": [],
            "source_kdbbps_nonblank_count": 0,
            "source_kdpbps_nonblank_count": 0,
            "source_kdppum_values": [],
            "source_province_names": [],
            "all_selected_features_sumatera_barat": False,
            "all_selected_geometries_polygonal": False,
            "all_selected_geometries_nonempty": False,
            "coordinate_pair_count": 0,
            "source_name_by_permendagri_code": {},
            "canonical_id_by_permendagri_code": {},
            "excluded_artifacts": [],
        }
    )
    if not isinstance(payload, Mapping) or payload.get("type") != "FeatureCollection":
        return public
    features = payload.get("features")
    if not isinstance(features, list):
        return public

    selected: list[tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]] = []
    excluded: list[dict[str, Any]] = []
    raw_kdbbps_nonblank = 0
    raw_kdpbps_nonblank = 0
    raw_province_names: set[str] = set()
    raw_kdppum_values: set[str] = set()

    for feature in features:
        if not isinstance(feature, Mapping):
            excluded.append({"reason": "non_mapping_feature"})
            continue
        properties = (
            feature.get("properties")
            if isinstance(feature.get("properties"), Mapping)
            else {}
        )
        geometry = (
            feature.get("geometry")
            if isinstance(feature.get("geometry"), Mapping)
            else {}
        )
        kdbbps = normalize_code(properties.get("KDBBPS"))
        kdpbps = normalize_code(properties.get("KDPBPS"))
        if kdbbps:
            raw_kdbbps_nonblank += 1
        if kdpbps:
            raw_kdpbps_nonblank += 1
        province_name = str(properties.get("WADMPR") or "").strip()
        if province_name:
            raw_province_names.add(province_name)
        kdppum = normalize_code(properties.get("KDPPUM"))
        if kdppum:
            raw_kdppum_values.add(kdppum)

        source_code = normalize_code(properties.get("KDPKAB"))
        source_name = str(properties.get("WADMKK") or "").strip()
        if not source_code or not source_name:
            excluded.append(
                {
                    "objectid": properties.get("OBJECTID"),
                    "namobj": str(properties.get("NAMOBJ") or "").strip(),
                    "wadmkk": source_name,
                    "kdpkab": str(properties.get("KDPKAB") or "").strip(),
                    "remark": str(properties.get("REMARK") or "").strip(),
                    "metadata": str(properties.get("METADATA") or "").strip(),
                    "reason": "blank_kdpkab_or_wadmkk",
                }
            )
            continue
        selected.append((feature, properties, geometry))

    codes: list[str] = []
    mapped_ids: list[str] = []
    source_names: dict[str, str] = {}
    canonical_by_code: dict[str, str] = {}
    name_mismatches: list[dict[str, str]] = []
    polygonal = True
    nonempty = True
    sumbar = True
    coordinate_pairs = 0

    for _feature, properties, geometry in selected:
        source_code = normalize_code(properties.get("KDPKAB"))
        source_name = str(properties.get("WADMKK") or "").strip()
        province_name = str(properties.get("WADMPR") or "").strip()
        codes.append(source_code)
        source_names[source_code] = source_name
        if province_name.casefold() != "sumatera barat":
            sumbar = False

        mapping = crosswalk.get(source_code)
        if mapping:
            canonical_id = str(mapping.get("canonical_geography_id") or "")
            if canonical_id:
                mapped_ids.append(canonical_id)
                canonical_by_code[source_code] = canonical_id
            expected_name = str(mapping.get("source_name_expected") or "").strip()
            if expected_name and source_name.casefold() != expected_name.casefold():
                name_mismatches.append(
                    {
                        "source_code": source_code,
                        "expected": expected_name,
                        "actual": source_name,
                    }
                )

        geometry_type = str(geometry.get("type", ""))
        if geometry_type not in {"Polygon", "MultiPolygon"}:
            polygonal = False
        count = _coordinate_pair_count(geometry.get("coordinates"))
        coordinate_pairs += count
        if count == 0:
            nonempty = False

    code_counts = Counter(codes)
    source_code_set = set(codes)
    mapped_id_set = set(mapped_ids)
    public["is_geojson_feature_collection"] = True
    public["raw_source_feature_count"] = len(features)
    public["excluded_non_kabkota_artifact_count"] = len(excluded)
    public["selected_kabkota_count"] = len(selected)
    public["source_permendagri_codes"] = sorted(source_code_set)
    public["missing_source_codes"] = sorted(expected_source_codes - source_code_set)
    public["unexpected_source_codes"] = sorted(source_code_set - expected_source_codes)
    public["duplicate_source_codes"] = sorted(
        code for code, count in code_counts.items() if count > 1
    )
    public["mapped_canonical_geography_ids"] = sorted(mapped_id_set)
    public["missing_canonical_geography_ids"] = sorted(
        expected_canonical_ids - mapped_id_set
    )
    public["unexpected_canonical_geography_ids"] = sorted(
        mapped_id_set - expected_canonical_ids
    )
    public["name_mismatches"] = name_mismatches
    public["source_kdbbps_nonblank_count"] = raw_kdbbps_nonblank
    public["source_kdpbps_nonblank_count"] = raw_kdpbps_nonblank
    public["source_kdppum_values"] = sorted(raw_kdppum_values)
    public["source_province_names"] = sorted(raw_province_names)
    public["all_selected_features_sumatera_barat"] = sumbar
    public["all_selected_geometries_polygonal"] = polygonal
    public["all_selected_geometries_nonempty"] = nonempty
    public["coordinate_pair_count"] = coordinate_pairs
    public["source_name_by_permendagri_code"] = dict(sorted(source_names.items()))
    public["canonical_id_by_permendagri_code"] = dict(sorted(canonical_by_code.items()))
    public["excluded_artifacts"] = excluded
    return public


def build_query_url() -> str:
    params = {
        "where": "WADMPR='Sumatera Barat'",
        "outFields": "OBJECTID,NAMOBJ,KDBBPS,KDPBPS,KDPKAB,KDPPUM,WADMKK,WADMPR,LUASWH,TIPADM,REMARK,METADATA,SRS_ID",
        "returnGeometry": "true",
        "returnZ": "false",
        "returnM": "false",
        "outSR": "4326",
        "orderByFields": "OBJECTID ASC",
        "f": "geojson",
    }
    return f"{LAYER_URL}/query?{urllib.parse.urlencode(params)}"


def run_probe(raw_output: Path | None = None) -> dict[str, Any]:
    canonical = canonical_sumbar_geographies()
    crosswalk = big_crosswalk()
    service_result = fetch(f"{SERVICE_ROOT}?f=pjson")
    layer_result = fetch(f"{LAYER_URL}?f=pjson")
    query_result = fetch(build_query_url())

    if (
        raw_output
        and isinstance(query_result.get("body"), (bytes, bytearray))
        and query_result.get("http_status") == 200
    ):
        raw_output.parent.mkdir(parents=True, exist_ok=True)
        raw_output.write_bytes(bytes(query_result["body"]))

    service = inspect_service(service_result)
    layer = inspect_layer(layer_result)
    geojson = inspect_geojson(query_result, crosswalk, canonical)

    qualified = all(
        [
            len(canonical) == 19,
            len(crosswalk) == 19,
            service.get("http_status") == 200,
            service.get("is_arcgis_map_service"),
            service.get("edition_matches_expected"),
            layer.get("http_status") == 200,
            layer.get("is_polygon_feature_layer"),
            layer.get("required_fields_present"),
            "geoJSON" in str(layer.get("supported_query_formats", "")),
            geojson.get("http_status") == 200,
            geojson.get("is_geojson_feature_collection"),
            geojson.get("selected_kabkota_count") == 19,
            not geojson.get("missing_source_codes"),
            not geojson.get("unexpected_source_codes"),
            not geojson.get("duplicate_source_codes"),
            not geojson.get("missing_canonical_geography_ids"),
            not geojson.get("unexpected_canonical_geography_ids"),
            not geojson.get("name_mismatches"),
            geojson.get("all_selected_geometries_polygonal"),
            geojson.get("all_selected_geometries_nonempty"),
            geojson.get("all_selected_features_sumatera_barat"),
        ]
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe_version": 3,
        "authority": "Badan Informasi Geospasial",
        "expected_edition": EXPECTED_EDITION,
        "selection_rule": "query WADMPR=Sumatera Barat; client-side retain nonblank KDPKAB and WADMKK",
        "mapping_rule": "BIG KDPKAB Permendagri/PUM code -> explicit June 2026 BIG crosswalk -> canonical geography_id",
        "service": service,
        "layer": layer,
        "sumatera_barat_geojson": geojson,
        "canonical_geography_count": len(canonical),
        "crosswalk_count": len(crosswalk),
        "conclusions": {
            "official_big_polygon_lane_qualified": qualified,
            "current_sumbar_19_geographies_exactly_covered": qualified,
            "geometry_suitable_for_current_zonal_aggregation_candidate": qualified,
            "bps_fields_usable_as_live_join_key": bool(
                geojson.get("source_kdbbps_nonblank_count")
                or geojson.get("source_kdpbps_nonblank_count")
            ),
            "permendagri_kdpkab_crosswalk_required": True,
            "historical_boundary_continuity_established": False,
            "safe_to_project_current_boundaries_backward_without_harmonization": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Probe BIG current Sumatera Barat kabupaten/kota polygons"
    )
    parser.add_argument("--output", type=Path, help="JSON qualification manifest")
    parser.add_argument("--raw-output", type=Path, help="Raw source GeoJSON snapshot")
    args = parser.parse_args()
    payload = run_probe(args.raw_output)
    rendered = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
