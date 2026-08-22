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
CONTRACT = ROOT / "data/manifests/milestone27_sumbar_global_search_contract.json"
BASELINE = ROOT / "data/manifests/milestone27_bkpm_public_data_zero_row_probe.json"
BINDING = ROOT / "data/manifests/milestone27_bkpm_preview_parameter_binding.json"
GEOGRAPHIES = ROOT / "data/registries/geographies.csv"
OUT = ROOT / "data/manifests/milestone27_bkpm_sumbar_global_search_probe.json"
USER_AGENT = "ranah-observatory/1.0 (+https://github.com/nabilrn/ranah-observatory)"


class SearchProbeError(RuntimeError):
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
    if c.get("schema") != "ranah-observatory/milestone27-sumbar-global-search-contract/v1":
        raise SearchProbeError("unexpected global-search contract schema")
    if c.get("contract_locked_before_live_search_requests") is not True:
        raise SearchProbeError("global-search contract not locked")
    if c.get("request_method") != "GET" or c.get("get_request_authorized") is not True:
        raise SearchProbeError("GET not authorized")
    if c.get("global_search_submission_authorized") is not True or c.get("negative_control_submission_authorized") is not True:
        raise SearchProbeError("search submissions not authorized")
    if c.get("follow_redirects") is not False:
        raise SearchProbeError("redirect following must be disabled")
    if c.get("response_body_read_authorized") is not True:
        raise SearchProbeError("bounded response read not authorized")
    for key in (
        "response_body_persistence_authorized",
        "raw_json_persistence_authorized",
        "data_array_element_inspection_authorized",
        "target_investment_values_inspection_authorized",
        "non_geography_observation_values_inspection_authorized",
        "source_selection_uses_search_result",
        "quarterly_flow_interpretation_authorized",
        "cross_quarter_additivity_authorized",
        "annual_sum_authorized",
        "pma_pmdn_combination_authorized",
        "external_fx_conversion_authorized",
        "numeric_materialization_authorized",
        "statistical_model_fit_authorized",
        "causal_claim_authorized",
        "monetary_wasted_potential_estimate_authorized",
    ):
        if c.get(key) is not False:
            raise SearchProbeError(f"forbidden authorization enabled: {key}")
    return c


def data_array_empty(body: bytes) -> bool | None:
    text = body.decode("utf-8", errors="strict")
    match = re.search(r'"data"\s*:\s*\[', text)
    if not match:
        return None
    pos = match.end()
    while pos < len(text) and text[pos].isspace():
        pos += 1
    if pos >= len(text):
        return None
    return text[pos] == "]"


def request_zero_row(url: str, max_bytes: int) -> dict[str, Any]:
    opener = urllib.request.build_opener(NoRedirect())
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        response = opener.open(req, timeout=40)
        status = int(response.status)
        content_type = response.headers.get("Content-Type", "")
        body = response.read(max_bytes + 1)
        response.close()
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        content_type = exc.headers.get("Content-Type", "")
        body = b""
        exc.close()
    except urllib.error.URLError as exc:
        raise SearchProbeError(f"transport error: {exc}") from exc
    if len(body) > max_bytes:
        raise SearchProbeError("response exceeded preregistered byte limit")

    empty = None
    records_total = None
    records_filtered = None
    parsed = False
    if status == 200 and content_type.lower().startswith("application/json"):
        empty = data_array_empty(body)
        if empty is True:
            payload = json.loads(body.decode("utf-8"))
            parsed = True
            if not isinstance(payload, dict):
                raise SearchProbeError("zero-row response is not a JSON object")
            rt = payload.get("recordsTotal")
            rf = payload.get("recordsFiltered")
            records_total = rt if isinstance(rt, int) else None
            records_filtered = rf if isinstance(rf, int) else None
    return {
        "status": status,
        "content_type": content_type,
        "response_body_bytes_received": len(body),
        "data_array_empty": empty,
        "json_parsed": parsed,
        "records_total": records_total,
        "records_filtered": records_filtered,
        "response_body_persisted": False,
        "raw_json_persisted": False,
        "data_array_elements_inspected": False,
        "target_investment_values_inspected": False,
        "non_geography_observation_values_inspected": False,
    }


def build_url(contract: dict[str, Any], resource_uuid: str, search_value: str) -> str:
    params = {
        "dataset_detail_parent_id": resource_uuid,
        **{str(k): str(v) for k, v in contract["query_parameters"].items()},
        "search[value]": search_value,
    }
    url = contract["target_route"] + "?" + urllib.parse.urlencode(params)
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != contract["official_domain"] or parsed.path != "/data":
        raise SearchProbeError("request escaped locked route")
    return url


