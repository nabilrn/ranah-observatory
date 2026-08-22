#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import io
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
CONTRACT = ROOT / "data/manifests/milestone27_stage1_pilot_contract.json"
SCHEMA = ROOT / "data/manifests/milestone27_bkpm_public_data_zero_row_probe.json"
SEARCH = ROOT / "data/manifests/milestone27_bkpm_sumbar_global_search_qualified.json"
BINDING = ROOT / "data/manifests/milestone27_bkpm_preview_parameter_binding.json"
GEO_CONTRACT = ROOT / "data/registries/bkpm_sumbar_geography_contract.csv"
CANONICAL_GEO = ROOT / "data/registries/geographies.csv"
RAW_ROOT = ROOT / "data/processed/bkpm/m27_stage1_pilot"
OUT_CSV = ROOT / "data/analysis/engine/investment_realization_v1/m27-bkpm-stage1-pilot-quarterly.csv"
OUT_MANIFEST = ROOT / "data/manifests/milestone27_bkpm_stage1_pilot.json"
USER_AGENT = "ranah-observatory/1.0 (+https://github.com/nabilrn/ranah-observatory)"


class PilotError(RuntimeError):
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
        name = re.sub(r"^(kab|kabupaten)\b\s*", "", text, count=1)
        return "regency", name
    if re.match(r"^kota\b", text):
        name = re.sub(r"^kota\b\s*", "", text, count=1)
        return "city", name
    return None, text


def load_geography_map() -> dict[tuple[str, str], dict[str, str]]:
    mapping: dict[tuple[str, str], dict[str, str]] = {}
    with GEO_CONTRACT.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 19:
        raise PilotError(f"expected 19 geography contract rows, found {len(rows)}")
    for row in rows:
        level = row["required_source_type"]
        names = [row["normalized_name"]]
        if row.get("accepted_normalized_aliases", "").strip():
            names.extend(part.strip() for part in row["accepted_normalized_aliases"].split("|") if part.strip())
        for name in names:
            key = (level, normalize_text(name))
            if key in mapping and mapping[key]["geography_id"] != row["geography_id"]:
                raise PilotError(f"ambiguous preregistered geography alias: {key}")
            mapping[key] = row
    return mapping


def quarter_matches(raw: Any, year: int, quarter: str) -> bool:
    text = normalize_text(raw)
    if str(year) not in text.split() and str(year) not in text:
        return False
    qnum = {"I": "1", "II": "2", "III": "3", "IV": "4"}[quarter]
    qroman = quarter.casefold()
    raw_cf = unicodedata.normalize("NFKC", str(raw)).casefold()
    patterns = [
        rf"\btriwulan\s*[-:/]?\s*{re.escape(qroman)}\b",
        rf"\btriwulan\s*[-:/]?\s*{qnum}\b",
        rf"\btw\s*[-:/]?\s*{re.escape(qroman)}\b",
        rf"\btw\s*[-:/]?\s*{qnum}\b",
        rf"\bq\s*[-:/]?\s*{qnum}\b",
        rf"\bquarter\s*[-:/]?\s*{qnum}\b",
    ]
    if any(re.search(p, raw_cf) for p in patterns):
        return True
    compact = re.sub(r"\s+", "", raw_cf)
    return any(re.search(p, compact) for p in (
        rf"{year}[-_/]{qnum}(?:\D|$)",
        rf"{year}[-_/]{re.escape(qroman)}(?:\D|$)",
        rf"{qnum}[-_/]{year}(?:\D|$)",
        rf"{re.escape(qroman)}[-_/]{year}(?:\D|$)",
    ))


def parse_decimal(value: Any) -> tuple[Decimal | None, bool]:
    if value is None:
        return None, True
    if isinstance(value, bool):
        raise PilotError("boolean target metric is invalid")
    text = str(value).strip()
    if text == "":
        return None, True
    try:
        number = Decimal(text)
    except InvalidOperation as exc:
        raise PilotError(f"target metric is not Decimal-compatible: {text!r}") from exc
    if not number.is_finite():
        raise PilotError(f"target metric is not finite: {text!r}")
    return number, False


def decimal_text(value: Decimal) -> str:
    if value == 0:
        return "0"
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def fetch(url: str, max_bytes: int = 10_000_000) -> tuple[int, str, bytes]:
    opener = urllib.request.build_opener(NoRedirect())
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        response = opener.open(req, timeout=60)
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
        raise PilotError(f"transport error: {exc}") from exc
    if len(body) > max_bytes:
        raise PilotError("response exceeded safety byte limit")
    return status, content_type, body


