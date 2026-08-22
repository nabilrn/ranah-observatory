#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "data/analysis/engine/investment_realization_v1/m27-bkpm-resource-inventory.csv"
SEMANTIC_AUDIT = ROOT / "data/analysis/engine/investment_realization_v1/m27-bkpm-semantic-audit.csv"
MANIFEST = ROOT / "data/manifests/milestone27_bkpm_resource_inventory.json"
SEMANTIC_CONTRACT = ROOT / "data/manifests/milestone27_quarter_semantics_contract.json"


class AuditError(RuntimeError):
    pass


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def clean_text(value: str) -> str:
    value = html.unescape(value).replace("\xa0", " ")
    return re.sub(r"\s+", " ", value).strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [{k: (v or "") for k, v in row.items()} for row in csv.DictReader(handle)]


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def extract_resource_identity(raw: str) -> tuple[str, str]:
    match = re.search(
        r'<h6[^>]*>\s*([^<\r\n]+?)\s*<small[^>]*>\s*\((CSV|JSON|XLSX|XLS)\)\s*</small>',
        raw,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        raise AuditError("resource identity block not found")
    return clean_text(match.group(1)), match.group(2).upper()


def extract_download_action(raw: str) -> tuple[str, str]:
    matches = re.findall(
        r"handleUnduhDisclamer\(event,\s*'file',\s*'([0-9a-fA-F-]{36})',\s*([0-9]+)\)",
        raw,
        flags=re.IGNORECASE,
    )
    unique = sorted(set(matches))
    if len(unique) != 1:
        raise AuditError(f"expected exactly one file download action, found {unique!r}")
    return unique[0]


def semantic_states(raw: str, year: int, quarter: str) -> dict[str, bool]:
    text = clean_text(re.sub(r"<[^>]+>", " ", raw))
    period_description = bool(re.search(
        rf"hasil agregasi dari realisasi investasi sepanjang tahun\s+{year}\s+triwulan\s+{re.escape(quarter)}\b",
        text,
        flags=re.IGNORECASE,
    ))
    lkpm = "Laporan Kegiatan Penanaman Modal (LKPM)".lower() in text.lower()
    period_field = bool(re.search(
        r"periode\s*:\s*Periode dari data yang disajikan\s*\(sudah dikelompokan berdasarkan tahun dan triwulan\)",
        text,
        flags=re.IGNORECASE,
    ))
    rupiah = bool(re.search(
        r"investasi_rp_juta\s*:\s*Nilai tambahan realisasi dari laporan LKPM yang disajikan dalam satuan Juta Rupiah",
        text,
        flags=re.IGNORECASE,
    ))
    usd = bool(re.search(
        r"investasi_us_ribu\s*:\s*Nilai tambahan realisasi dari laporan LKPM yang disajikan dalam satuan Ribu US Dolar",
        text,
        flags=re.IGNORECASE,
    ))
    update_quarterly = bool(re.search(r"Frekuensi Update Konten\s+Triwulanan", text, flags=re.IGNORECASE))
    collection_quarterly = bool(re.search(r"Frekuensi Pengumpulan\s+Triwulanan", text, flags=re.IGNORECASE))
    return {
        "description_period_match": period_description,
        "lkpm_source_identity_match": lkpm,
        "period_field_semantics_match": period_field,
        "rupiah_increment_semantics_match": rupiah,
        "usd_increment_semantics_match": usd,
        "update_frequency_quarterly_match": update_quarterly,
        "collection_frequency_quarterly_match": collection_quarterly,
    }


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    contract = json.loads(SEMANTIC_CONTRACT.read_text(encoding="utf-8"))
    if manifest.get("schema") not in {
        "ranah-observatory/milestone27-bkpm-resource-inventory/v1",
        "ranah-observatory/milestone27-bkpm-resource-inventory/v2",
    }:
        raise AuditError("unexpected inventory manifest schema")
    if contract.get("schema") != "ranah-observatory/milestone27-quarter-semantics-contract/v1":
        raise AuditError("unexpected semantic contract schema")
    if contract.get("contract_locked_before_inventory_coverage_results_reviewed") is not True:
        raise AuditError("semantic contract was not locked before coverage review")
    if manifest.get("candidate_detail_count") != 64 or manifest.get("distinct_period_count") != 64:
        raise AuditError("frozen inventory does not contain exact 64 period candidates")
    if manifest.get("missing_period_count") != 0 or manifest.get("duplicate_period_count") != 0:
        raise AuditError("frozen inventory period coverage is not exact")
    if manifest.get("target_investment_values_inspected") is not False:
        raise AuditError("target values were inspected before semantic audit")

    rows = read_csv(INVENTORY)
    if len(rows) != 64:
        raise AuditError(f"expected 64 inventory rows, found {len(rows)}")
    evidence_by_period = {
        (int(item["year"]), str(item["quarter"])): item
        for item in manifest["detail_evidence"]
    }
    if len(evidence_by_period) != 64:
        raise AuditError("detail evidence period key is not unique")

    corrected_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    download_action_pairs: set[tuple[str, str]] = set()
    semantic_match_count = 0

    new_fields = list(rows[0].keys())
    for field in (
        "resource_download_action_file_uuid",
        "resource_download_action_record_id",
        "resource_download_action_count",
        "resource_transport_endpoint_resolved",
        "semantic_family_state",
    ):
        if field not in new_fields:
            new_fields.append(field)

    for row in rows:
        year = int(row["year"])
        quarter = row["quarter"]
        evidence = evidence_by_period.get((year, quarter))
        if evidence is None:
            raise AuditError(f"missing frozen detail evidence for {year} Q{row['quarter_number']}")
        raw_path = ROOT / evidence["raw_path"]
        if sha256_path(raw_path) != evidence["raw_sha256"]:
            raise AuditError(f"frozen detail checksum drift: {rel(raw_path)}")
        raw = raw_path.read_text(encoding="utf-8", errors="replace")

        resource_name, resource_format = extract_resource_identity(raw)
        file_uuid, record_id = extract_download_action(raw)
        semantics = semantic_states(raw, year, quarter)
        semantic_match = all(semantics.values())
        if semantic_match:
            semantic_match_count += 1
            semantic_state = "semantic_family_match"
        else:
            semantic_state = "held_semantic_evidence_incomplete"

        # The first inventory parser counted shared UI image assets under /storage/
        # as transport locators. Correct that representation without fetching the
        # underlying resource or inspecting values. The only qualified transport
        # evidence at this stage is the source-native disclaimer action identity.
        corrected = dict(row)
        corrected.update({
            "resource_name": resource_name,
            "resource_format": resource_format,
            "resource_transport_locator_count": "0",
            "resource_transport_locators": "",
            "promotion_state": "metadata_qualified_resource_transport_pending",
            "resource_download_action_file_uuid": file_uuid,
            "resource_download_action_record_id": record_id,
            "resource_download_action_count": "1",
            "resource_transport_endpoint_resolved": "false",
            "semantic_family_state": semantic_state,
        })
        corrected_rows.append(corrected)
        download_action_pairs.add((file_uuid, record_id))

        audit_rows.append({
            "year": year,
            "quarter": quarter,
            "quarter_number": int(row["quarter_number"]),
            "dataset_identifier": row["dataset_identifier"],
            **{key: str(value).lower() for key, value in semantics.items()},
            "semantic_family_state": semantic_state,
            "target_investment_values_inspected": "false",
            "annual_sum_authorized": "false",
        })

    corrected_rows.sort(key=lambda r: (int(r["year"]), int(r["quarter_number"])))
    audit_rows.sort(key=lambda r: (int(r["year"]), int(r["quarter_number"])))
    write_csv(INVENTORY, new_fields, corrected_rows)
    audit_fields = [
        "year", "quarter", "quarter_number", "dataset_identifier",
        "description_period_match", "lkpm_source_identity_match", "period_field_semantics_match",
        "rupiah_increment_semantics_match", "usd_increment_semantics_match",
        "update_frequency_quarterly_match", "collection_frequency_quarterly_match",
        "semantic_family_state", "target_investment_values_inspected", "annual_sum_authorized",
    ]
    write_csv(SEMANTIC_AUDIT, audit_fields, audit_rows)

    manifest.update({
        "schema": "ranah-observatory/milestone27-bkpm-resource-inventory/v2",
        "stage": "stage0_inventory_and_semantic_continuity_qualified_transport_pending",
        "inventory_parser_transport_false_positive_corrected": True,
        "false_positive_locator_class": "shared_storage_image_assets",
        "direct_resource_transport_period_count": 0,
        "direct_resource_url_count": 0,
        "resource_download_action_period_count": 64,
        "resource_download_action_unique_pair_count": len(download_action_pairs),
        "resource_transport_endpoint_resolved_period_count": 0,
        "declared_expected_schema_complete_period_count": 64,
        "semantic_contract": {"path": rel(SEMANTIC_CONTRACT), "sha256": sha256_path(SEMANTIC_CONTRACT)},
        "semantic_family_match_period_count": semantic_match_count,
        "semantic_family_hold_period_count": 64 - semantic_match_count,
        "semantic_audit": {"path": rel(SEMANTIC_AUDIT), "sha256": sha256_path(SEMANTIC_AUDIT)},
        "quarter_specific_period_semantics_supported_by_page_text": semantic_match_count == 64,
        "incremental_reported_realization_semantics_supported_by_page_text": semantic_match_count == 64,
        "quarterly_flow_interpretation_authorized": False,
        "cross_quarter_additivity_authorized": False,
        "annual_sum_authorized": False,
        "resource_transport_endpoint_qualified": False,
        "resource_header_retrieval_authorized": False,
        "resource_file_download_performed": False,
        "target_investment_values_inspected": False,
        "investment_value_aggregation_performed": False,
        "statistical_model_fit": False,
        "causal_claim_created": False,
        "monetary_wasted_potential_estimated": False,
        "stage0_complete": False,
    })
    manifest["outputs"] = {
        "inventory": rel(INVENTORY),
        "inventory_sha256": sha256_path(INVENTORY),
        "semantic_audit": rel(SEMANTIC_AUDIT),
        "semantic_audit_sha256": sha256_path(SEMANTIC_AUDIT),
    }
    write_json(MANIFEST, manifest)

    print(json.dumps({
        "period_count": 64,
        "semantic_family_match_period_count": semantic_match_count,
        "resource_download_action_period_count": 64,
        "direct_resource_url_count": 0,
        "transport_endpoint_qualified": False,
        "target_investment_values_inspected": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError, AuditError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