def main() -> int:
    contract = load_contract()
    baseline = load_json(BASELINE)
    binding = load_json(BINDING)
    if baseline.get("schema_qualified") is not True:
        raise SearchProbeError("zero-row baseline prerequisite not qualified")
    if binding.get("binding_qualified") is not True:
        raise SearchProbeError("binding prerequisite not qualified")
    if not GEOGRAPHIES.is_file() or "idn.13,province,Sumatera Barat,13," not in GEOGRAPHIES.read_text(encoding="utf-8"):
        raise SearchProbeError("canonical Sumatera Barat geography registry row not found")

    baseline_by_key = {(int(r["year"]), str(r["quarter"])): r for r in baseline["pilot_results"]}
    binding_by_key = {(int(r["year"]), str(r["quarter"])): r for r in binding["pilot_results"]}
    max_bytes = int(contract["max_response_body_bytes"])
    positive_value = str(contract["positive_search_value"])
    negative_value = str(contract["negative_control_value"])
    results: list[dict[str, Any]] = []

    for pilot in contract["pilot_periods"]:
        key = (int(pilot["year"]), str(pilot["quarter"]))
        b = baseline_by_key.get(key)
        bind = binding_by_key.get(key)
        if b is None or bind is None:
            raise SearchProbeError(f"pilot prerequisite missing: {key}")
        baseline_total = b.get("records_total")
        if not isinstance(baseline_total, int) or baseline_total <= 0:
            raise SearchProbeError(f"invalid baseline total: {key}")
        uuid = str(bind["preview_parameter_value"])
        positive_url = build_url(contract, uuid, positive_value)
        negative_url = build_url(contract, uuid, negative_value)
        positive = request_zero_row(positive_url, max_bytes)
        negative = request_zero_row(negative_url, max_bytes)

        positive_ok = (
            positive["status"] == 200
            and positive["data_array_empty"] is True
            and positive["records_total"] == baseline_total
            and isinstance(positive["records_filtered"], int)
            and 0 < positive["records_filtered"] < baseline_total
        )
        negative_ok = (
            negative["status"] == 200
            and negative["data_array_empty"] is True
            and negative["records_total"] == baseline_total
            and negative["records_filtered"] == 0
        )
        results.append({
            "year": key[0],
            "quarter": key[1],
            "dataset_identifier": bind["dataset_identifier"],
            "baseline_records_total": baseline_total,
            "positive_search": {"submitted_value": positive_value, "request_url": positive_url, **positive, "qualified": positive_ok},
            "negative_control_search": {"submitted_value": negative_value, "request_url": negative_url, **negative, "qualified": negative_ok},
            "global_search_transport_qualified": positive_ok and negative_ok,
            "response_body_persisted": False,
            "raw_json_persisted": False,
            "data_array_elements_inspected": False,
            "target_investment_values_inspected": False,
            "non_geography_observation_values_inspected": False,
        })

    all_qualified = all(r["global_search_transport_qualified"] for r in results)
    payload = {
        "schema": "ranah-observatory/milestone27-bkpm-sumbar-global-search-probe/v1",
        "milestone": 27,
        "stage": "stage0k_sumbar_global_search_transport_probe",
        "pilot_count": len(results),
        "pilot_results": results,
        "global_search_transport_qualified_all_pilots": all_qualified,
        "positive_search_value": positive_value,
        "canonical_province_geography_id": contract["canonical_province_geography_id"],
        "response_body_persisted": False,
        "raw_json_persisted": False,
        "data_array_elements_inspected": False,
        "target_investment_values_inspected": False,
        "non_geography_observation_values_inspected": False,
        "source_selection_uses_search_result": False,
        "quarterly_flow_interpretation_authorized": False,
        "cross_quarter_additivity_authorized": False,
        "annual_sum_authorized": False,
        "pma_pmdn_combination_authorized": False,
        "external_fx_conversion_authorized": False,
        "numeric_materialization_authorized": False,
        "statistical_model_fit": False,
        "causal_claim_created": False,
        "monetary_wasted_potential_estimated": False,
        "contract": {"path": rel(CONTRACT), "sha256": sha256_path(CONTRACT)},
        "baseline": {"path": rel(BASELINE), "sha256": sha256_path(BASELINE)},
        "binding": {"path": rel(BINDING), "sha256": sha256_path(BINDING)},
        "geography_registry": {"path": rel(GEOGRAPHIES), "sha256": sha256_path(GEOGRAPHIES)},
    }
    write_json(OUT, payload)
    print(json.dumps({
        "all_qualified": all_qualified,
        "filtered_counts": {f"{r['year']}-{r['quarter']}": [r['positive_search']['records_filtered'], r['negative_control_search']['records_filtered']] for r in results},
        "target_investment_values_inspected": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError, SearchProbeError) as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
