#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from scripts import build_milestone26_population_stats_geometry as stats_geom
from scripts import materialize_milestone26_stage1_components as stage1
from scripts import probe_milestone26_population_stats_equivalence as equiv

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "data/manifests/milestone26_population_production_contract.json"
PARTITIONS = ROOT / "data/manifests/milestone26_population_stats_partitions.json"
EQUIVALENCE = ROOT / "data/manifests/milestone26_population_stats_equivalence.json"
SOURCE_META = ROOT / "data/processed/bnpb/m26_source_qualification/inarisk_population_2020.json"
FRAME = ROOT / "data/analysis/engine/disaster_risk_chain_v1/m26-stage1-population-component.csv"
PROVENANCE = ROOT / "data/analysis/engine/disaster_risk_chain_v1/m26-stage1-population-provenance.csv"
MANIFEST = ROOT / "data/manifests/milestone26_stage1_population_component.json"
RAW_ROOT = ROOT / "data/processed/bnpb/m26_population_component_stats"
RETRIEVAL_INDEX = RAW_ROOT / "retrieval-index.json"

FRAME_FIELDS = [
    "geography_id",
    "geography_name",
    "source_permendagri_code",
    "spatial_frame",
    "population_reference_year",
    "population_exposure_proxy_2020_persons",
    "population_inside_pixel_count",
    "population_valid_pixel_count",
    "population_valid_fraction",
    "population_partition_count",
    "transport",
    "claim_type",
    "risk_synthesis_authorized",
]

PROVENANCE_FIELDS = [
    "provenance_id",
    "source_id",
    "component_class",
    "geography_id",
    "reference_year",
    "aggregation",
    "transport",
    "partition_count",
    "source_service_url",
    "source_metadata_path",
    "source_metadata_sha256",
    "semantic_evidence_path",
    "semantic_evidence_sha256",
    "partition_manifest_path",
    "partition_manifest_sha256",
    "equivalence_manifest_path",
    "equivalence_manifest_sha256",
    "retrieval_index_path",
    "retrieval_index_sha256",
]


class M26PopulationProductionError(RuntimeError):
    pass


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def csv_bytes(fields: list[str], rows: list[dict[str, Any]]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field, "") for field in fields})
    return buffer.getvalue().encode("utf-8")


def load_contract() -> dict[str, Any]:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if contract.get("schema") != "ranah-observatory/milestone26-population-production-contract/v1":
        raise M26PopulationProductionError("unexpected population production contract schema")
    if contract.get("contract_locked_before_cross_geography_numeric_extraction") is not True:
        raise M26PopulationProductionError("population production contract was not pre-locked")
    if contract.get("source_id") != "inarisk_population_2020":
        raise M26PopulationProductionError("population source id drift")
    if int(contract.get("geography_count_expected", 0)) != 19:
        raise M26PopulationProductionError("population geography count contract drift")
    if contract.get("stage1_population_production_extraction_authorized") is not True:
        raise M26PopulationProductionError("population production extraction is not authorized")
    if contract.get("component_value_materialization_authorized") is not True:
        raise M26PopulationProductionError("population component materialization is not authorized")
    if contract.get("cross_geography_numeric_source_extraction_authorized") is not True:
        raise M26PopulationProductionError("cross-geography population extraction is not authorized")
    for key in (
        "substantive_interpretation_authorized",
        "cross_component_temporal_aggregation_authorized",
        "risk_synthesis_authorized",
        "statistical_model_fit_authorized",
        "causal_claim_authorized",
        "monetary_wasted_potential_estimate_authorized",
        "source_family_changed",
        "aggregation_semantics_changed",
        "minimum_valid_fraction_changed",
    ):
        if contract.get(key) is not False:
            raise M26PopulationProductionError(f"invalid production boundary: {key}")
    aggregation = contract["aggregation"]
    if float(aggregation.get("minimum_valid_fraction_inside_geography", -1)) != 0.99:
        raise M26PopulationProductionError("population valid-fraction gate drift")
    for key in (
        "downsampling_authorized",
        "upsampling_authorized",
        "mean_as_population_total_authorized",
        "area_weighted_density_integration_authorized",
        "imputation_authorized",
    ):
        if aggregation.get(key) is not False:
            raise M26PopulationProductionError(f"invalid aggregation authorization: {key}")
    return contract