def load_contract() -> dict[str, Any]:
    c = load_json(CONTRACT)
    if c.get("schema") != "ranah-observatory/milestone27-stage1-pilot-contract/v1":
        raise PilotError("unexpected Stage 1 pilot contract schema")
    if c.get("contract_locked_before_target_investment_value_retrieval") is not True:
        raise PilotError("Stage 1 contract not locked before target retrieval")
    if c.get("target_investment_value_retrieval_authorized") is not True or c.get("target_investment_value_inspection_authorized") is not True:
        raise PilotError("target-value retrieval/inspection not authorized")
    if c.get("raw_filtered_response_persistence_authorized") is not True:
        raise PilotError("raw evidence persistence not authorized")
    if c.get("within_quarter_within_status_within_geography_addition_authorized") is not True:
        raise PilotError("within-quarter aggregation not authorized")
    for key in (
        "pma_pmdn_combination_authorized",
        "cross_quarter_additivity_authorized",
        "annual_sum_authorized",
        "q4_as_annual_total_authorized",
        "external_fx_conversion_authorized",
        "per_capita_normalization_authorized",
        "ranking_authorized",
        "statistical_model_fit_authorized",
        "causal_claim_authorized",
        "monetary_wasted_potential_estimate_authorized",
    ):
        if c.get(key) is not False:
            raise PilotError(f"forbidden Stage 1 authorization enabled: {key}")
    return c


