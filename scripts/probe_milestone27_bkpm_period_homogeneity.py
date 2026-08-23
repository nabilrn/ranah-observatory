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
CONTRACT = ROOT / "data/manifests/milestone27_period_homogeneity_contract.json"
PERIOD = ROOT / "data/manifests/milestone27_bkpm_period_identity_prefix_probe.json"
BASELINE = ROOT / "data/manifests/milestone27_bkpm_public_data_zero_row_probe.json"
BINDING = ROOT / "data/manifests/milestone27_bkpm_preview_parameter_binding.json"
OUT = ROOT / "data/manifests/milestone27_bkpm_period_homogeneity_probe.json"
USER_AGENT = "ranah-observatory/1.0 (+https://github.com/nabilrn/ranah-observatory)"


class HomogeneityError(RuntimeError):
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
    if c.get("schema") != "ranah-observatory/milestone27-period-homogeneity-contract/v1":
        raise HomogeneityError("unexpected homogeneity contract schema")
    if c.get("contract_locked_before_live_filter_requests") is not True:
        raise HomogeneityError("homogeneity contract not locked")
    if c.get("request_method") != "GET" or c.get("get_request_authorized") is not True:
        raise HomogeneityError("GET not authorized")
    if c.get("follow_redirects") is not False:
        raise HomogeneityError("redirect following must be disabled")
    if c.get("response_body_read_authorized") is not True:
        raise HomogeneityError("bounded structural response read not authorized")
    if c.get("period_filter_value_submission_authorized") is not True or c.get("negative_control_submission_authorized") is not True:
        raise HomogeneityError("required filter submissions not authorized")
    for key in (
        "response_body_persistence_authorized",
        "raw_json_persistence_authorized",
        "data_array_element_inspection_authorized",
        "target_investment_values_inspection_authorized",
        "non_period_observation_values_inspection_authorized",
        "source_selection_uses_filter_result",
        "zip_resource_request_authorized",
        "interactive_disclaimer_form_submission_authorized",
        "synthetic_personal_information_submission_authorized",
        "quarterly_flow_interpretation_authorized",
        "cross_quarter_additivity_authorized",
        "annual_sum_authorized",
        "pma_pmdn_combination_authorized",
        "external_fx_conversion_authorized",
        "geography_mapping_authorized",
        "numeric_aggregation_authorized",
        "statistical_model_fit_authorized",
        "causal_claim_authorized",
        "monetary_wasted_potential_estimate_authorized",
    ):
        if c.get(key) is not False:
            raise HomogeneityError(f"forbidden authorization enabled: {key}")
    return c


def data_array_is_empty(body: bytes) -> bool | None:
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
        raise HomogeneityError(f"transport error: {exc}") from exc

    if len(body) > max_bytes:
        raise HomogeneityError("response exceeded preregistered byte limit")

    data_empty = None
    records_total = None
    records_filtered = None
    json_parsed = False
    if status == 200 and content_type.lower().startswith("application/json"):
        data_empty = data_array_is_empty(body)
        if data_empty is True:
            payload = json.loads(body.decode("utf-8"))
            json_parsed = True
            if not isinstance(payload, dict):
                raise HomogeneityError("zero-row response is not a JSON object")
            rt = payload.get("recordsTotal")
            rf = payload.get("recordsFiltered")
            records_total = rt if isinstance(rt, int) else None
            records_filtered = rf if isinstance(rf, int) else None

    return {
        "status": status,
        "content_type": content_type,
        "response_body_bytes_received": len(body),
        "data_array_empty": data_empty,
        "json_parsed": json_parsed,
        "records_total": records_total,
        "records_filtered": records_filtered,
        "response_body_persisted": False,
        "raw_json_persisted": False,
        "data_array_elements_inspected": False,
        "target_investment_values_inspected": False,
        "non_period_observation_values_inspected": False,
    }


def build_url(contract: dict[str, Any], resource_uuid: str, search_value: str) -> str:
    params: dict[str, str] = {
        "dataset_detail_parent_id": resource_uuid,
        **{str(k): str(v) for k, v in contract["common_query_parameters"].items()},
        "columns[0][search][value]": search_value,
    }
    url = contract["target_route"] + "?" + urllib.parse.urlencode(params)
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != contract["official_domain"] or parsed.path != "/data":
        raise HomogeneityError("request escaped locked official route")
    return url


