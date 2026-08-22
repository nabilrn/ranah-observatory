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
CONTRACT = ROOT / "data/manifests/milestone27_period_identity_prefix_contract.json"
BINDING = ROOT / "data/manifests/milestone27_bkpm_preview_parameter_binding.json"
SCHEMA = ROOT / "data/manifests/milestone27_bkpm_public_data_zero_row_probe.json"
OUT = ROOT / "data/manifests/milestone27_bkpm_period_identity_prefix_probe.json"
USER_AGENT = "ranah-observatory/1.0 (+https://github.com/nabilrn/ranah-observatory)"


class PeriodPrefixError(RuntimeError):
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
    if c.get("schema") != "ranah-observatory/milestone27-period-identity-prefix-contract/v1":
        raise PeriodPrefixError("unexpected period-prefix contract schema")
    if c.get("contract_locked_before_live_row_prefix_request") is not True:
        raise PeriodPrefixError("period-prefix contract not locked")
    if c.get("request_method") != "GET" or c.get("get_request_authorized") is not True:
        raise PeriodPrefixError("GET not authorized")
    if c.get("follow_redirects") is not False:
        raise PeriodPrefixError("redirect following must be disabled")
    if c.get("stream_read_mode") != "one_byte_at_a_time_until_first_data_object_periode_string_closes":
        raise PeriodPrefixError("unexpected stream read mode")
    if c.get("response_prefix_read_authorized") is not True:
        raise PeriodPrefixError("response prefix read not authorized")
    if c.get("response_remainder_read_authorized") is not False:
        raise PeriodPrefixError("response remainder read must remain forbidden")
    if c.get("period_scalar_extraction_authorized") is not True:
        raise PeriodPrefixError("period scalar extraction not authorized")
    for key in (
        "response_body_persistence_authorized",
        "raw_json_persistence_authorized",
        "subsequent_data_object_key_or_value_read_authorized",
        "target_investment_values_inspection_authorized",
        "non_period_observation_values_inspection_authorized",
        "source_selection_uses_period_value",
        "record_selection_uses_target_investment_values",
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
            raise PeriodPrefixError(f"forbidden authorization enabled: {key}")
    return c


def read_one(response: Any, state: dict[str, int], limit: int) -> str:
    if state["bytes"] >= limit:
        raise PeriodPrefixError("response prefix exceeded preregistered byte limit")
    chunk = response.read(1)
    if not chunk:
        raise PeriodPrefixError("response ended before period scalar was completed")
    state["bytes"] += 1
    try:
        return chunk.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PeriodPrefixError("non-UTF8 byte encountered in structural prefix") from exc


def skip_ws(response: Any, state: dict[str, int], limit: int) -> str:
    while True:
        ch = read_one(response, state, limit)
        if not ch.isspace():
            return ch


def read_json_string_after_open_quote(response: Any, state: dict[str, int], limit: int) -> str:
    chars: list[str] = []
    escaped = False
    while True:
        ch = read_one(response, state, limit)
        if escaped:
            chars.append("\\" + ch)
            escaped = False
            continue
        if ch == "\\":
            escaped = True
            continue
        if ch == '"':
            raw = '"' + "".join(chars) + '"'
            value = json.loads(raw)
            if not isinstance(value, str):
                raise PeriodPrefixError("JSON string decoder returned non-string")
            return value
        chars.append(ch)


def read_first_period_scalar(url: str, limit: int) -> tuple[int, str, str, int, str]:
    opener = urllib.request.build_opener(NoRedirect())
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        response = opener.open(req, timeout=40)
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        exc.close()
        return status, "", "", 0, "http_error"
    except urllib.error.URLError as exc:
        raise PeriodPrefixError(f"GET transport error for {url}: {exc}") from exc

    state = {"bytes": 0}
    status = int(response.status)
    content_type = response.headers.get("Content-Type", "")
    try:
        if status != 200 or not content_type.lower().startswith("application/json"):
            return status, content_type, "", state["bytes"], "http_or_content_type_not_qualified"

        # Locate the top-level data array token. This intentionally ignores all
        # preceding metadata and never parses observation values.
        target = '"data"'
        matched = 0
        while matched < len(target):
            ch = read_one(response, state, limit)
            if ch == target[matched]:
                matched += 1
            else:
                matched = 1 if ch == target[0] else 0

        ch = skip_ws(response, state, limit)
        if ch != ":":
            raise PeriodPrefixError("data token not followed by colon")
        ch = skip_ws(response, state, limit)
        if ch != "[":
            raise PeriodPrefixError("data token not followed by array")
        ch = skip_ws(response, state, limit)
        if ch != "{":
            raise PeriodPrefixError("first data element is not an object")
        ch = skip_ws(response, state, limit)
        if ch != '"':
            raise PeriodPrefixError("first data-object key is not a JSON string")
        first_key = read_json_string_after_open_quote(response, state, limit)
        if first_key != "periode":
            raise PeriodPrefixError(f"first data-object key is {first_key!r}, expected 'periode'")
        ch = skip_ws(response, state, limit)
        if ch != ":":
            raise PeriodPrefixError("periode key not followed by colon")
        ch = skip_ws(response, state, limit)
        if ch != '"':
            raise PeriodPrefixError("periode value is not a JSON string")
        period_value = read_json_string_after_open_quote(response, state, limit)

        # Critical boundary: the final byte read above is the closing quote of
        # the period scalar. Do not read the following comma or any later field.
        return status, content_type, period_value, state["bytes"], "period_prefix_read_complete"
    finally:
        response.close()


def quarter_matches(raw: str, year: int, quarter: str) -> bool:
    text = raw.casefold().strip()
    if str(year) not in text:
        return False

    qnum = {"I": "1", "II": "2", "III": "3", "IV": "4"}[quarter]
    qroman = quarter.casefold()
    patterns = [
        rf"\btriwulan\s*[-:/]?\s*{re.escape(qroman)}\b",
        rf"\btriwulan\s*[-:/]?\s*{qnum}\b",
        rf"\btw\s*[-:/]?\s*{re.escape(qroman)}\b",
        rf"\btw\s*[-:/]?\s*{qnum}\b",
        rf"\bq\s*[-:/]?\s*{qnum}\b",
        rf"\bquarter\s*[-:/]?\s*{qnum}\b",
    ]
    if any(re.search(pattern, text) for pattern in patterns):
        return True

    # Fallback only for compact year-quarter forms such as 2025-2 / 2025_II.
    compact = re.sub(r"\s+", "", text)
    fallback = [
        rf"{year}[-_/]{qnum}(?:\D|$)",
        rf"{year}[-_/]{re.escape(qroman)}(?:\D|$)",
        rf"{qnum}[-_/]{year}(?:\D|$)",
        rf"{re.escape(qroman)}[-_/]{year}(?:\D|$)",
    ]
    return any(re.search(pattern, compact) for pattern in fallback)


def main() -> int:
    contract = load_contract()
    binding = load_json(BINDING)
    schema = load_json(SCHEMA)
    if binding.get("binding_qualified") is not True:
        raise PeriodPrefixError("qualified parameter binding prerequisite missing")
    if schema.get("schema_qualified") is not True:
        raise PeriodPrefixError("qualified zero-row schema prerequisite missing")
    if schema.get("qualified_declared_columns", [None])[0] != "periode":
        raise PeriodPrefixError("qualified schema does not place periode first")

    by_period = {(int(r["year"]), str(r["quarter"])): r for r in binding["pilot_results"]}
    results: list[dict[str, Any]] = []
    limit = int(contract["max_prefix_bytes"])

    for pilot in contract["pilot_periods"]:
        year = int(pilot["year"])
        quarter = str(pilot["quarter"])
        row = by_period.get((year, quarter))
        if row is None:
            raise PeriodPrefixError(f"pilot missing from binding: {year}-{quarter}")
        params = {
            "dataset_detail_parent_id": row["preview_parameter_value"],
            "draw": "1",
            "start": "0",
            "length": "1",
        }
        request_url = contract["target_route"] + "?" + urllib.parse.urlencode(params)
        parsed = urllib.parse.urlparse(request_url)
        if parsed.scheme != "https" or parsed.hostname != contract["official_domain"] or parsed.path != "/data":
            raise PeriodPrefixError(f"request escaped locked route: {request_url}")

        status, content_type, raw_period, prefix_bytes, classification = read_first_period_scalar(request_url, limit)
        identity_match = classification == "period_prefix_read_complete" and quarter_matches(raw_period, year, quarter)
        results.append({
            "year": year,
            "quarter": quarter,
            "pilot_role": pilot["role"],
            "expected_metadata_identity": pilot["expected_metadata_identity"],
            "dataset_identifier": row["dataset_identifier"],
            "request_method": "GET",
            "request_url": request_url,
            "status": status,
            "content_type": content_type,
            "response_prefix_bytes_read": prefix_bytes,
            "stream_stopped_immediately_after_period_closing_quote": classification == "period_prefix_read_complete",
            "first_data_object_key": "periode" if classification == "period_prefix_read_complete" else "unresolved",
            "source_native_period_value": raw_period,
            "period_identity_matches_preregistered_year_quarter": identity_match,
            "classification": classification if not identity_match else "period_identity_match",
            "response_remainder_read": False,
            "response_body_persisted": False,
            "raw_json_persisted": False,
            "subsequent_observation_field_read": False,
            "target_investment_values_inspected": False,
            "non_period_observation_values_inspected": False,
        })

    q2 = next(r for r in results if r["year"] == 2025 and r["quarter"] == "II")
    all_match = all(r["period_identity_matches_preregistered_year_quarter"] for r in results)
    payload = {
        "schema": "ranah-observatory/milestone27-bkpm-period-identity-prefix-probe/v1",
        "milestone": 27,
        "stage": "stage0i_period_identity_prefix_probe",
        "pilot_count": len(results),
        "pilot_results": results,
        "all_pilot_period_identities_match": all_match,
        "source_2025_q2_period_identity_matches_q2": q2["period_identity_matches_preregistered_year_quarter"],
        "source_2025_q2_period_value": q2["source_native_period_value"],
        "response_remainder_read": False,
        "response_body_persisted": False,
        "raw_json_persisted": False,
        "subsequent_observation_field_read": False,
        "target_investment_values_inspected": False,
        "non_period_observation_values_inspected": False,
        "source_selection_uses_period_value": False,
        "record_selection_uses_target_investment_values": False,
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
        "binding": {"path": rel(BINDING), "sha256": sha256_path(BINDING)},
        "schema_probe": {"path": rel(SCHEMA), "sha256": sha256_path(SCHEMA)},
    }
    write_json(OUT, payload)
    print(json.dumps({
        "period_values": {(str(r['year']) + '-' + r['quarter']): r['source_native_period_value'] for r in results},
        "all_match": all_match,
        "source_2025_q2_period_identity_matches_q2": payload["source_2025_q2_period_identity_matches_q2"],
        "target_investment_values_inspected": False,
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError, PeriodPrefixError) as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
