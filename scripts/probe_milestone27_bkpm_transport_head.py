#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import http.client
import json
import ssl
import sys
import urllib.parse
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "data/manifests/milestone27_transport_probe_contract.json"
INVENTORY = ROOT / "data/analysis/engine/investment_realization_v1/m27-bkpm-resource-inventory.csv"
SEMANTIC_AUDIT = ROOT / "data/analysis/engine/investment_realization_v1/m27-bkpm-semantic-audit.csv"
OUT = ROOT / "data/manifests/milestone27_bkpm_transport_probe.json"
RAW_ROOT = ROOT / "data/processed/bkpm/m27_transport_probe"
USER_AGENT = "ranah-observatory/1.0 (+https://github.com/nabilrn/ranah-observatory)"


class TransportProbeError(RuntimeError):
    pass


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [{k: (v or "") for k, v in row.items()} for row in csv.DictReader(handle)]


def load_contract() -> dict[str, Any]:
    c = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if c.get("schema") != "ranah-observatory/milestone27-transport-probe-contract/v1":
        raise TransportProbeError("unexpected transport probe contract schema")
    if c.get("contract_locked_before_live_transport_probe") is not True:
        raise TransportProbeError("transport contract not locked before live probe")
    false_keys = (
        "interactive_disclaimer_form_submission_authorized",
        "synthetic_personal_information_submission_authorized",
        "disclaimer_bypass_authorized",
        "redirect_following_authorized",
        "response_body_read_authorized",
        "resource_file_download_authorized",
        "resource_header_content_inspection_authorized",
        "pilot_selection_uses_target_investment_values",
        "target_investment_values_inspection_authorized",
        "period_column_inspection_authorized",
        "csv_schema_inspection_authorized",
        "quarterly_flow_interpretation_authorized",
        "cross_quarter_additivity_authorized",
        "annual_sum_authorized",
        "pma_pmdn_combination_authorized",
        "external_currency_conversion_authorized",
        "geography_mapping_authorized",
        "numeric_aggregation_authorized",
        "statistical_model_fit_authorized",
        "causal_claim_authorized",
        "monetary_wasted_potential_estimate_authorized",
    )
    for key in false_keys:
        if c.get(key) is not False:
            raise TransportProbeError(f"forbidden transport authorization enabled: {key}")
    if c.get("probe_method") != "HEAD":
        raise TransportProbeError("only HEAD transport probe is authorized")
    if len(c.get("pilot_periods_locked_before_probe", [])) != 3:
        raise TransportProbeError("expected exactly three preregistered transport pilots")
    return c


def classify(statuses: list[int], contract: dict[str, Any]) -> str:
    rules = contract["qualification_rule"]
    if all(200 <= status < 300 for status in statuses):
        return rules["all_pilots_status_2xx"]
    if any(status in {401, 403} for status in statuses):
        return rules["any_pilot_status_401_or_403"]
    if any(300 <= status < 400 for status in statuses):
        return rules["any_pilot_status_3xx"]
    if any(status == 405 for status in statuses):
        return rules["any_pilot_status_405"]
    return rules["otherwise"]


def head_once(url: str, allowed_headers: set[str]) -> dict[str, Any]:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "data.bkpm.go.id":
        raise TransportProbeError(f"unexpected transport target: {url}")
    path = parsed.path
    if parsed.query:
        path += "?" + parsed.query

    conn = http.client.HTTPSConnection(
        parsed.hostname,
        parsed.port or 443,
        timeout=30,
        context=ssl.create_default_context(),
    )
    try:
        conn.request("HEAD", path, body=None, headers={
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
            "Connection": "close",
        })
        response = conn.getresponse()
        headers = {
            key.lower(): value
            for key, value in response.getheaders()
            if key.lower() in allowed_headers
        }
        # HEAD explicitly forbids response-body inspection in this contract.
        return {
            "requested_url": url,
            "method": "HEAD",
            "status": int(response.status),
            "reason": str(response.reason or ""),
            "headers": headers,
            "redirect_followed": False,
            "response_body_read": False,
            "response_body_bytes_read": 0,
        }
    finally:
        conn.close()


