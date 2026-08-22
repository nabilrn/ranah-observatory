#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
import urllib.parse
from pathlib import Path
from typing import Any

from scripts import probe_milestone26_population_mapserver_multipoint as base

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "data/manifests/milestone26_population_mapserver_scale_contract.json"
IDENTITY = ROOT / "data/manifests/milestone26_population_mapserver_identity.json"
SEMANTICS = ROOT / "data/manifests/milestone26_population_mapserver_pixel_semantics_amendment.json"
SMALL_BATCH = ROOT / "data/manifests/milestone26_population_mapserver_multipoint.json"
IMAGE_EVIDENCE = ROOT / "data/processed/bnpb/m26_source_qualification/inarisk_population_2020.json"
OUT_DIR = ROOT / "data/processed/bnpb/m26_population_mapserver_scale"
OUT_MANIFEST = ROOT / "data/manifests/milestone26_population_mapserver_scale.json"


class M26PopulationScaleError(RuntimeError):
    pass


def canonical_json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def load_locked_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    identity = json.loads(IDENTITY.read_text(encoding="utf-8"))
    semantics = json.loads(SEMANTICS.read_text(encoding="utf-8"))
    small = json.loads(SMALL_BATCH.read_text(encoding="utf-8"))
    image = json.loads(IMAGE_EVIDENCE.read_text(encoding="utf-8"))
    if contract.get("schema") != "ranah-observatory/milestone26-population-mapserver-scale-contract/v1":
        raise M26PopulationScaleError("unexpected scale contract schema")
    if contract.get("locked_before_live_probe") is not True:
        raise M26PopulationScaleError("scale contract is not locked")
    if contract.get("production_batch_candidate") != 64:
        raise M26PopulationScaleError("production batch candidate drift")
    if identity.get("same_dataset_transport_candidate_qualified") is not True:
        raise M26PopulationScaleError("MapServer identity is not qualified")
    if small.get("gates", {}).get("multipoint_batch_transport_qualified") is not True:
        raise M26PopulationScaleError("small-batch multipoint transport is not qualified")
    if semantics.get("semantic_binding", {}).get("accepted_field_name") != contract.get("accepted_pixel_field"):
        raise M26PopulationScaleError("pixel semantic binding drift")
    for key in (
        "stage1_population_aggregation_authorized",
        "numeric_aggregation_authorized",
        "substantive_value_promotion_authorized",
        "cross_geography_numeric_extraction_authorized",
        "aggregation_semantics_changed",
        "source_family_changed",
        "minimum_valid_fraction_changed",
        "risk_synthesis_authorized",
        "statistical_model_fit_authorized",
        "causal_claim_authorized",
        "monetary_wasted_potential_estimate_authorized",
    ):
        if contract.get(key) is not False:
            raise M26PopulationScaleError(f"invalid locked boundary: {key}")
    return contract, identity, semantics, small, image


def lattice_points(anchor_x: float, anchor_y: float, columns: int, rows: int, step: float = 100.0) -> list[list[float]]:
    return [[anchor_x + col * step, anchor_y + row * step] for row in range(rows) for col in range(columns)]


def build_url(mapserver: str, points: list[list[float]]) -> str:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    geometry = {"points": points, "spatialReference": {"wkid": 3395}}
    params = {
        "geometry": json.dumps(geometry, separators=(",", ":")),
        "geometryType": "esriGeometryMultipoint",
        "sr": "3395",
        "layers": "all:0",
        "tolerance": "1",
        "mapExtent": f"{min(xs)-100:.6f},{min(ys)-100:.6f},{max(xs)+100:.6f},{max(ys)+100:.6f}",
        "imageDisplay": "800,800,96",
        "returnGeometry": "true",
        "f": "json",
    }
    return mapserver.rstrip("/") + "/identify?" + urllib.parse.urlencode(params)


def associate_points(input_points: list[list[float]], parsed_results: list[dict[str, Any]], tolerance: float) -> dict[str, float] | None:
    unmatched = list(range(len(parsed_results)))
    mapping: dict[str, float] = {}
    for source in input_points:
        found = None
        for index in unmatched:
            target = parsed_results[index].get("geometry")
            if not isinstance(target, list) or len(target) != 2:
                continue
            if abs(source[0] - float(target[0])) <= tolerance and abs(source[1] - float(target[1])) <= tolerance:
                found = index
                break
        if found is None:
            return None
        unmatched.remove(found)
        key = f"{source[0]:.6f},{source[1]:.6f}"
        mapping[key] = float(parsed_results[found]["value"])
    return mapping if not unmatched else None


def mappings_equal(left: dict[str, float] | None, right: dict[str, float] | None, tolerance: float) -> bool:
    if left is None or right is None or set(left) != set(right):
        return False
    return all(abs(left[key] - right[key]) <= tolerance for key in left)