def load_frozen_inputs(contract: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    partitions = json.loads(PARTITIONS.read_text(encoding="utf-8"))
    equivalence = json.loads(EQUIVALENCE.read_text(encoding="utf-8"))
    source_meta = json.loads(SOURCE_META.read_text(encoding="utf-8"))

    part_contract = contract["partition_contract"]
    if partitions.get("geography_count") != 19:
        raise M26PopulationProductionError("partition geography count drift")
    if partitions.get("total_partition_count") != int(part_contract["partition_count_expected"]):
        raise M26PopulationProductionError("partition count drift")
    if partitions.get("total_inside_boundary_native_cell_count") != int(part_contract["inside_native_cell_count_expected"]):
        raise M26PopulationProductionError("inside native cell count drift")
    if partitions.get("all_partition_cell_counts_exact") is not True:
        raise M26PopulationProductionError("partition cell counts are not exact")
    if partitions.get("all_partition_urls_within_gate") is not True:
        raise M26PopulationProductionError("partition URL gate is not frozen qualified")

    transport = contract["transport_qualification"]
    required_flag = str(transport["required_flag"])
    if equivalence.get(required_flag) is not bool(transport["required_value"]):
        raise M26PopulationProductionError("population statistics equivalence is not frozen qualified")
    if equivalence.get("statistics_transport_equivalent_on_complete_pilot") is not True:
        raise M26PopulationProductionError("complete pilot equivalence did not pass")
    if equivalence.get("stage1_population_production_extraction_authorized") is not False:
        raise M26PopulationProductionError("equivalence probe must not self-authorize production")

    primary = source_meta.get("primary")
    if not isinstance(primary, dict):
        raise M26PopulationProductionError("population source metadata missing primary payload")
    source_transport = contract["source_transport"]
    if int(primary.get("spatialReference", {}).get("wkid", 0)) != int(source_transport["native_grid_crs_epsg"]):
        raise M26PopulationProductionError("population source CRS drift")
    if float(primary.get("pixelSizeX", 0)) != 100.0 or float(primary.get("pixelSizeY", 0)) != 100.0:
        raise M26PopulationProductionError("population native pixel size drift")
    if float(primary["minValues"][0]) != float(source_transport["frozen_valid_value_min"]):
        raise M26PopulationProductionError("population source min-value drift")
    if float(primary["maxValues"][0]) != float(source_transport["frozen_valid_value_max"]):
        raise M26PopulationProductionError("population source max-value drift")
    return partitions, equivalence, source_meta


def request_bytes(url: str, *, timeout: float = 60.0, attempts: int = 3) -> bytes:
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "ranah-observatory/0.1 (+https://github.com/nabilrn/ranah-observatory)",
                    "Accept": "text/html,application/xhtml+xml,*/*",
                },
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                if int(response.status) != 200:
                    raise M26PopulationProductionError(f"HTTP {response.status}: {url}")
                return response.read()
        except (urllib.error.URLError, TimeoutError, M26PopulationProductionError) as exc:
            last = exc
            if attempt < attempts:
                time.sleep(float(2 ** (attempt - 1)))
    raise M26PopulationProductionError(f"request failed after {attempts} attempts: {url}") from last


