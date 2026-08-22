#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "data/manifests/milestone27_public_data_zero_row_contract.json"
REQUEST_METADATA = ROOT / "data/manifests/milestone27_bkpm_preview_request_metadata.json"
BINDING = ROOT / "data/manifests/milestone27_bkpm_preview_parameter_binding.json"
HEAD = ROOT / "data/manifests/milestone27_bkpm_public_data_head_probe.json"
OUT = ROOT / "data/manifests/milestone27_bkpm_public_data_zero_row_probe.json"
USER_AGENT = "ranah-observatory/1.0 (+https://github.com/nabilrn/ranah-observatory)"


class ZeroRowError(RuntimeError):
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
    if c.get("schema") != "ranah-observatory/milestone27-public-data-zero-row-contract/v1":
        raise ZeroRowError("unexpected zero-row contract schema")
    if c.get("contract_locked_before_live_get_request") is not True:
        raise ZeroRowError("zero-row contract not locked")
    if c.get("request_method") != "GET" or c.get("get_request_authorized") is not True:
        raise ZeroRowError("GET not authorized")
    if c.get("follow_redirects") is not False:
        raise ZeroRowError("redirect following must be disabled")
    if c.get("response_body_read_authorized") is not True:
        raise ZeroRowError("bounded structural response-body read not authorized")
    if c.get("response_body_persistence_authorized") is not False:
        raise ZeroRowError("response body persistence must remain disabled")
    if c.get("data_array_emptiness_check_authorized") is not True:
        raise ZeroRowError("data-array emptiness check not authorized")
    if c.get("data_array_element_inspection_authorized") is not False:
        raise ZeroRowError("data-array element inspection must remain disabled")
    for key in (
        "target_investment_values_inspection_authorized",
        "period_value_inspection_authorized",
        "table_body_persistence_authorized",
        "raw_json_persistence_authorized",
        "zip_resource_request_authorized",
        "interactive_disclaimer_form_submission_authorized",
        "synthetic_personal_information_submission_authorized",
        "source_selection_uses_response_values",
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
            raise ZeroRowError(f"forbidden authorization enabled: {key}")
    return c


def request_bytes(url: str, limit: int) -> tuple[int, str, bytes, dict[str, str]]:
    opener = urllib.request.build_opener(NoRedirect())
    req = urllib.request.Request(
        url,
        method="GET",
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    try:
        response = opener.open(req, timeout=40)
        status = int(response.status)
        final_url = response.geturl()
        headers = response.headers
        body = response.read(limit + 1)
        response.close()
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        final_url = url
        headers = exc.headers
        body = b""
        exc.close()
    except urllib.error.URLError as exc:
        raise ZeroRowError(f"GET transport error for {url}: {exc}") from exc

    if len(body) > limit:
        raise ZeroRowError(f"response exceeded preregistered byte limit for {url}")
    return status, final_url, body, {
        "content_type": headers.get("Content-Type", ""),
        "content_length": headers.get("Content-Length", ""),
        "location": headers.get("Location", ""),
    }


def data_array_is_empty_without_element_inspection(body: bytes) -> tuple[bool | None, bool]:
    text = body.decode("utf-8", errors="strict")
    match = re.search(r'"data"\s*:\s*\[', text)
    if not match:
        return None, False
    pos = match.end()
    while pos < len(text) and text[pos].isspace():
        pos += 1
    if pos >= len(text):
        return None, True
    return text[pos] == "]", True


def main() -> int:
    contract = load_contract()
    request_metadata = load_json(REQUEST_METADATA)
    binding = load_json(BINDING)
    head_manifest = load_json(HEAD)

    if request_metadata.get("request_metadata_resolved") is not True:
        raise ZeroRowError("request metadata prerequisite not resolved")
    if binding.get("binding_qualified") is not True:
        raise ZeroRowError("binding prerequisite not qualified")
    if head_manifest.get("head_supported_all_pilots") is not True:
        raise ZeroRowError("HEAD prerequisite not qualified")

    binding_by_period = {(int(r["year"]), str(r["quarter"])): r for r in binding["pilot_results"]}
    max_bytes = int(contract["max_response_body_bytes"])
    results: list[dict[str, Any]] = []

    for pilot in contract["pilot_periods"]:
        key = (int(pilot["year"]), str(pilot["quarter"]))
        binding_row = binding_by_period.get(key)
        if binding_row is None:
            raise ZeroRowError(f"pilot missing from binding: {key}")

        params = {
            "dataset_detail_parent_id": binding_row["preview_parameter_value"],
            "draw": "1",
            "start": "0",
            "length": "0",
        }
        request_url = contract["target_route"] + "?" + urllib.parse.urlencode(params)
        parsed = urllib.parse.urlparse(request_url)
        if parsed.scheme != "https" or parsed.hostname != contract["official_domain"] or parsed.path != "/data":
            raise ZeroRowError(f"request escaped locked route: {request_url}")

        status, final_url, body, headers = request_bytes(request_url, max_bytes)
        content_type_json = headers["content_type"].lower().startswith("application/json")
        data_empty: bool | None = None
        data_key_found = False
        json_parsed = False
        top_level_keys: list[str] = []
        columns: list[str] = []
        records_total: int | None = None
        records_filtered: int | None = None
        classification = "http_or_content_type_not_qualified"

        if status == 200 and content_type_json:
            data_empty, data_key_found = data_array_is_empty_without_element_inspection(body)
            if data_empty is True:
                payload = json.loads(body.decode("utf-8"))
                json_parsed = True
                if not isinstance(payload, dict):
                    raise ZeroRowError(f"zero-row JSON is not an object for {key}")
                top_level_keys = sorted(str(k) for k in payload.keys())
                raw_columns = payload.get("columns")
                if isinstance(raw_columns, list) and all(isinstance(v, str) for v in raw_columns):
                    columns = list(raw_columns)
                raw_total = payload.get("recordsTotal")
                raw_filtered = payload.get("recordsFiltered")
                records_total = raw_total if isinstance(raw_total, int) else None
                records_filtered = raw_filtered if isinstance(raw_filtered, int) else None
                classification = "zero_row_honored_schema_available" if columns else "zero_row_honored_schema_missing"
            elif data_empty is False:
                classification = "zero_row_not_honored_nonempty_data_detected_without_element_inspection"
            else:
                classification = "data_array_structure_unresolved"

        results.append({
            "year": key[0],
            "quarter": key[1],
            "dataset_identifier": binding_row["dataset_identifier"],
            "request_url": request_url,
            "request_method": "GET",
            "status": status,
            "final_url": final_url,
            **headers,
            "response_body_bytes_received": len(body),
            "response_body_persisted": False,
            "data_key_found": data_key_found,
            "data_array_empty": data_empty,
            "data_array_elements_inspected": False,
            "json_parsed": json_parsed,
            "top_level_json_keys": top_level_keys,
            "declared_columns": columns,
            "declared_column_count": len(columns),
            "records_total": records_total,
            "records_filtered": records_filtered,
            "classification": classification,
            "raw_json_persisted": False,
            "target_investment_values_inspected": False,
            "period_values_inspected": False,
        })

    schema_candidates = [tuple(r["declared_columns"]) for r in results if r["classification"] == "zero_row_honored_schema_available"]
    all_zero_row = len(schema_candidates) == len(results)
    identical_schema = all_zero_row and len(set(schema_candidates)) == 1
    schema_qualified = all_zero_row and identical_schema

    payload = {
        "schema": "ranah-observatory/milestone27-bkpm-public-data-zero-row-probe/v1",
        "milestone": 27,
        "stage": "stage0h_public_data_zero_row_schema_probe",
        "pilot_count": len(results),
        "pilot_results": results,
        "all_pilots_zero_row_honored": all_zero_row,
        "identical_declared_schema_across_pilots": identical_schema,
        "schema_qualified": schema_qualified,
        "qualified_declared_columns": list(schema_candidates[0]) if schema_qualified else [],
        "qualified_declared_column_count": len(schema_candidates[0]) if schema_qualified else 0,
        "response_body_persisted": False,
        "raw_json_persisted": False,
        "data_array_elements_inspected": False,
        "target_investment_values_inspected": False,
        "period_values_inspected": False,
        "source_selection_uses_response_values": False,
        "zip_resource_requested": False,
        "interactive_disclaimer_form_submitted": False,
        "synthetic_personal_information_submitted": False,
        "investment_value_aggregation_performed": False,
        "quarterly_flow_interpretation_authorized": False,
        "cross_quarter_additivity_authorized": False,
        "annual_sum_authorized": False,
        "geography_mapping_authorized": False,
        "statistical_model_fit": False,
        "causal_claim_created": False,
        "monetary_wasted_potential_estimated": False,
        "contract": {"path": rel(CONTRACT), "sha256": sha256_path(CONTRACT)},
        "request_metadata": {"path": rel(REQUEST_METADATA), "sha256": sha256_path(REQUEST_METADATA)},
        "binding": {"path": rel(BINDING), "sha256": sha256_path(BINDING)},
        "head_probe": {"path": rel(HEAD), "sha256": sha256_path(HEAD)},
    }
    write_json(OUT, payload)
    print(json.dumps({
        "pilot_count": len(results),
        "classifications": [r["classification"] for r in results],
        "schema_qualified": schema_qualified,
        "qualified_declared_column_count": payload["qualified_declared_column_count"],
        "target_investment_values_inspected": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError, ZeroRowError) as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
