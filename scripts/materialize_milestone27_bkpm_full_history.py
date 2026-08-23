#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "data/manifests/milestone27_stage1_full_history_contract.json"
INVENTORY = ROOT / "data/analysis/engine/investment_realization_v1/m27-bkpm-resource-inventory.csv"
SCHEMA = ROOT / "data/manifests/milestone27_bkpm_public_data_zero_row_probe.json"
PILOT = ROOT / "data/manifests/milestone27_bkpm_stage1_pilot.json"
Q2_PERIOD = ROOT / "data/manifests/milestone27_bkpm_period_identity_prefix_probe.json"
GEO_CONTRACT = ROOT / "data/registries/bkpm_sumbar_geography_contract.csv"
CANONICAL_GEO = ROOT / "data/registries/geographies.csv"
RAW_ROOT = ROOT / "data/processed/bkpm/m27_full_history"
OUT_CSV = ROOT / "data/analysis/engine/investment_realization_v1/m27-bkpm-quarterly-history.csv"
OUT_AUDIT = ROOT / "data/analysis/engine/investment_realization_v1/m27-bkpm-quarter-audit.csv"
OUT_MANIFEST = ROOT / "data/manifests/milestone27_bkpm_full_history.json"
USER_AGENT = "ranah-observatory/1.0 (+https://github.com/nabilrn/ranah-observatory)"
QNUM = {"I": 1, "II": 2, "III": 3, "IV": 4}