def main() -> int:
    contract = load_contract()
    inventory = read_csv(INVENTORY)
    semantic_rows = read_csv(SEMANTIC_AUDIT)
    by_period = {(int(r["year"]), r["quarter"]): r for r in inventory}
    semantics = {(int(r["year"]), r["quarter"]): r for r in semantic_rows}
    if len(by_period) != 64 or len(semantics) != 64:
        raise TransportProbeError("frozen inventory/semantic audit does not contain 64 unique periods")

    allowed_headers = {str(x).lower() for x in contract["response_headers_authorized"]}
    forbidden_headers = {str(x).lower() for x in contract["response_headers_forbidden_to_persist"]}
    if allowed_headers & forbidden_headers:
        raise TransportProbeError("allowed and forbidden persisted header sets overlap")

    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    route_template = contract["route_template_from_frozen_official_frontend"]

    for pilot in contract["pilot_periods_locked_before_probe"]:
        year = int(pilot["year"])
        quarter = str(pilot["quarter"])
        row = by_period.get((year, quarter))
        sem = semantics.get((year, quarter))
        if row is None or sem is None:
            raise TransportProbeError(f"pilot period missing from frozen inventory: {year}-{quarter}")
        if row.get("resource_download_action_count") != "1":
            raise TransportProbeError(f"pilot does not have one frozen download action: {year}-{quarter}")
        file_uuid = row.get("resource_download_action_file_uuid", "")
        record_id = row.get("resource_download_action_record_id", "")
        if not file_uuid or not record_id.isdigit():
            raise TransportProbeError(f"pilot action identity malformed: {year}-{quarter}")
        url = route_template.format(file_uuid=file_uuid, record_id=record_id)
        probe = head_once(url, allowed_headers)
        probe.update({
            "year": year,
            "quarter": quarter,
            "quarter_number": int(row["quarter_number"]),
            "pilot_role": pilot["role"],
            "dataset_identifier": row["dataset_identifier"],
            "semantic_family_state": sem["semantic_family_state"],
            "resource_download_action_file_uuid": file_uuid,
            "resource_download_action_record_id": record_id,
            "target_investment_values_inspected": False,
            "csv_schema_inspected": False,
            "period_column_inspected": False,
            "disclaimer_form_submitted": False,
            "synthetic_personal_information_submitted": False,
        })
        sidecar = RAW_ROOT / f"{year}-q{row['quarter_number']}-head.json"
        write_json(sidecar, probe)
        probe["sidecar_path"] = rel(sidecar)
        probe["sidecar_sha256"] = sha256_path(sidecar)
        results.append(probe)

    statuses = [int(item["status"]) for item in results]
    classification = classify(statuses, contract)
    payload = {
        "schema": "ranah-observatory/milestone27-bkpm-transport-probe/v1",
        "milestone": 27,
        "stage": "stage0c_head_only_transport_route_qualification",
        "probe_method": "HEAD",
        "pilot_count": len(results),
        "pilot_results": results,
        "status_codes": statuses,
        "classification": classification,
        "all_pilots_2xx": all(200 <= status < 300 for status in statuses),
        "transport_route_reachable_without_response_body": classification == "head_route_reachable_without_response_body",
        "transport_endpoint_qualified_for_file_retrieval": False,
        "interactive_disclaimer_form_submitted": False,
        "synthetic_personal_information_submitted": False,
        "disclaimer_bypass_performed": False,
        "redirect_following_performed": False,
        "response_body_read": False,
        "response_body_bytes_read": 0,
        "resource_file_downloaded": False,
        "resource_header_content_inspected": False,
        "csv_schema_inspected": False,
        "period_column_inspected": False,
        "target_investment_values_inspected": False,
        "investment_value_aggregation_performed": False,
        "quarterly_flow_interpretation_authorized": False,
        "cross_quarter_additivity_authorized": False,
        "annual_sum_authorized": False,
        "geography_mapping_authorized": False,
        "statistical_model_fit": False,
        "causal_claim_created": False,
        "monetary_wasted_potential_estimated": False,
        "contract": {"path": rel(CONTRACT), "sha256": sha256_path(CONTRACT)},
        "inventory": {"path": rel(INVENTORY), "sha256": sha256_path(INVENTORY)},
        "semantic_audit": {"path": rel(SEMANTIC_AUDIT), "sha256": sha256_path(SEMANTIC_AUDIT)},
        "route_discovery_evidence": {
            "path": contract["route_discovery_evidence"],
            "sha256": sha256_path(ROOT / contract["route_discovery_evidence"]),
        },
    }
    write_json(OUT, payload)
    print(json.dumps({
        "classification": classification,
        "pilot_count": len(results),
        "status_codes": statuses,
        "response_body_bytes_read": 0,
        "target_investment_values_inspected": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError, TransportProbeError, ssl.SSLError) as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