def main() -> int:
    contract = load_contract()
    schema_manifest = load_json(SCHEMA)
    search_manifest = load_json(SEARCH)
    binding_manifest = load_json(BINDING)
    geo_map = load_geography_map()

    if schema_manifest.get("schema_qualified") is not True:
        raise PilotError("schema prerequisite not qualified")
    expected_columns = list(schema_manifest["qualified_declared_columns"])
    if expected_columns != [
        "periode", "status_penanaman_modal", "regional", "negara", "sektor_utama", "nama_sektor",
        "deskripsi_kbli_2digit", "provinsi", "kabupaten_kota", "jawa_luar_jawa", "pulau",
        "investasi_rp_juta", "investasi_us_ribu", "tki",
    ]:
        raise PilotError("qualified schema differs from locked Stage 1 schema")
    if search_manifest.get("global_search_transport_qualified_all_pilots") is not True:
        raise PilotError("Sumbar search transport prerequisite not qualified")
    if binding_manifest.get("binding_qualified") is not True:
        raise PilotError("resource binding prerequisite not qualified")

    search_by_key = {(int(r["year"]), str(r["quarter"])): r for r in search_manifest["pilot_results"]}
    binding_by_key = {(int(r["year"]), str(r["quarter"])): r for r in binding_manifest["pilot_results"]}

    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    all_output_rows: list[dict[str, Any]] = []
    pilot_results: list[dict[str, Any]] = []

    for pilot in contract["pilot_periods"]:
        year = int(pilot["year"])
        quarter = str(pilot["quarter"])
        key = (year, quarter)
        search_row = search_by_key.get(key)
        binding_row = binding_by_key.get(key)
        if search_row is None or binding_row is None:
            raise PilotError(f"pilot prerequisite missing: {key}")
        expected_count = int(search_row["sumbar_post_search_count"])
        params = {
            "dataset_detail_parent_id": binding_row["preview_parameter_value"],
            "draw": "1",
            "start": "0",
            "length": str(int(contract["request_length"])),
            "search[regex]": "false",
            "search[value]": contract["search_value"],
        }
        url = contract["target_route"] + "?" + urllib.parse.urlencode(params)
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https" or parsed.hostname != contract["official_domain"] or parsed.path != "/data":
            raise PilotError(f"request escaped locked route: {url}")

        status, content_type, body = fetch(url)
        raw_path = RAW_ROOT / f"{year}-q{quarter.lower()}.json"
        raw_path.write_bytes(body)

        fail_reasons: list[str] = []
        source_labels: set[str] = set()
        source_statuses: set[str] = set()
        source_periods: set[str] = set()
        mapped_geographies: set[str] = set()
        negative_metric_counts = {"investasi_rp_juta": 0, "investasi_us_ribu": 0}

        if status != 200:
            fail_reasons.append(f"http_status_{status}")
        if not content_type.lower().startswith("application/json"):
            fail_reasons.append("content_type_not_json")

        data: list[Any] = []
        records_total: int | None = None
        records_filtered: int | None = None
        columns: list[str] = []
        row_records: list[dict[str, Any]] = []
        if not fail_reasons:
            payload = json.loads(body.decode("utf-8"), parse_int=str, parse_float=str)
            if not isinstance(payload, dict):
                fail_reasons.append("response_not_object")
            else:
                raw_data = payload.get("data")
                raw_columns = payload.get("columns")
                try:
                    records_total = int(payload.get("recordsTotal"))
                    records_filtered = int(payload.get("recordsFiltered"))
                except (TypeError, ValueError):
                    fail_reasons.append("record_counts_not_integer")
                if not isinstance(raw_data, list):
                    fail_reasons.append("data_not_list")
                else:
                    data = raw_data
                if not isinstance(raw_columns, list) or not all(isinstance(v, str) for v in raw_columns):
                    fail_reasons.append("columns_not_string_list")
                else:
                    columns = list(raw_columns)

        if records_total != expected_count or records_filtered != expected_count or len(data) != expected_count:
            fail_reasons.append("filtered_response_count_mismatch")
        if columns != expected_columns:
            fail_reasons.append("declared_schema_mismatch")

        dimension_seen: set[tuple[str, ...]] = set()
        duplicate_dimension_count = 0
        unmapped_labels: set[str] = set()
        false_positive_province_count = 0
        period_mismatch_count = 0
        invalid_status_count = 0

        for idx, raw_row in enumerate(data):
            if not isinstance(raw_row, dict):
                fail_reasons.append(f"row_{idx}_not_object")
                continue
            if set(raw_row.keys()) != set(expected_columns):
                fail_reasons.append(f"row_{idx}_schema_mismatch")
                continue

            period_raw = str(raw_row.get("periode", ""))
            province_raw = str(raw_row.get("provinsi", ""))
            geo_raw = str(raw_row.get("kabupaten_kota", ""))
            status_raw = str(raw_row.get("status_penanaman_modal", "")).strip().upper()
            source_labels.add(geo_raw)
            source_statuses.add(status_raw)
            source_periods.add(period_raw)

            if normalize_text(province_raw) != contract["accepted_province_normalized"]:
                false_positive_province_count += 1
                continue
            if not quarter_matches(period_raw, year, quarter):
                period_mismatch_count += 1
                continue
            if status_raw not in contract["accepted_status_penanaman_modal"]:
                invalid_status_count += 1
                continue

            source_type, source_name = normalize_source_geography(geo_raw)
            mapped = geo_map.get((source_type or "", source_name)) if source_type else None
            if mapped is None:
                unmapped_labels.add(geo_raw)
                continue
            mapped_geographies.add(mapped["geography_id"])

            dim = tuple("" if raw_row.get(field) is None else str(raw_row.get(field)) for field in contract["source_dimensions"])
            if dim in dimension_seen:
                duplicate_dimension_count += 1
            else:
                dimension_seen.add(dim)

            rp, rp_missing = parse_decimal(raw_row.get("investasi_rp_juta"))
            usd, usd_missing = parse_decimal(raw_row.get("investasi_us_ribu"))
            if rp is not None and rp < 0:
                negative_metric_counts["investasi_rp_juta"] += 1
            if usd is not None and usd < 0:
                negative_metric_counts["investasi_us_ribu"] += 1

            row_records.append({
                "year": year,
                "quarter": quarter,
                "geography_id": mapped["geography_id"],
                "canonical_name": mapped["canonical_name"],
                "status_penanaman_modal": status_raw,
                "rp": rp,
                "rp_missing": rp_missing,
                "usd": usd,
                "usd_missing": usd_missing,
            })

        if false_positive_province_count:
            fail_reasons.append("global_search_returned_non_sumbar_rows")
        if period_mismatch_count:
            fail_reasons.append("row_period_mismatch")
        if invalid_status_count:
            fail_reasons.append("unexpected_status_penanaman_modal")
        if unmapped_labels:
            fail_reasons.append("unmapped_kabupaten_kota")
        if duplicate_dimension_count:
            fail_reasons.append("duplicate_complete_source_dimension_tuple")

        qualified = not fail_reasons
        emitted_count = 0
        if qualified:
            grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
            for record in row_records:
                grouped[(record["geography_id"], record["status_penanaman_modal"])].append(record)
            for (geography_id, status_pm), records in sorted(grouped.items()):
                rp_missing_count = sum(1 for r in records if r["rp_missing"])
                usd_missing_count = sum(1 for r in records if r["usd_missing"])
                rp_complete = rp_missing_count == 0
                usd_complete = usd_missing_count == 0
                rp_sum = sum((r["rp"] for r in records if r["rp"] is not None), Decimal(0)) if rp_complete else None
                usd_sum = sum((r["usd"] for r in records if r["usd"] is not None), Decimal(0)) if usd_complete else None
                canonical_name = records[0]["canonical_name"]
                all_output_rows.append({
                    "year": year,
                    "quarter": quarter,
                    "geography_id": geography_id,
                    "canonical_name": canonical_name,
                    "status_penanaman_modal": status_pm,
                    "observed_source_row_count": len(records),
                    "investasi_rp_juta_complete": str(rp_complete).lower(),
                    "investasi_rp_juta_missing_rows": rp_missing_count,
                    "investasi_rp_juta_sum": "" if rp_sum is None else decimal_text(rp_sum),
                    "investasi_us_ribu_complete": str(usd_complete).lower(),
                    "investasi_us_ribu_missing_rows": usd_missing_count,
                    "investasi_us_ribu_sum": "" if usd_sum is None else decimal_text(usd_sum),
                    "raw_evidence_path": rel(raw_path),
                    "raw_evidence_sha256": sha256_bytes(body),
                })
                emitted_count += 1

        pilot_results.append({
            "year": year,
            "quarter": quarter,
            "pilot_role": pilot["role"],
            "dataset_identifier": binding_row["dataset_identifier"],
            "request_url": url,
            "status": status,
            "content_type": content_type,
            "expected_sumbar_search_count": expected_count,
            "response_records_total": records_total,
            "response_records_filtered": records_filtered,
            "response_data_row_count": len(data),
            "raw_evidence_path": rel(raw_path),
            "raw_evidence_sha256": sha256_bytes(body),
            "raw_evidence_bytes": len(body),
            "observed_source_period_values": sorted(source_periods),
            "observed_source_status_values": sorted(source_statuses),
            "observed_source_geography_labels": sorted(source_labels),
            "mapped_geography_ids": sorted(mapped_geographies),
            "mapped_geography_count": len(mapped_geographies),
            "false_positive_province_row_count": false_positive_province_count,
            "period_mismatch_row_count": period_mismatch_count,
            "unexpected_status_row_count": invalid_status_count,
            "unmapped_geography_labels": sorted(unmapped_labels),
            "duplicate_source_dimension_tuple_count": duplicate_dimension_count,
            "negative_metric_row_counts": negative_metric_counts,
            "qualified": qualified,
            "fail_reasons": sorted(set(fail_reasons)),
            "emitted_geography_status_observation_count": emitted_count,
        })

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "year", "quarter", "geography_id", "canonical_name", "status_penanaman_modal",
        "observed_source_row_count", "investasi_rp_juta_complete", "investasi_rp_juta_missing_rows",
        "investasi_rp_juta_sum", "investasi_us_ribu_complete", "investasi_us_ribu_missing_rows",
        "investasi_us_ribu_sum", "raw_evidence_path", "raw_evidence_sha256",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in sorted(all_output_rows, key=lambda r: (r["year"], {"I":1,"II":2,"III":3,"IV":4}[r["quarter"]], r["geography_id"], r["status_penanaman_modal"])):
            writer.writerow(row)

    pilot_success = all(r["qualified"] for r in pilot_results) and len(all_output_rows) > 0
    manifest = {
        "schema": "ranah-observatory/milestone27-bkpm-stage1-pilot/v1",
        "milestone": 27,
        "stage": "stage1_numeric_pilot",
        "pilot_count": len(pilot_results),
        "pilot_results": pilot_results,
        "pilot_success": pilot_success,
        "materialized_geography_status_observation_count": len(all_output_rows),
        "target_investment_values_retrieved": True,
        "target_investment_values_inspected": True,
        "raw_filtered_response_persisted": True,
        "within_quarter_within_status_within_geography_addition_performed": pilot_success,
        "missing_values_coerced_to_zero": False,
        "absent_geography_status_groups_materialized_as_zero": False,
        "pma_pmdn_combination_performed": False,
        "cross_quarter_addition_performed": False,
        "annual_sum_performed": False,
        "q4_interpreted_as_annual_total": False,
        "external_fx_conversion_performed": False,
        "per_capita_normalization_performed": False,
        "ranking_created": False,
        "statistical_model_fit": False,
        "causal_claim_created": False,
        "monetary_wasted_potential_estimated": False,
        "output_csv": {"path": rel(OUT_CSV), "sha256": sha256_path(OUT_CSV)},
        "contract": {"path": rel(CONTRACT), "sha256": sha256_path(CONTRACT)},
        "schema_prerequisite": {"path": rel(SCHEMA), "sha256": sha256_path(SCHEMA)},
        "search_prerequisite": {"path": rel(SEARCH), "sha256": sha256_path(SEARCH)},
        "binding_prerequisite": {"path": rel(BINDING), "sha256": sha256_path(BINDING)},
        "geography_contract": {"path": rel(GEO_CONTRACT), "sha256": sha256_path(GEO_CONTRACT)},
        "canonical_geography_registry": {"path": rel(CANONICAL_GEO), "sha256": sha256_path(CANONICAL_GEO)},
    }
    write_json(OUT_MANIFEST, manifest)
    print(json.dumps({
        "pilot_success": pilot_success,
        "pilot_qualified": {f"{r['year']}-{r['quarter']}": r['qualified'] for r in pilot_results},
        "fail_reasons": {f"{r['year']}-{r['quarter']}": r['fail_reasons'] for r in pilot_results},
        "mapped_geography_counts": {f"{r['year']}-{r['quarter']}": r['mapped_geography_count'] for r in pilot_results},
        "observations": len(all_output_rows),
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError, PilotError) as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