def ensure_semantic_evidence(contract: dict[str, Any], fetch_live: bool) -> dict[str, Any]:
    spec = contract["semantic_evidence"]
    path = ROOT / str(spec["frozen_path"])
    if fetch_live:
        body = request_bytes(str(spec["url"]))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    if not path.exists():
        raise M26PopulationProductionError("frozen population semantic evidence is missing")
    body = path.read_bytes()
    normalized = stage1.normalize_text(body)
    required = stage1.normalize_phrase(str(spec["required_phrase"]))
    if required not in normalized:
        raise M26PopulationProductionError("required population grid-cell semantic phrase not found")
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(body).hexdigest(),
        "source_url": str(spec["url"]),
        "evidence_role": str(spec["evidence_role"]),
    }


def raw_path(geography_id: str, partition_index: int) -> Path:
    return RAW_ROOT / geography_id / f"partition-{partition_index:04d}.json"


def fetch_all_partitions(contract: dict[str, Any], partitions: dict[str, Any]) -> None:
    service = str(contract["source_transport"]["service"])
    url_gate = int(contract["partition_contract"]["maximum_encoded_get_url_length"])
    index_rows: list[dict[str, Any]] = []
    RAW_ROOT.mkdir(parents=True, exist_ok=True)

    for geography in sorted(partitions["geographies"], key=lambda row: row["geography_id"]):
        gid = str(geography["geography_id"])
        for partition in sorted(geography["partitions"], key=lambda row: int(row["partition_index"])):
            partition_index = int(partition["partition_index"])
            geometry = partition["candidate"]["arcgis_geometry"]
            url = stats_geom.stats_url(service, geometry)
            if len(url) > url_gate:
                raise M26PopulationProductionError(f"partition URL exceeds locked gate: {gid}/{partition_index}")
            response, payload, attempts_used = equiv.request_json_with_retries(url, timeout=30.0, attempts=3)
            body = response.get("body")
            if not isinstance(body, bytes):
                raise M26PopulationProductionError("statistics response body is not bytes")
            path = raw_path(gid, partition_index)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
            index_rows.append({
                "geography_id": gid,
                "partition_index": partition_index,
                "selected_cell_count": int(partition["selected_cell_count"]),
                "requested_url": url,
                "requested_url_length": len(url),
                "status": int(response["status"]),
                "content_type": str(response.get("content_type", "")),
                "attempts_used": attempts_used,
                "raw_path": path.relative_to(ROOT).as_posix(),
                "raw_sha256": hashlib.sha256(body).hexdigest(),
                "raw_bytes": len(body),
            })

    expected = int(contract["partition_contract"]["partition_count_expected"])
    if len(index_rows) != expected:
        raise M26PopulationProductionError(f"retrieval index count mismatch: {len(index_rows)} != {expected}")
    RETRIEVAL_INDEX.write_bytes(canonical_json_bytes({
        "schema": "ranah-observatory/milestone26-population-retrieval-index/v1",
        "source_id": contract["source_id"],
        "response_count": len(index_rows),
        "responses": index_rows,
    }))


def load_retrieval_index(contract: dict[str, Any]) -> tuple[dict[str, Any], dict[tuple[str, int], dict[str, Any]]]:
    if not RETRIEVAL_INDEX.exists():
        raise M26PopulationProductionError("population retrieval index is missing")
    index = json.loads(RETRIEVAL_INDEX.read_text(encoding="utf-8"))
    if index.get("schema") != "ranah-observatory/milestone26-population-retrieval-index/v1":
        raise M26PopulationProductionError("unexpected population retrieval index schema")
    expected = int(contract["partition_contract"]["partition_count_expected"])
    if index.get("response_count") != expected or len(index.get("responses", [])) != expected:
        raise M26PopulationProductionError("population retrieval index response count drift")
    mapping: dict[tuple[str, int], dict[str, Any]] = {}
    for row in index["responses"]:
        key = (str(row["geography_id"]), int(row["partition_index"]))
        if key in mapping:
            raise M26PopulationProductionError(f"duplicate retrieval index key: {key}")
        path = ROOT / str(row["raw_path"])
        if not path.exists():
            raise M26PopulationProductionError(f"missing frozen statistics response: {path}")
        body = path.read_bytes()
        if hashlib.sha256(body).hexdigest() != row["raw_sha256"]:
            raise M26PopulationProductionError(f"statistics response SHA drift: {path}")
        if len(body) != int(row["raw_bytes"]):
            raise M26PopulationProductionError(f"statistics response byte count drift: {path}")
        mapping[key] = row
    return index, mapping