def main() -> int:
    contract = load_contract()
    period_manifest = load_json(PERIOD)
    baseline_manifest = load_json(BASELINE)
    binding_manifest = load_json(BINDING)

    if period_manifest.get("all_pilot_period_identities_match") is not True:
        raise HomogeneityError("period-prefix prerequisite not qualified")
    if baseline_manifest.get("schema_qualified") is not True:
        raise HomogeneityError("zero-row baseline prerequisite not qualified")
    if binding_manifest.get("binding_qualified") is not True:
        raise HomogeneityError("binding prerequisite not qualified")

    period_by_key = {(int(r["year"]), str(r["quarter"])): r for r in period_manifest["pilot_results"]}
    baseline_by_key = {(int(r["year"]), str(r["quarter"])): r for r in baseline_manifest["pilot_results"]}
    binding_by_key = {(int(r["year"]), str(r["quarter"])): r for r in binding_manifest["pilot_results"]}
    max_bytes = int(contract["max_response_body_bytes"])
    sentinel = str(contract["negative_control_value"])
    results: list[dict[str, Any]] = []

    for pilot in contract["pilot_periods"]:
        key = (int(pilot["year"]), str(pilot["quarter"]))
        p = period_by_key.get(key)
        b = baseline_by_key.get(key)
        bind = binding_by_key.get(key)
        if p is None or b is None or bind is None:
            raise HomogeneityError(f"pilot prerequisite missing: {key}")
        baseline_total = b.get("records_total")
        if not isinstance(baseline_total, int) or baseline_total <= 0:
            raise HomogeneityError(f"invalid baseline total for {key}")
        exact_value = str(p["source_native_period_value"])
        uuid = str(bind["preview_parameter_value"])

        exact_url = build_url(contract, uuid, exact_value)
        negative_url = build_url(contract, uuid, sentinel)
        exact = request_zero_row(exact_url, max_bytes)
        negative = request_zero_row(negative_url, max_bytes)

        exact_qualified = (
            exact["status"] == 200
            and exact["data_array_empty"] is True
            and exact["records_total"] == baseline_total
            and exact["records_filtered"] == baseline_total
        )
        negative_qualified = (
            negative["status"] == 200
            and negative["data_array_empty"] is True
            and negative["records_total"] == baseline_total
            and negative["records_filtered"] == 0
        )
        results.append({
            "year": key[0],
            "quarter": key[1],
            "dataset_identifier": p["dataset_identifier"],
            "source_native_period_value": exact_value,
            "baseline_records_total": baseline_total,
            "exact_period_filter": {
                "request_url": exact_url,
                **exact,
                "qualified": exact_qualified,
            },
            "negative_control_filter": {
                "request_url": negative_url,
                "submitted_value": sentinel,
                **negative,
                "qualified": negative_qualified,
            },
            "period_homogeneous": exact_qualified and negative_qualified,
            "response_body_persisted": False,
            "raw_json_persisted": False,
            "data_array_elements_inspected": False,
            "target_investment_values_inspected": False,
            "non_period_observation_values_inspected": False,
        })

    all_homogeneous = all(r["period_homogeneous"] for r in results)
    q2 = next(r for r in results if r["year"] == 2025 and r["quarter"] == "II")
    payload = {
        "schema": "ranah-observatory/milestone27-bkpm-period-homogeneity-probe/v1",
        "milestone": 27,
        "stage": "stage0j_period_homogeneity_zero_row_probe",
        "pilot_count": len(results),
        "pilot_results": results,
        "all_pilots_period_homogeneous": all_homogeneous,
        "source_2025_q2_resource_wide_period_identity_qualified": q2["period_homogeneous"],
        "source_2025_q2_resource_wide_period_value": q2["source_native_period_value"],
        "response_body_persisted": False,
        "raw_json_persisted": False,
        "data_array_elements_inspected": False,
        "target_investment_values_inspected": False,
        "non_period_observation_values_inspected": False,
        "source_selection_uses_filter_result": False,
        "quarterly_flow_interpretation_authorized": False,
        "cross_quarter_additivity_authorized": False,
        "annual_sum_authorized": False,
        "pma_pmdn_combination_authorized": False,
        "external_fx_conversion_authorized": False,
        "geography_mapping_authorized": False,
        "statistical_model_fit": False,
        "causal_claim_created": False,
        "monetary_wasted_potential_estimated": False,
        "contract": {"path": rel(CONTRACT), "sha256": sha256_path(CONTRACT)},
        "period_prefix": {"path": rel(PERIOD), "sha256": sha256_path(PERIOD)},
        "zero_row_baseline": {"path": rel(BASELINE), "sha256": sha256_path(BASELINE)},
        "binding": {"path": rel(BINDING), "sha256": sha256_path(BINDING)},
    }
    write_json(OUT, payload)
    print(json.dumps({
        "all_pilots_period_homogeneous": all_homogeneous,
        "q2_resource_wide_period_identity_qualified": payload["source_2025_q2_resource_wide_period_identity_qualified"],
        "counts": {
            f"{r['year']}-{r['quarter']}": {
                "baseline": r["baseline_records_total"],
                "exact_filtered": r["exact_period_filter"]["records_filtered"],
                "negative_filtered": r["negative_control_filter"]["records_filtered"],
            }
            for r in results
        },
        "target_investment_values_inspected": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError, HomogeneityError) as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