def run_attempt(
    *,
    name: str,
    mapserver: str,
    points: list[list[float]],
    field_name: str,
    min_value: float,
    max_value: float,
    geometry_tolerance: float,
) -> dict[str, Any]:
    url = build_url(mapserver, points)
    response = base.request_once(url, timeout=30.0)
    body = response.pop("body")
    path = OUT_DIR / f"{name}.body"
    path.write_bytes(body)
    payload = base.parse_json(body)
    raw_results = payload.get("results") if isinstance(payload, dict) and isinstance(payload.get("results"), list) else []
    parsed = [candidate for row in raw_results if isinstance(row, dict) and (candidate := base.extract_pixel_result(row, field_name)) is not None]
    mapping = associate_points(points, parsed, geometry_tolerance)
    transport_ok = bool(
        response["status"] == 200
        and response["exception_class"] is None
        and isinstance(payload, dict)
        and not isinstance(payload.get("error"), dict)
    )
    count_match = len(raw_results) == len(parsed) == len(points)
    range_match = bool(parsed and all(min_value <= float(row["value"]) <= max_value for row in parsed))
    geometry_match = mapping is not None
    all_gates = bool(transport_ok and count_match and range_match and geometry_match)
    return {
        "name": name,
        "input_point_count": len(points),
        "requested_url_length": len(url),
        "response": {
            **response,
            "body_path": path.relative_to(ROOT).as_posix(),
            "body_bytes": len(body),
            "body_sha256": hashlib.sha256(body).hexdigest(),
            "json_parseable": isinstance(payload, dict),
            "arcgis_error_present": bool(isinstance(payload, dict) and isinstance(payload.get("error"), dict)),
        },
        "raw_result_count": len(raw_results),
        "parsed_pixel_result_count": len(parsed),
        "point_value_mapping": mapping,
        "gates": {
            "transport_ok": transport_ok,
            "result_count_match": count_match,
            "all_values_inside_frozen_range": range_match,
            "one_to_one_result_geometry_match": geometry_match,
            "all_attempt_gates_passed": all_gates,
        },
    }


def run() -> dict[str, Any]:
    contract, identity, semantics, small, image = load_locked_inputs()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    anchor_x = float(identity["pilot"]["center_x"])
    anchor_y = float(identity["pilot"]["center_y"])
    field_name = str(contract["accepted_pixel_field"])
    image_meta = image["primary"]
    min_value = float(image_meta["minValues"][0])
    max_value = float(image_meta["maxValues"][0])
    geometry_tolerance = float(contract["qualification_gates_per_attempt"]["one_to_one_result_geometry_match_to_input_points_within_meters"])
    mapserver = str(contract["candidate_mapserver"])

    attempts: list[dict[str, Any]] = []
    by_size: dict[int, list[dict[str, Any]]] = {}
    for plan in contract["batch_plan"]:
        size = int(plan["batch_size"])
        points = lattice_points(anchor_x, anchor_y, int(plan["shape_columns"]), int(plan["shape_rows"]))
        if len(points) != size:
            raise M26PopulationScaleError(f"batch shape mismatch for {size}")
        for repeat in range(1, int(plan["repeat_count"]) + 1):
            attempt = run_attempt(
                name=f"batch-{size}-attempt-{repeat}",
                mapserver=mapserver,
                points=points,
                field_name=field_name,
                min_value=min_value,
                max_value=max_value,
                geometry_tolerance=geometry_tolerance,
            )
            attempts.append(attempt)
            by_size.setdefault(size, []).append(attempt)

    sixty_four = by_size.get(64, [])
    reproducibility_tolerance = float(contract["reproducibility_gate_64"]["numeric_absolute_tolerance"])
    reproducible_64 = bool(
        len(sixty_four) == 2
        and mappings_equal(sixty_four[0]["point_value_mapping"], sixty_four[1]["point_value_mapping"], reproducibility_tolerance)
    )
    both_64_attempts_pass = bool(len(sixty_four) == 2 and all(row["gates"]["all_attempt_gates_passed"] for row in sixty_four))
    production_batch_qualified = bool(both_64_attempts_pass and reproducible_64)

    summary_by_size: dict[str, Any] = {}
    for size, rows in sorted(by_size.items()):
        summary_by_size[str(size)] = {
            "attempt_count": len(rows),
            "all_attempts_passed": all(row["gates"]["all_attempt_gates_passed"] for row in rows),
            "requested_url_lengths": [row["requested_url_length"] for row in rows],
        }

    manifest = {
        "schema": "ranah-observatory/milestone26-population-mapserver-scale/v1",
        "milestone": 26,
        "stage": "stage1_transport_qualification",
        "contract": {"path": CONTRACT.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(CONTRACT.read_bytes()).hexdigest()},
        "identity_evidence_sha256": hashlib.sha256(IDENTITY.read_bytes()).hexdigest(),
        "semantic_amendment_sha256": hashlib.sha256(SEMANTICS.read_bytes()).hexdigest(),
        "small_batch_evidence_sha256": hashlib.sha256(SMALL_BATCH.read_bytes()).hexdigest(),
        "anchor": [anchor_x, anchor_y],
        "accepted_pixel_field": field_name,
        "frozen_valid_range": [min_value, max_value],
        "attempts": attempts,
        "batch_summary": summary_by_size,
        "reproducibility_64": {
            "tolerance": reproducibility_tolerance,
            "both_attempts_passed": both_64_attempts_pass,
            "point_value_mapping_reproducible": reproducible_64,
        },
        "qualified_production_batch_size": 64 if production_batch_qualified else None,
        "production_batch_transport_qualified": production_batch_qualified,
        "headroom_128_observed_pass": bool(by_size.get(128) and by_size[128][0]["gates"]["all_attempt_gates_passed"]),
        "stage1_population_aggregation_authorized": False,
        "numeric_aggregation_performed": False,
        "substantive_value_promotion_performed": False,
        "cross_geography_numeric_extraction_performed": False,
        "aggregation_semantics_changed": False,
        "source_family_changed": False,
        "risk_synthesis_authorized": False,
        "statistical_model_fit": False,
        "causal_claim_created": False,
        "monetary_wasted_potential_estimated": False,
    }
    OUT_MANIFEST.write_bytes(canonical_json_bytes(manifest))
    return manifest


def main() -> int:
    try:
        manifest = run()
    except Exception as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "batch_summary": manifest["batch_summary"],
        "reproducibility_64": manifest["reproducibility_64"],
        "qualified_production_batch_size": manifest["qualified_production_batch_size"],
        "production_batch_transport_qualified": manifest["production_batch_transport_qualified"],
        "headroom_128_observed_pass": manifest["headroom_128_observed_pass"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