def parse_frozen_stats(
    contract: dict[str, Any], retrieval_row: dict[str, Any], selected_cell_count: int
) -> dict[str, Any]:
    path = ROOT / str(retrieval_row["raw_path"])
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise M26PopulationProductionError(f"frozen statistics response is not JSON: {path}") from exc
    if isinstance(payload, dict) and payload.get("error"):
        raise M26PopulationProductionError(f"frozen statistics response contains ArcGIS error: {path}")
    required = set(contract["source_transport"]["required_statistics_fields"])
    stats = equiv.parse_statistics(payload, required)
    if stats["skipX"] != int(contract["source_transport"]["skipX_required"]):
        raise M26PopulationProductionError(f"skipX drift: {path}")
    if stats["skipY"] != int(contract["source_transport"]["skipY_required"]):
        raise M26PopulationProductionError(f"skipY drift: {path}")
    value_min = float(contract["source_transport"]["frozen_valid_value_min"])
    value_max = float(contract["source_transport"]["frozen_valid_value_max"])
    if stats["min"] < value_min - 1e-12 or stats["max"] > value_max + 1e-12:
        raise M26PopulationProductionError(f"statistics value range drift: {path}")
    if stats["count"] < 0 or stats["count"] > selected_cell_count:
        raise M26PopulationProductionError(f"statistics count outside partition cell count: {path}")
    return stats


def stable_provenance_id(geography_id: str, contract_sha: str, retrieval_index_sha: str) -> str:
    token = f"inarisk_population_2020|{geography_id}|{contract_sha}|{retrieval_index_sha}"
    return "m26pop_" + hashlib.sha256(token.encode("utf-8")).hexdigest()[:24]