class HarvestError(RuntimeError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        return None


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = unicodedata.normalize("NFKD", str(value)).casefold()
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_source_geography(value: Any) -> tuple[str | None, str]:
    text = normalize_text(value)
    if re.match(r"^(kab|kabupaten)\b", text):
        return "regency", re.sub(r"^(kab|kabupaten)\b\s*", "", text, count=1)
    if re.match(r"^kota\b", text):
        return "city", re.sub(r"^kota\b\s*", "", text, count=1)
    return None, text


def load_geography_map() -> dict[tuple[str, str], dict[str, str]]:
    mapping: dict[tuple[str, str], dict[str, str]] = {}
    with GEO_CONTRACT.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 19:
        raise HarvestError(f"expected 19 geography rows, found {len(rows)}")
    for row in rows:
        names = [row["normalized_name"]]
        names.extend(x.strip() for x in row.get("accepted_normalized_aliases", "").split("|") if x.strip())
        for name in names:
            key = (row["required_source_type"], normalize_text(name))
            if key in mapping and mapping[key]["geography_id"] != row["geography_id"]:
                raise HarvestError(f"ambiguous geography alias: {key}")
            mapping[key] = row
    return mapping


def quarter_matches(raw: Any, year: int, quarter: str) -> bool:
    raw_cf = unicodedata.normalize("NFKC", str(raw)).casefold()
    if str(year) not in raw_cf:
        return False
    qnum = str(QNUM[quarter])
    qroman = quarter.casefold()
    return any(re.search(pattern, raw_cf) for pattern in (
        rf"\btriwulan\s*[-:/]?\s*{re.escape(qroman)}\b",
        rf"\btriwulan\s*[-:/]?\s*{qnum}\b",
        rf"\btw\s*[-:/]?\s*{re.escape(qroman)}\b",
        rf"\btw\s*[-:/]?\s*{qnum}\b",
        rf"\bq\s*[-:/]?\s*{qnum}\b",
        rf"\bquarter\s*[-:/]?\s*{qnum}\b",
    ))


def parse_decimal(value: Any) -> tuple[Decimal | None, bool]:
    if value is None or str(value).strip() == "":
        return None, True
    if isinstance(value, bool):
        raise HarvestError("boolean target metric is invalid")
    text = str(value).strip()
    try:
        number = Decimal(text)
    except InvalidOperation as exc:
        raise HarvestError(f"target metric is not Decimal-compatible: {text!r}") from exc
    if not number.is_finite():
        raise HarvestError(f"target metric is not finite: {text!r}")
    return number, False


def decimal_text(value: Decimal) -> str:
    if value == 0:
        return "0"
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def fetch_json(url: str, max_bytes: int = 12_000_000) -> tuple[int, str, bytes, dict[str, Any] | None]:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "data.bkpm.go.id" or parsed.path != "/data":
        raise HarvestError(f"request escaped locked BKPM route: {url}")
    opener = urllib.request.build_opener(NoRedirect())
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        response = opener.open(req, timeout=90)
        status = int(response.status)
        content_type = response.headers.get("Content-Type", "")
        body = response.read(max_bytes + 1)
        response.close()
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        content_type = exc.headers.get("Content-Type", "")
        body = exc.read(max_bytes + 1)
        exc.close()
    except urllib.error.URLError as exc:
        raise HarvestError(f"transport error: {exc}") from exc
    if len(body) > max_bytes:
        raise HarvestError("response exceeded safety byte limit")
    payload = None
    if status == 200 and content_type.lower().startswith("application/json"):
        payload = json.loads(body.decode("utf-8"), parse_int=str, parse_float=str)
        if not isinstance(payload, dict):
            payload = None
    return status, content_type, body, payload


def request_url(uuid: str, start: int, length: int, search_value: str) -> str:
    params = {
        "dataset_detail_parent_id": uuid,
        "draw": "1",
        "start": str(start),
        "length": str(length),
        "search[regex]": "false",
        "search[value]": search_value,
    }
    return "https://data.bkpm.go.id/data?" + urllib.parse.urlencode(params)


def read_inventory() -> list[dict[str, str]]:
    with INVENTORY.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 64:
        raise HarvestError(f"expected 64 inventory rows, found {len(rows)}")
    keys = {(int(r["year"]), r["quarter"]) for r in rows}
    expected = {(y, q) for y in range(2010, 2026) for q in QNUM}
    if keys != expected:
        raise HarvestError("inventory does not exactly cover 2010-2025 x Q1-Q4")
    for r in rows:
        if not r.get("resource_download_action_file_uuid", "").strip():
            raise HarvestError(f"missing resource UUID for {r['year']}-{r['quarter']}")
        key = (int(r["year"]), r["quarter"])
        if r.get("semantic_family_state") != "semantic_family_match" and key != (2025, "II"):
            raise HarvestError(f"unresolved semantic inventory row: {key}")
    return sorted(rows, key=lambda r: (int(r["year"]), QNUM[r["quarter"]]))


def main() -> int:
    contract = load_json(CONTRACT)
    if contract.get("schema") != "ranah-observatory/milestone27-stage1-full-history-contract/v1":
        raise HarvestError("unexpected full-history contract schema")
    if contract.get("contract_locked_before_full_history_retrieval") is not True:
        raise HarvestError("full-history contract not locked")
    pilot = load_json(PILOT)
    if pilot.get("pilot_success") is not True:
        raise HarvestError("Stage 1 pilot prerequisite not qualified")
    q2 = load_json(Q2_PERIOD)
    if q2.get("source_2025_q2_period_identity_matches_q2") is not True:
        raise HarvestError("2025-Q2 period identity not resolved")
    schema = load_json(SCHEMA)
    if schema.get("schema_qualified") is not True:
        raise HarvestError("schema prerequisite not qualified")
    expected_columns = list(schema["qualified_declared_columns"])
    for key in (
        "pma_pmdn_combination_authorized", "cross_quarter_additivity_authorized", "annual_sum_authorized",
        "q4_as_annual_total_authorized", "external_fx_conversion_authorized", "missing_as_zero_authorized",
        "per_capita_normalization_authorized", "ranking_authorized", "statistical_model_fit_authorized",
        "causal_claim_authorized", "monetary_wasted_potential_estimate_authorized",
    ):
        if contract.get(key) is not False:
            raise HarvestError(f"forbidden authorization enabled: {key}")

    inventory = read_inventory()
    geo_map = load_geography_map()
    page_length = int(contract["page_length"])
    RAW_ROOT.mkdir(parents=True, exist_ok=True)

    all_output_rows: list[dict[str, Any]] = []
    quarter_results: list[dict[str, Any]] = []

    for inv in inventory:
        year = int(inv["year"])
        quarter = inv["quarter"]
        qn = QNUM[quarter]
        uuid = inv["resource_download_action_file_uuid"]
        quarter_dir = RAW_ROOT / str(year) / f"q{qn}"
        quarter_dir.mkdir(parents=True, exist_ok=True)
        fail: list[str] = []
        raw_pages: list[dict[str, Any]] = []

        zero_url = request_url(uuid, 0, 0, contract["search_value"])
        status, content_type, zero_body, zero_payload = fetch_json(zero_url)
        zero_path = quarter_dir / "count-schema.json"
        zero_path.write_bytes(zero_body)
        raw_pages.append({"path": rel(zero_path), "sha256": sha256_bytes(zero_body), "bytes": len(zero_body), "start": 0, "length": 0})

        count = None
        if status != 200:
            fail.append(f"count_http_status_{status}")
        if not content_type.lower().startswith("application/json"):
            fail.append("count_content_type_not_json")
        if zero_payload is None:
            fail.append("count_payload_not_object")
        else:
            try:
                count = int(zero_payload.get("recordsFiltered"))
                count_total = int(zero_payload.get("recordsTotal"))
            except (TypeError, ValueError):
                count = None
                count_total = None
                fail.append("count_fields_not_integer")
            if count is not None and count_total != count:
                fail.append("observed_count_semantics_changed")
            if zero_payload.get("data") != []:
                fail.append("length_zero_not_honored")
            if zero_payload.get("columns") != expected_columns:
                fail.append("declared_schema_mismatch")

        data: list[Any] = []
        if not fail and count is not None and count > 0:
            start = 0
            while start < count:
                length = min(page_length, count - start)
                url = request_url(uuid, start, length, contract["search_value"])
                p_status, p_ct, body, payload = fetch_json(url)
                page_path = quarter_dir / f"page-{start:06d}.json"
                page_path.write_bytes(body)
                raw_pages.append({"path": rel(page_path), "sha256": sha256_bytes(body), "bytes": len(body), "start": start, "length": length})
                if p_status != 200:
                    fail.append(f"page_http_status_{p_status}_start_{start}")
                    break
                if not p_ct.lower().startswith("application/json") or payload is None:
                    fail.append(f"page_not_json_start_{start}")
                    break
                try:
                    page_total = int(payload.get("recordsTotal"))
                    page_filtered = int(payload.get("recordsFiltered"))
                except (TypeError, ValueError):
                    fail.append(f"page_counts_invalid_start_{start}")
                    break
                if page_total != count or page_filtered != count:
                    fail.append(f"page_count_changed_start_{start}")
                    break
                if payload.get("columns") != expected_columns:
                    fail.append(f"page_schema_changed_start_{start}")
                    break
                page_data = payload.get("data")
                if not isinstance(page_data, list):
                    fail.append(f"page_data_not_list_start_{start}")
                    break
                if len(page_data) != length:
                    fail.append(f"page_length_mismatch_start_{start}")
                    break
                data.extend(page_data)
                start += len(page_data)

        if count is not None and len(data) != count:
            if count != 0:
                fail.append("reconstructed_row_count_mismatch")

        source_periods: set[str] = set()
        source_statuses: set[str] = set()
        source_labels: set[str] = set()
        mapped_geographies: set[str] = set()
        unmapped_labels: set[str] = set()
        false_positive_province_count = 0
        period_mismatch_count = 0
        unexpected_status_count = 0
        duplicate_dimension_count = 0
        negative_counts = {"investasi_rp_juta": 0, "investasi_us_ribu": 0}
        dimension_seen: set[tuple[str, ...]] = set()
        records: list[dict[str, Any]] = []

        if not fail:
            for idx, row in enumerate(data):
                if not isinstance(row, dict) or set(row.keys()) != set(expected_columns):
                    fail.append(f"row_schema_mismatch_{idx}")
                    continue
                period_raw = str(row.get("periode", ""))
                province_raw = str(row.get("provinsi", ""))
                geo_raw = str(row.get("kabupaten_kota", ""))
                status_pm = str(row.get("status_penanaman_modal", "")).strip().upper()
                source_periods.add(period_raw)
                source_statuses.add(status_pm)
                source_labels.add(geo_raw)
                if normalize_text(province_raw) != contract["accepted_province_normalized"]:
                    false_positive_province_count += 1
                    continue
                if not quarter_matches(period_raw, year, quarter):
                    period_mismatch_count += 1
                    continue
                if status_pm not in contract["accepted_status_penanaman_modal"]:
                    unexpected_status_count += 1
                    continue
                source_type, source_name = normalize_source_geography(geo_raw)
                mapped = geo_map.get((source_type or "", source_name)) if source_type else None
                if mapped is None:
                    unmapped_labels.add(geo_raw)
                    continue
                mapped_geographies.add(mapped["geography_id"])
                dim = tuple("" if row.get(field) is None else str(row.get(field)) for field in contract["source_dimensions"])
                if dim in dimension_seen:
                    duplicate_dimension_count += 1
                else:
                    dimension_seen.add(dim)
                rp, rp_missing = parse_decimal(row.get("investasi_rp_juta"))
                usd, usd_missing = parse_decimal(row.get("investasi_us_ribu"))
                if rp is not None and rp < 0:
                    negative_counts["investasi_rp_juta"] += 1
                if usd is not None and usd < 0:
                    negative_counts["investasi_us_ribu"] += 1
                records.append({
                    "geography_id": mapped["geography_id"], "canonical_name": mapped["canonical_name"],
                    "status_penanaman_modal": status_pm, "rp": rp, "rp_missing": rp_missing,
                    "usd": usd, "usd_missing": usd_missing,
                })

        if false_positive_province_count:
            fail.append("global_search_returned_non_sumbar_rows")
        if period_mismatch_count:
            fail.append("row_period_mismatch")
        if unexpected_status_count:
            fail.append("unexpected_status_penanaman_modal")
        if unmapped_labels:
            fail.append("unmapped_kabupaten_kota")
        if duplicate_dimension_count:
            fail.append("duplicate_complete_source_dimension_tuple")

        qualified = not fail
        emitted = 0
        if qualified and count and count > 0:
            grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
            for r in records:
                grouped[(r["geography_id"], r["status_penanaman_modal"])].append(r)
            for (geo_id, status_pm), grp in sorted(grouped.items()):
                rp_missing = sum(1 for r in grp if r["rp_missing"])
                usd_missing = sum(1 for r in grp if r["usd_missing"])
                rp_complete = rp_missing == 0
                usd_complete = usd_missing == 0
                rp_sum = sum((r["rp"] for r in grp if r["rp"] is not None), Decimal(0)) if rp_complete else None
                usd_sum = sum((r["usd"] for r in grp if r["usd"] is not None), Decimal(0)) if usd_complete else None
                all_output_rows.append({
                    "year": year, "quarter": quarter, "geography_id": geo_id,
                    "canonical_name": grp[0]["canonical_name"], "status_penanaman_modal": status_pm,
                    "observed_source_row_count": len(grp),
                    "investasi_rp_juta_complete": str(rp_complete).lower(),
                    "investasi_rp_juta_missing_rows": rp_missing,
                    "investasi_rp_juta_sum": "" if rp_sum is None else decimal_text(rp_sum),
                    "investasi_us_ribu_complete": str(usd_complete).lower(),
                    "investasi_us_ribu_missing_rows": usd_missing,
                    "investasi_us_ribu_sum": "" if usd_sum is None else decimal_text(usd_sum),
                })
                emitted += 1

        quarter_results.append({
            "year": year, "quarter": quarter, "dataset_identifier": inv["dataset_identifier"],
            "resource_file_uuid": uuid, "sumbar_source_row_count": count,
            "reconstructed_source_row_count": len(data), "raw_page_count": len(raw_pages),
            "raw_pages": raw_pages, "observed_source_period_values": sorted(source_periods),
            "observed_source_status_values": sorted(source_statuses),
            "observed_source_geography_labels": sorted(source_labels),
            "mapped_geography_count": len(mapped_geographies), "mapped_geography_ids": sorted(mapped_geographies),
            "false_positive_province_row_count": false_positive_province_count,
            "period_mismatch_row_count": period_mismatch_count,
            "unexpected_status_row_count": unexpected_status_count,
            "unmapped_geography_labels": sorted(unmapped_labels),
            "duplicate_source_dimension_tuple_count": duplicate_dimension_count,
            "negative_metric_row_counts": negative_counts,
            "emitted_geography_status_observation_count": emitted,
            "qualified": qualified, "classification": "no_observed_sumbar_rows" if qualified and count == 0 else ("qualified_numeric_quarter" if qualified else "held_failed_validation"),
            "fail_reasons": sorted(set(fail)),
        })

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fields = ["year","quarter","geography_id","canonical_name","status_penanaman_modal","observed_source_row_count","investasi_rp_juta_complete","investasi_rp_juta_missing_rows","investasi_rp_juta_sum","investasi_us_ribu_complete","investasi_us_ribu_missing_rows","investasi_us_ribu_sum"]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(sorted(all_output_rows, key=lambda r: (r["year"], QNUM[r["quarter"]], r["geography_id"], r["status_penanaman_modal"])))

    audit_fields = ["year","quarter","sumbar_source_row_count","reconstructed_source_row_count","mapped_geography_count","emitted_geography_status_observation_count","classification","qualified","fail_reasons"]
    with OUT_AUDIT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=audit_fields)
        writer.writeheader()
        for r in quarter_results:
            writer.writerow({k: ("|".join(r[k]) if k == "fail_reasons" else r[k]) for k in audit_fields})

    success = len(quarter_results) == 64 and all(r["qualified"] for r in quarter_results) and len(all_output_rows) > 0
    manifest = {
        "schema": "ranah-observatory/milestone27-bkpm-full-history/v1",
        "milestone": 27, "stage": "stage1_full_quarterly_history",
        "quarter_count": len(quarter_results), "qualified_quarter_count": sum(1 for r in quarter_results if r["qualified"]),
        "zero_observed_sumbar_quarter_count": sum(1 for r in quarter_results if r["classification"] == "no_observed_sumbar_rows"),
        "failed_quarter_count": sum(1 for r in quarter_results if not r["qualified"]),
        "full_history_success": success,
        "source_row_count_total": sum((r["sumbar_source_row_count"] or 0) for r in quarter_results),
        "materialized_geography_quarter_status_observation_count": len(all_output_rows),
        "quarter_results": quarter_results,
        "target_investment_values_retrieved": True, "target_investment_values_inspected": True,
        "raw_filtered_response_persisted": True,
        "within_quarter_within_status_within_geography_addition_performed": success,
        "missing_values_coerced_to_zero": False, "absent_geography_status_groups_materialized_as_zero": False,
        "pma_pmdn_combination_performed": False, "cross_quarter_addition_performed": False,
        "annual_sum_performed": False, "q4_interpreted_as_annual_total": False,
        "external_fx_conversion_performed": False, "per_capita_normalization_performed": False,
        "ranking_created": False, "statistical_model_fit": False, "causal_claim_created": False,
        "monetary_wasted_potential_estimated": False,
        "output_csv": {"path": rel(OUT_CSV), "sha256": sha256_path(OUT_CSV)},
        "quarter_audit_csv": {"path": rel(OUT_AUDIT), "sha256": sha256_path(OUT_AUDIT)},
        "contract": {"path": rel(CONTRACT), "sha256": sha256_path(CONTRACT)},
        "inventory": {"path": rel(INVENTORY), "sha256": sha256_path(INVENTORY)},
        "pilot_prerequisite": {"path": rel(PILOT), "sha256": sha256_path(PILOT)},
        "geography_contract": {"path": rel(GEO_CONTRACT), "sha256": sha256_path(GEO_CONTRACT)},
        "canonical_geography_registry": {"path": rel(CANONICAL_GEO), "sha256": sha256_path(CANONICAL_GEO)},
    }
    write_json(OUT_MANIFEST, manifest)
    print(json.dumps({
        "full_history_success": success,
        "qualified_quarters": manifest["qualified_quarter_count"],
        "failed_quarters": manifest["failed_quarter_count"],
        "zero_observed_quarters": manifest["zero_observed_sumbar_quarter_count"],
        "source_rows": manifest["source_row_count_total"],
        "observations": len(all_output_rows),
        "failures": {f"{r['year']}-Q{QNUM[r['quarter']]}": r['fail_reasons'] for r in quarter_results if not r['qualified']},
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError, HarvestError) as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
