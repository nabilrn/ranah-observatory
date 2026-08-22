#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "data/manifests/milestone27_public_data_head_probe_contract.json"
BINDING = ROOT / "data/manifests/milestone27_bkpm_preview_parameter_binding.json"
OUT = ROOT / "data/manifests/milestone27_bkpm_public_data_head_probe.json"
USER_AGENT = "ranah-observatory/1.0 (+https://github.com/nabilrn/ranah-observatory)"


class HeadProbeError(RuntimeError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        return None


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_contract() -> dict[str, Any]:
    c = load_json(CONTRACT)
    if c.get("schema") != "ranah-observatory/milestone27-public-data-head-probe-contract/v1":
        raise HeadProbeError("unexpected HEAD contract schema")
    if c.get("contract_locked_before_live_route_request") is not True:
        raise HeadProbeError("HEAD contract not locked")
    if c.get("request_method") != "HEAD" or c.get("head_request_authorized") is not True:
        raise HeadProbeError("HEAD request not authorized")
    if c.get("request_parameter_submission_authorized") is not True:
        raise HeadProbeError("parameter submission not authorized")
    if c.get("follow_redirects") is not False:
        raise HeadProbeError("redirect following must be disabled")
    for key in (
        "response_body_read_authorized",
        "response_body_persistence_authorized",
        "get_request_authorized",
        "post_request_authorized",
        "datatable_pagination_parameters_authorized",
        "preview_table_schema_inspection_authorized",
        "table_column_name_extraction_authorized",
        "table_header_extraction_authorized",
        "table_body_extraction_authorized",
        "table_cell_text_extraction_authorized",
        "target_investment_values_inspection_authorized",
        "period_column_inspection_authorized",
        "csv_schema_inspection_authorized",
        "zip_resource_request_authorized",
        "interactive_disclaimer_form_submission_authorized",
        "synthetic_personal_information_submission_authorized",
        "source_selection_uses_transport_result",
        "quarterly_flow_interpretation_authorized",
        "cross_quarter_additivity_authorized",
        "annual_sum_authorized",
        "geography_mapping_authorized",
        "numeric_aggregation_authorized",
        "statistical_model_fit_authorized",
        "causal_claim_authorized",
        "monetary_wasted_potential_estimate_authorized",
    ):
        if c.get(key) is not False:
            raise HeadProbeError(f"forbidden authorization enabled: {key}")
    return c


def head(url: str) -> dict[str, Any]:
    opener = urllib.request.build_opener(NoRedirect())
    request = urllib.request.Request(
        url,
        method="HEAD",
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json,text/plain,*/*",
        },
    )
    try:
        response = opener.open(request, timeout=40)
        status = int(response.status)
        headers = response.headers
        final_url = response.geturl()
        response.close()
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        headers = exc.headers
        final_url = url
        exc.close()
    except urllib.error.URLError as exc:
        raise HeadProbeError(f"HEAD transport error for {url}: {exc}") from exc

    return {
        "status": status,
        "final_url": final_url,
        "content_type": headers.get("Content-Type", ""),
        "content_length": headers.get("Content-Length", ""),
        "location": headers.get("Location", ""),
        "cache_control": headers.get("Cache-Control", ""),
        "response_body_read": False,
        "response_body_persisted": False,
    }


def main() -> int:
    contract = load_contract()
    binding = load_json(BINDING)
    if binding.get("schema") != "ranah-observatory/milestone27-bkpm-preview-parameter-binding/v1":
        raise HeadProbeError("unexpected binding manifest schema")
    if binding.get("binding_qualified") is not True:
        raise HeadProbeError("preview parameter binding is not qualified")
    if binding.get("client_side_data_endpoint_requested") is not False:
        raise HeadProbeError("binding stage already requested client data endpoint")

    by_period = {(int(r["year"]), str(r["quarter"])): r for r in binding["pilot_results"]}
    results: list[dict[str, Any]] = []

    for pilot in contract["pilot_periods"]:
        key = (int(pilot["year"]), str(pilot["quarter"]))
        row = by_period.get(key)
        if row is None:
            raise HeadProbeError(f"pilot missing from qualified binding: {key}")
        parameter_value = row["preview_parameter_value"]
        query = urllib.parse.urlencode({contract["parameter_name"]: parameter_value})
        request_url = contract["target_route"] + "?" + query
        parsed = urllib.parse.urlparse(request_url)
        if parsed.scheme != "https" or parsed.hostname != contract["official_domain"] or parsed.path != "/data":
            raise HeadProbeError(f"request escaped locked route: {request_url}")

        metadata = head(request_url)
        results.append({
            "year": key[0],
            "quarter": key[1],
            "dataset_identifier": row["dataset_identifier"],
            "request_method": "HEAD",
            "request_url": request_url,
            "parameter_name": contract["parameter_name"],
            "parameter_value": parameter_value,
            **metadata,
            "request_parameter_submitted": True,
            "get_request_performed": False,
            "post_request_performed": False,
            "datatable_pagination_parameters_submitted": False,
            "target_investment_values_inspected": False,
            "table_schema_inspected": False,
        })

    statuses = [r["status"] for r in results]
    head_supported_all = all(200 <= status < 400 for status in statuses)
    payload = {
        "schema": "ranah-observatory/milestone27-bkpm-public-data-head-probe/v1",
        "milestone": 27,
        "stage": "stage0g_public_data_route_head_probe",
        "pilot_count": len(results),
        "pilot_results": results,
        "status_codes": statuses,
        "head_supported_all_pilots": head_supported_all,
        "transport_classification": "head_supported_all_pilots" if head_supported_all else "head_not_supported_or_transport_error_on_one_or_more_pilots",
        "request_parameter_submitted": True,
        "response_body_read": False,
        "response_body_persisted": False,
        "get_request_performed": False,
        "post_request_performed": False,
        "datatable_pagination_parameters_submitted": False,
        "preview_table_schema_inspected": False,
        "table_column_names_extracted": False,
        "table_header_extracted": False,
        "table_body_extracted": False,
        "table_cell_text_extracted": False,
        "target_investment_values_inspected": False,
        "period_column_inspected": False,
        "csv_schema_inspected": False,
        "zip_resource_requested": False,
        "interactive_disclaimer_form_submitted": False,
        "synthetic_personal_information_submitted": False,
        "source_selection_uses_transport_result": False,
        "investment_value_aggregation_performed": False,
        "quarterly_flow_interpretation_authorized": False,
        "cross_quarter_additivity_authorized": False,
        "annual_sum_authorized": False,
        "geography_mapping_authorized": False,
        "statistical_model_fit": False,
        "causal_claim_created": False,
        "monetary_wasted_potential_estimated": False,
        "contract": {"path": rel(CONTRACT), "sha256": sha256_path(CONTRACT)},
        "binding": {"path": rel(BINDING), "sha256": sha256_path(BINDING)},
    }
    write_json(OUT, payload)
    print(json.dumps({
        "pilot_count": len(results),
        "status_codes": statuses,
        "head_supported_all_pilots": head_supported_all,
        "response_body_read": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError, HeadProbeError) as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