def build_outputs(contract: dict[str, Any], partitions: dict[str, Any], equivalence: dict[str, Any], semantic: dict[str, Any]) -> dict[str, Any]:
    retrieval_index, retrieval_map = load_retrieval_index(contract)
    retrieval_index_sha = sha256_path(RETRIEVAL_INDEX)
    contract_sha = sha256_path(CONTRACT)
    partition_sha = sha256_path(PARTITIONS)
    equivalence_sha = sha256_path(EQUIVALENCE)
    source_meta_sha = sha256_path(SOURCE_META)
    minimum_fraction = float(contract["aggregation"]["minimum_valid_fraction_inside_geography"])
    decimal_places = int(contract["output"]["primary_value_decimal_places"])

    frame_rows: list[dict[str, Any]] = []
    provenance_rows: list[dict[str, Any]] = []
    raw_total_bytes = 0
    valid_cell_total = 0
    inside_cell_total = 0

    for geography in sorted(partitions["geographies"], key=lambda row: row["geography_id"]):
        gid = str(geography["geography_id"])
        partition_stats: list[dict[str, Any]] = []
        inside_count = 0
        for partition in sorted(geography["partitions"], key=lambda row: int(row["partition_index"])):
            partition_index = int(partition["partition_index"])
            selected_cell_count = int(partition["selected_cell_count"])
            row = retrieval_map.get((gid, partition_index))
            if row is None:
                raise M26PopulationProductionError(f"missing retrieval for partition: {gid}/{partition_index}")
            if int(row["selected_cell_count"]) != selected_cell_count:
                raise M26PopulationProductionError(f"retrieval selected-cell count drift: {gid}/{partition_index}")
            expected_url = stats_geom.stats_url(str(contract["source_transport"]["service"]), partition["candidate"]["arcgis_geometry"])
            if row["requested_url"] != expected_url:
                raise M26PopulationProductionError(f"retrieval URL drift: {gid}/{partition_index}")
            partition_stats.append(parse_frozen_stats(contract, row, selected_cell_count))
            inside_count += selected_cell_count
            raw_total_bytes += int(row["raw_bytes"])

        if inside_count != int(geography["inside_boundary_native_cell_count"]):
            raise M26PopulationProductionError(f"inside-cell count drift for {gid}")
        valid_count = sum(int(row["count"]) for row in partition_stats)
        population_sum = math.fsum(float(row["sum"]) for row in partition_stats)
        valid_fraction = valid_count / inside_count if inside_count else 0.0
        if valid_count <= 0 or valid_fraction < minimum_fraction:
            raise M26PopulationProductionError(f"population valid-fraction gate failed for {gid}: {valid_fraction}")
        if not math.isfinite(population_sum) or population_sum < 0.0:
            raise M26PopulationProductionError(f"invalid population exposure proxy aggregate for {gid}")

        inside_cell_total += inside_count
        valid_cell_total += valid_count
        frame_rows.append({
            "geography_id": gid,
            "geography_name": geography.get("geography_name", ""),
            "source_permendagri_code": geography.get("source_permendagri_code", ""),
            "spatial_frame": contract["spatial_frame"],
            "population_reference_year": contract["reference_year"],
            "population_exposure_proxy_2020_persons": f"{population_sum:.{decimal_places}f}",
            "population_inside_pixel_count": inside_count,
            "population_valid_pixel_count": valid_count,
            "population_valid_fraction": f"{valid_fraction:.9f}",
            "population_partition_count": len(partition_stats),
            "transport": "ImageServer_computeStatisticsHistograms_exact_native_mask_partitions",
            "claim_type": contract["claim_type"],
            "risk_synthesis_authorized": "false",
        })
        provenance_rows.append({
            "provenance_id": stable_provenance_id(gid, contract_sha, retrieval_index_sha),
            "source_id": contract["source_id"],
            "component_class": contract["component_class"],
            "geography_id": gid,
            "reference_year": contract["reference_year"],
            "aggregation": contract["aggregation"]["estimand"],
            "transport": "ImageServer_computeStatisticsHistograms_exact_native_mask_partitions",
            "partition_count": len(partition_stats),
            "source_service_url": contract["source_transport"]["service"],
            "source_metadata_path": SOURCE_META.relative_to(ROOT).as_posix(),
            "source_metadata_sha256": source_meta_sha,
            "semantic_evidence_path": semantic["path"],
            "semantic_evidence_sha256": semantic["sha256"],
            "partition_manifest_path": PARTITIONS.relative_to(ROOT).as_posix(),
            "partition_manifest_sha256": partition_sha,
            "equivalence_manifest_path": EQUIVALENCE.relative_to(ROOT).as_posix(),
            "equivalence_manifest_sha256": equivalence_sha,
            "retrieval_index_path": RETRIEVAL_INDEX.relative_to(ROOT).as_posix(),
            "retrieval_index_sha256": retrieval_index_sha,
        })

    if len(frame_rows) != int(contract["geography_count_expected"]):
        raise M26PopulationProductionError("population component geography count mismatch")
    if len({row["geography_id"] for row in frame_rows}) != len(frame_rows):
        raise M26PopulationProductionError("duplicate population component geography id")
    if inside_cell_total != int(contract["partition_contract"]["inside_native_cell_count_expected"]):
        raise M26PopulationProductionError("population total inside-cell count mismatch")

    FRAME.parent.mkdir(parents=True, exist_ok=True)
    FRAME.write_bytes(csv_bytes(FRAME_FIELDS, frame_rows))
    PROVENANCE.write_bytes(csv_bytes(PROVENANCE_FIELDS, provenance_rows))

    manifest = {
        "schema": "ranah-observatory/milestone26-stage1-population-component/v1",
        "milestone": 26,
        "stage": "stage1_population_component_materialization",
        "source_id": contract["source_id"],
        "component_class": contract["component_class"],
        "claim_type": contract["claim_type"],
        "reference_year": contract["reference_year"],
        "spatial_frame": contract["spatial_frame"],
        "geography_count": len(frame_rows),
        "observation_count": len(frame_rows),
        "partition_count": int(retrieval_index["response_count"]),
        "inside_native_cell_count": inside_cell_total,
        "valid_native_cell_count": valid_cell_total,
        "minimum_valid_fraction_required": minimum_fraction,
        "all_geographies_valid_fraction_pass": all(float(row["population_valid_fraction"]) >= minimum_fraction for row in frame_rows),
        "transport": "ImageServer_computeStatisticsHistograms_exact_native_mask_partitions",
        "transport_equivalence_qualified": equivalence.get("population_stats_production_transport_candidate_qualified") is True,
        "contract": {"path": CONTRACT.relative_to(ROOT).as_posix(), "sha256": contract_sha},
        "partition_manifest": {"path": PARTITIONS.relative_to(ROOT).as_posix(), "sha256": partition_sha},
        "equivalence_manifest": {"path": EQUIVALENCE.relative_to(ROOT).as_posix(), "sha256": equivalence_sha},
        "source_metadata": {"path": SOURCE_META.relative_to(ROOT).as_posix(), "sha256": source_meta_sha},
        "semantic_evidence": semantic,
        "retrieval_index": {"path": RETRIEVAL_INDEX.relative_to(ROOT).as_posix(), "sha256": retrieval_index_sha},
        "raw_response_count": int(retrieval_index["response_count"]),
        "raw_response_total_bytes": raw_total_bytes,
        "outputs": {
            "component_frame": FRAME.relative_to(ROOT).as_posix(),
            "component_frame_sha256": sha256_path(FRAME),
            "provenance_frame": PROVENANCE.relative_to(ROOT).as_posix(),
            "provenance_frame_sha256": sha256_path(PROVENANCE),
        },
        "population_component_materialized": True,
        "stage1_complete": False,
        "capacity_component_materialized_in_this_run": False,
        "substantive_interpretation_performed": False,
        "cross_component_temporal_aggregation_performed": False,
        "risk_synthesis_authorized": False,
        "statistical_model_fit": False,
        "causal_claim_created": False,
        "monetary_wasted_potential_estimated": False,
    }
    MANIFEST.write_bytes(canonical_json_bytes(manifest))
    return manifest


def build(fetch_live: bool) -> dict[str, Any]:
    contract = load_contract()
    partitions, equivalence, _source_meta = load_frozen_inputs(contract)
    semantic = ensure_semantic_evidence(contract, fetch_live)
    if fetch_live:
        fetch_all_partitions(contract, partitions)
    return build_outputs(contract, partitions, equivalence, semantic)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch", action="store_true", help="fetch and freeze the 420 qualified ImageServer statistics responses")
    args = parser.parse_args()
    try:
        manifest = build(fetch_live=args.fetch)
    except (
        OSError,
        ValueError,
        KeyError,
        json.JSONDecodeError,
        M26PopulationProductionError,
        equiv.M26PopulationStatsEquivalenceError,
        stage1.M26Stage1Error,
    ) as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "population_component_materialized": manifest["population_component_materialized"],
        "geography_count": manifest["geography_count"],
        "partition_count": manifest["partition_count"],
        "inside_native_cell_count": manifest["inside_native_cell_count"],
        "all_geographies_valid_fraction_pass": manifest["all_geographies_valid_fraction_pass"],
        "stage1_complete": manifest["stage1_complete"],
        "risk_synthesis_authorized": manifest["risk_synthesis_authorized"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
