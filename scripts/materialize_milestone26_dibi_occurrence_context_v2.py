#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

from scripts.materialize_milestone26_dibi_occurrence_context import (
    CONTRACT_PATH,
    REPRESENTATION_AMENDMENT_PATH,
    ROOT,
    acquire_raw,
    csv_numeric,
    load_and_validate_contracts,
    parse_features,
    rel,
    sha256_path,
    write_csv,
    write_json,
)

CROSSWALK_PATH = ROOT / "data/registries/bnpb_geography_map.csv"
CROSSWALK_AMENDMENT_PATH = ROOT / "data/manifests/milestone26_dibi_canonical_crosswalk_amendment.json"
M16_FRAME_PATH = ROOT / "data/analysis/engine/spatial_climate_risk_v1/m16-spatial-component-frame.csv"


class DibiCanonicalizationError(RuntimeError):
    pass


def normalize_source_name(value: str) -> str:
    text = " ".join(value.strip().upper().split())
    text = re.sub(r"^KAB\.\s*", "", text)
    text = re.sub(r"^KABUPATEN\s+", "", text)
    return text


def load_crosswalk() -> dict[int, dict[str, str]]:
    amendment = json.loads(CROSSWALK_AMENDMENT_PATH.read_text(encoding="utf-8"))
    if amendment.get("schema") != "ranah-observatory/milestone26-dibi-canonical-crosswalk-amendment/v1":
        raise DibiCanonicalizationError("unexpected DIBI canonical crosswalk amendment schema")
    for key in (
        "historical_boundary_reconstruction_performed",
        "aggregate_2015_2024_source_values_repartitioned",
        "source_family_changed",
        "source_endpoint_changed",
        "source_layer_changed",
        "source_numeric_fields_changed",
        "source_numeric_values_changed",
        "coverage_changed",
        "claim_type_changed",
        "component_class_changed",
        "cross_field_sum_authorized",
        "cross_field_ratio_authorized",
        "annualization_authorized",
        "imputation_authorized",
        "semantic_interpretation_of_abbreviated_fields_authorized",
        "event_level_record_inference_authorized",
        "observed_impact_inference_authorized",
        "cross_component_temporal_aggregation_authorized",
        "risk_synthesis_authorized",
        "statistical_model_fit_authorized",
        "causal_claim_authorized",
        "monetary_wasted_potential_estimate_authorized",
    ):
        if amendment.get(key) is not False:
            raise DibiCanonicalizationError(f"crosswalk amendment unexpectedly opens scientific boundary: {key}")
    if amendment.get("current_identity_crosswalk_only") is not True:
        raise DibiCanonicalizationError("crosswalk amendment is not identity-only")

    cfg = amendment["authoritative_crosswalk"]
    if cfg.get("path") != rel(CROSSWALK_PATH):
        raise DibiCanonicalizationError("crosswalk path drift")
    with CROSSWALK_PATH.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != int(cfg["expected_row_count"]):
        raise DibiCanonicalizationError(f"BNPB crosswalk row-count drift: {len(rows)}")

    result: dict[int, dict[str, str]] = {}
    for row in rows:
        if row.get("mapping_status") != cfg["required_mapping_status"]:
            raise DibiCanonicalizationError(f"unqualified BNPB crosswalk row: {row}")
        if row.get("source_system") != cfg["required_source_system"]:
            raise DibiCanonicalizationError(f"unexpected BNPB crosswalk source system: {row}")
        start = int(row["applicable_start_year"])
        end = int(row["applicable_end_year"])
        reference_year = int(cfg["required_reference_year"])
        if not start <= reference_year <= end:
            raise DibiCanonicalizationError(f"BNPB crosswalk row does not cover reference year {reference_year}: {row}")
        code = int(row["source_code_normalized"])
        if code in result:
            raise DibiCanonicalizationError(f"duplicate BNPB crosswalk source code: {code}")
        canonical = row["canonical_geography_id"]
        if not re.fullmatch(r"idn\.13\.\d{4}", canonical):
            raise DibiCanonicalizationError(f"invalid canonical geography id: {canonical}")
        result[code] = row
    if len({row["canonical_geography_id"] for row in result.values()}) != 19:
        raise DibiCanonicalizationError("BNPB crosswalk canonical geography ids are not unique")
    return result


def load_expected_canonical_ids() -> set[str]:
    with M16_FRAME_PATH.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 19:
        raise DibiCanonicalizationError("M16 canonical geography frame count drift")
    ids = {row["geography_id"] for row in rows}
    if len(ids) != 19:
        raise DibiCanonicalizationError("M16 canonical geography ids are not unique")
    if {row["spatial_frame"] for row in rows} != {"BIG_June_2026_fixed_current_boundary"}:
        raise DibiCanonicalizationError("M16 canonical geography frame semantic drift")
    return ids


def canonicalize_rows(source_rows: list[dict[str, Any]], crosswalk: dict[int, dict[str, str]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen_canonical: set[str] = set()
    for source in source_rows:
        code = int(source["NO_KAB"])
        mapping = crosswalk.get(code)
        if mapping is None:
            raise DibiCanonicalizationError(f"missing qualified BNPB crosswalk for NO_KAB={code}")
        source_name = normalize_source_name(str(source["NAMA_KAB"]))
        expected_name = normalize_source_name(mapping["source_name_expected"])
        if source_name != expected_name:
            raise DibiCanonicalizationError(
                f"DIBI source-name/crosswalk mismatch for NO_KAB={code}: {source_name!r} != {expected_name!r}"
            )
        canonical_id = mapping["canonical_geography_id"]
        if canonical_id in seen_canonical:
            raise DibiCanonicalizationError(f"duplicate canonical geography after crosswalk: {canonical_id}")
        seen_canonical.add(canonical_id)
        row = dict(source)
        row["geography_id"] = canonical_id
        row["canonical_name"] = mapping["canonical_name"]
        row["bnpb_crosswalk_status"] = mapping["mapping_status"]
        result.append(row)
    return sorted(result, key=lambda row: row["geography_id"])


def build(mode: str) -> dict[str, Any]:
    contract, representation_amendment, qualification_path, transport_amendment_path, metadata_path, transport_amendment = load_and_validate_contracts()
    preferred_path, response_path, sidecar_path, response_payload = acquire_raw(
        contract=contract,
        representation_amendment=representation_amendment,
        transport_amendment=transport_amendment,
        qualification_path=qualification_path,
        transport_amendment_path=transport_amendment_path,
        metadata_path=metadata_path,
        mode=mode,
    )
    source_rows = parse_features(contract, representation_amendment, response_payload)
    crosswalk = load_crosswalk()
    rows = canonicalize_rows(source_rows, crosswalk)
    expected_canonical = load_expected_canonical_ids()
    observed_canonical = {row["geography_id"] for row in rows}
    if observed_canonical != expected_canonical:
        raise DibiCanonicalizationError(
            f"canonical geography set mismatch missing={sorted(expected_canonical-observed_canonical)} extra={sorted(observed_canonical-expected_canonical)}"
        )

    output = contract["output"]
    component_path = ROOT / str(output["component_frame"])
    provenance_path = ROOT / str(output["provenance_frame"])
    manifest_path = ROOT / str(output["manifest"])
    numeric_fields = [str(value) for value in contract["numeric_fields"]["retained_source_native_fields"]]

    component_rows: list[dict[str, Any]] = []
    provenance_rows: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        source_key = int(row["NO_KAB"])
        component: dict[str, Any] = {
            "geography_id": row["geography_id"],
            "canonical_name": row["canonical_name"],
            "NO_PROP": int(row["NO_PROP"]),
            "NO_KAB": source_key,
            "NAMA_PROP": row["NAMA_PROP"],
            "NAMA_KAB": row["NAMA_KAB"],
            "coverage_start_year": int(contract["coverage"]["declared_start_year"]),
            "coverage_end_year": int(contract["coverage"]["declared_end_year"]),
        }
        for field in numeric_fields:
            component[field] = csv_numeric(row[field])
        component.update(
            {
                "source_id": contract["source_id"],
                "component_class": contract["component_class"],
                "claim_type": contract["claim_type"],
                "bnpb_crosswalk_status": row["bnpb_crosswalk_status"],
                "semantic_interpretation_of_abbreviated_field_names_authorized": "false",
                "event_level_record_inference_authorized": "false",
                "observed_impact_inference_authorized": "false",
                "risk_synthesis_authorized": "false",
            }
        )
        component_rows.append(component)
        provenance_rows.append(
            {
                "geography_id": row["geography_id"],
                "canonical_name": row["canonical_name"],
                "source_NO_KAB": source_key,
                "source_NAMA_KAB": row["NAMA_KAB"],
                "source_record_order_after_canonical_sort": index,
                "raw_response_path": rel(response_path),
                "raw_response_sha256": sha256_path(response_path),
                "request_sidecar_path": rel(sidecar_path),
                "request_sidecar_sha256": sha256_path(sidecar_path),
                "preferred_service_status_path": rel(preferred_path),
                "preferred_service_status_sha256": sha256_path(preferred_path),
                "canonical_crosswalk_path": rel(CROSSWALK_PATH),
                "canonical_crosswalk_sha256": sha256_path(CROSSWALK_PATH),
                "canonical_crosswalk_amendment_path": rel(CROSSWALK_AMENDMENT_PATH),
                "canonical_crosswalk_amendment_sha256": sha256_path(CROSSWALK_AMENDMENT_PATH),
                "source_geography_key": "NO_KAB",
                "source_key_assumed_canonical": "false",
                "source_field_semantics_preserved_without_renaming": "true",
            }
        )

    component_fields = [
        "geography_id", "canonical_name", "NO_PROP", "NO_KAB", "NAMA_PROP", "NAMA_KAB",
        "coverage_start_year", "coverage_end_year", *numeric_fields,
        "source_id", "component_class", "claim_type", "bnpb_crosswalk_status",
        "semantic_interpretation_of_abbreviated_field_names_authorized",
        "event_level_record_inference_authorized", "observed_impact_inference_authorized",
        "risk_synthesis_authorized",
    ]
    provenance_fields = [
        "geography_id", "canonical_name", "source_NO_KAB", "source_NAMA_KAB",
        "source_record_order_after_canonical_sort", "raw_response_path", "raw_response_sha256",
        "request_sidecar_path", "request_sidecar_sha256", "preferred_service_status_path",
        "preferred_service_status_sha256", "canonical_crosswalk_path", "canonical_crosswalk_sha256",
        "canonical_crosswalk_amendment_path", "canonical_crosswalk_amendment_sha256",
        "source_geography_key", "source_key_assumed_canonical", "source_field_semantics_preserved_without_renaming",
    ]
    write_csv(component_path, component_fields, component_rows)
    write_csv(provenance_path, provenance_fields, provenance_rows)

    manifest = {
        "schema": "ranah-observatory/milestone26-stage1-dibi-occurrence-context/v2",
        "milestone": 26,
        "stage": "stage1_dibi_recorded_occurrence_context_materialization",
        "source_id": contract["source_id"],
        "component_class": contract["component_class"],
        "claim_type": contract["claim_type"],
        "coverage": contract["coverage"],
        "geography_count": len(component_rows),
        "observation_count": len(component_rows),
        "exact_source_key_set_pass": len({int(row["NO_KAB"]) for row in rows}) == 19,
        "exact_canonical_geography_set_pass": observed_canonical == expected_canonical,
        "source_geography_key": "NO_KAB",
        "source_key_assumed_canonical": False,
        "canonical_crosswalk_applied": True,
        "canonical_crosswalk": {"path": rel(CROSSWALK_PATH), "sha256": sha256_path(CROSSWALK_PATH)},
        "canonical_crosswalk_amendment": {"path": rel(CROSSWALK_AMENDMENT_PATH), "sha256": sha256_path(CROSSWALK_AMENDMENT_PATH)},
        "source_province_filter": "NO_PROP = 13",
        "representation_amendment_applied": True,
        "retained_source_native_numeric_fields": numeric_fields,
        "source_numeric_values_changed_by_crosswalk_correction": False,
        "source_field_renaming_performed": False,
        "cross_field_sum_performed": False,
        "cross_field_ratio_performed": False,
        "annualization_performed": False,
        "imputation_performed": False,
        "semantic_interpretation_of_abbreviated_field_names_performed": False,
        "historical_boundary_reconstruction_performed": False,
        "aggregate_2015_2024_source_values_repartitioned": False,
        "preferred_service_runtime_unavailable_evidence": {"path": rel(preferred_path), "sha256": sha256_path(preferred_path)},
        "transport_fallback_used": True,
        "transport_fallback_authorized": bool(transport_amendment["fallback_authorized_only_when_preferred_endpoint_reports_runtime_unavailable"]),
        "raw_response": {"path": rel(response_path), "sha256": sha256_path(response_path), "bytes": response_path.stat().st_size},
        "request_sidecar": {"path": rel(sidecar_path), "sha256": sha256_path(sidecar_path)},
        "contract": {"path": rel(CONTRACT_PATH), "sha256": sha256_path(CONTRACT_PATH)},
        "representation_amendment": {"path": rel(REPRESENTATION_AMENDMENT_PATH), "sha256": sha256_path(REPRESENTATION_AMENDMENT_PATH)},
        "source_qualification": {"path": rel(qualification_path), "sha256": sha256_path(qualification_path)},
        "transport_amendment": {"path": rel(transport_amendment_path), "sha256": sha256_path(transport_amendment_path)},
        "source_metadata": {"path": rel(metadata_path), "sha256": sha256_path(metadata_path)},
        "outputs": {
            "component_frame": rel(component_path),
            "component_frame_sha256": sha256_path(component_path),
            "provenance_frame": rel(provenance_path),
            "provenance_frame_sha256": sha256_path(provenance_path),
        },
        "offline_rebuild_required": True,
        "live_and_offline_outputs_must_be_byte_identical": True,
        "event_level_record_inference_performed": False,
        "observed_impact_inference_performed": False,
        "substantive_interpretation_performed": False,
        "cross_component_temporal_aggregation_performed": False,
        "risk_synthesis_authorized": False,
        "statistical_model_fit": False,
        "causal_claim_created": False,
        "monetary_wasted_potential_estimated": False,
        "stage1_complete": False
    }
    write_json(manifest_path, manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Re-materialize M26 DIBI occurrence/context using the qualified BNPB canonical crosswalk")
    parser.add_argument("--mode", choices=("live", "offline"), default="offline")
    args = parser.parse_args()
    payload = build(args.mode)
    print(json.dumps({
        "mode": args.mode,
        "geography_count": payload["geography_count"],
        "canonical_crosswalk_applied": payload["canonical_crosswalk_applied"],
        "exact_canonical_geography_set_pass": payload["exact_canonical_geography_set_pass"],
        "component_frame": payload["outputs"]["component_frame"]
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
