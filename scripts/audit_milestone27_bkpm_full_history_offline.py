#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import io
import json
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from scripts.materialize_milestone27_bkpm_full_history import (
    QNUM,
    decimal_text,
    load_geography_map,
    normalize_source_geography,
    normalize_text,
    parse_decimal,
    quarter_matches,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "data/manifests/milestone27_stage1_full_history_contract.json"
SCHEMA = ROOT / "data/manifests/milestone27_bkpm_public_data_zero_row_probe.json"
LIVE_MANIFEST = ROOT / "data/manifests/milestone27_bkpm_full_history.json"
QUALIFICATION = ROOT / "data/manifests/milestone27_bkpm_stage1_qualification.json"
DUP_DIAG = ROOT / "data/manifests/milestone27_bkpm_2024q1_duplicate_diagnostic.json"
OUT_CSV = ROOT / "data/analysis/engine/investment_realization_v1/m27-bkpm-quarterly-history.csv"
OUT_AUDIT = ROOT / "data/analysis/engine/investment_realization_v1/m27-bkpm-quarter-audit.csv"
OUT_MANIFEST = ROOT / "data/manifests/milestone27_bkpm_offline_reproducibility.json"


class OfflineError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_bytes(fieldnames: list[str], rows: list[dict[str, Any]]) -> bytes:
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


def main() -> int:
    contract = load_json(CONTRACT)
    schema = load_json(SCHEMA)
    live = load_json(LIVE_MANIFEST)
    qualification = load_json(QUALIFICATION)
    dup_diag = load_json(DUP_DIAG)

    if contract.get("schema") != "ranah-observatory/milestone27-stage1-full-history-contract/v1":
        raise OfflineError("unexpected acquisition contract")
    if live.get("quarter_count") != 64 or live.get("qualified_quarter_count") != 63 or live.get("failed_quarter_count") != 1:
        raise OfflineError("unexpected live full-history state")
    if qualification.get("bounded_quarterly_history_qualified") is not True:
        raise OfflineError("bounded Stage 1 qualification missing")
    if qualification.get("continuous_64_quarter_history_qualified") is not False:
        raise OfflineError("continuous history unexpectedly qualified")
    if dup_diag.get("classification") != "mixed_duplicate_mechanisms":
        raise OfflineError("2024-Q1 diagnostic state changed")

    expected_columns = list(schema["qualified_declared_columns"])
    source_dimensions = list(contract["source_dimensions"])
    geo_map = load_geography_map()
    output_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    rebuilt_quarters: list[dict[str, Any]] = []

    for qr in live["quarter_results"]:
        year = int(qr["year"])
        quarter = str(qr["quarter"])
        count = int(qr["sumbar_source_row_count"] or 0)
        raw_pages = list(qr["raw_pages"])
        if not raw_pages:
            raise OfflineError(f"no frozen pages for {year}-{quarter}")

        count_path = ROOT / raw_pages[0]["path"]
        if sha256_path(count_path) != raw_pages[0]["sha256"]:
            raise OfflineError(f"count page checksum mismatch {year}-{quarter}")
        count_payload = load_json(count_path)
        if count_payload.get("data") != [] or count_payload.get("columns") != expected_columns:
            raise OfflineError(f"count/schema evidence mismatch {year}-{quarter}")
        if int(count_payload.get("recordsFiltered")) != count or int(count_payload.get("recordsTotal")) != count:
            raise OfflineError(f"count evidence changed {year}-{quarter}")

        data: list[Any] = []
        for page_meta in raw_pages[1:]:
            p = ROOT / page_meta["path"]
            if sha256_path(p) != page_meta["sha256"]:
                raise OfflineError(f"page checksum mismatch {page_meta['path']}")
            payload = load_json(p)
            if payload.get("columns") != expected_columns:
                raise OfflineError(f"page schema mismatch {page_meta['path']}")
            if int(payload.get("recordsFiltered")) != count or int(payload.get("recordsTotal")) != count:
                raise OfflineError(f"page count mismatch {page_meta['path']}")
            page_data = payload.get("data")
            if not isinstance(page_data, list):
                raise OfflineError(f"page data invalid {page_meta['path']}")
            data.extend(page_data)
        if len(data) != count:
            raise OfflineError(f"offline reconstructed count mismatch {year}-{quarter}: {len(data)} != {count}")

        fail: list[str] = []
        false_positive = 0
        period_mismatch = 0
        invalid_status = 0
        unmapped: set[str] = set()
        mapped_geographies: set[str] = set()
        dimension_seen: set[tuple[str, ...]] = set()
        duplicate_count = 0
        records: list[dict[str, Any]] = []

        for idx, row in enumerate(data):
            if not isinstance(row, dict) or set(row.keys()) != set(expected_columns):
                fail.append(f"row_schema_mismatch_{idx}")
                continue
            if normalize_text(row.get("provinsi")) != contract["accepted_province_normalized"]:
                false_positive += 1
                continue
            if not quarter_matches(row.get("periode"), year, quarter):
                period_mismatch += 1
                continue
            status = str(row.get("status_penanaman_modal", "")).strip().upper()
            if status not in contract["accepted_status_penanaman_modal"]:
                invalid_status += 1
                continue
            source_type, source_name = normalize_source_geography(row.get("kabupaten_kota"))
            mapped = geo_map.get((source_type or "", source_name)) if source_type else None
            if mapped is None:
                unmapped.add(str(row.get("kabupaten_kota", "")))
                continue
            mapped_geographies.add(mapped["geography_id"])
            dim = tuple("" if row.get(f) is None else str(row.get(f)) for f in source_dimensions)
            if dim in dimension_seen:
                duplicate_count += 1
            else:
                dimension_seen.add(dim)
            rp, rp_missing = parse_decimal(row.get("investasi_rp_juta"))
            usd, usd_missing = parse_decimal(row.get("investasi_us_ribu"))
            records.append({
                "geography_id": mapped["geography_id"],
                "canonical_name": mapped["canonical_name"],
                "status_penanaman_modal": status,
                "rp": rp,
                "rp_missing": rp_missing,
                "usd": usd,
                "usd_missing": usd_missing,
            })

        if false_positive:
            fail.append("global_search_returned_non_sumbar_rows")
        if period_mismatch:
            fail.append("row_period_mismatch")
        if invalid_status:
            fail.append("unexpected_status_penanaman_modal")
        if unmapped:
            fail.append("unmapped_kabupaten_kota")
        if duplicate_count:
            fail.append("duplicate_complete_source_dimension_tuple")

        is_held = (year, quarter) == (2024, "I")
        if is_held:
            if sorted(set(fail)) != ["duplicate_complete_source_dimension_tuple"]:
                raise OfflineError(f"2024-Q1 failure changed: {fail}")
            qualified = False
        else:
            if fail:
                raise OfflineError(f"qualified quarter no longer rebuilds cleanly {year}-{quarter}: {fail}")
            qualified = True

        emitted = 0
        if qualified and count > 0:
            grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
            for r in records:
                grouped[(r["geography_id"], r["status_penanaman_modal"])].append(r)
            for (geo_id, status), grp in sorted(grouped.items()):
                rp_missing = sum(1 for r in grp if r["rp_missing"])
                usd_missing = sum(1 for r in grp if r["usd_missing"])
                rp_complete = rp_missing == 0
                usd_complete = usd_missing == 0
                rp_sum = sum((r["rp"] for r in grp if r["rp"] is not None), Decimal(0)) if rp_complete else None
                usd_sum = sum((r["usd"] for r in grp if r["usd"] is not None), Decimal(0)) if usd_complete else None
                output_rows.append({
                    "year": year,
                    "quarter": quarter,
                    "geography_id": geo_id,
                    "canonical_name": grp[0]["canonical_name"],
                    "status_penanaman_modal": status,
                    "observed_source_row_count": len(grp),
                    "investasi_rp_juta_complete": str(rp_complete).lower(),
                    "investasi_rp_juta_missing_rows": rp_missing,
                    "investasi_rp_juta_sum": "" if rp_sum is None else decimal_text(rp_sum),
                    "investasi_us_ribu_complete": str(usd_complete).lower(),
                    "investasi_us_ribu_missing_rows": usd_missing,
                    "investasi_us_ribu_sum": "" if usd_sum is None else decimal_text(usd_sum),
                })
                emitted += 1

        classification = "held_failed_validation" if is_held else ("no_observed_sumbar_rows" if count == 0 else "qualified_numeric_quarter")
        fail_unique = sorted(set(fail))
        audit_rows.append({
            "year": year,
            "quarter": quarter,
            "sumbar_source_row_count": count,
            "reconstructed_source_row_count": len(data),
            "mapped_geography_count": len(mapped_geographies),
            "emitted_geography_status_observation_count": emitted,
            "classification": classification,
            "qualified": qualified,
            "fail_reasons": "|".join(fail_unique),
        })
        rebuilt_quarters.append({
            "year": year,
            "quarter": quarter,
            "source_rows": count,
            "mapped_geography_count": len(mapped_geographies),
            "duplicate_dimension_row_count_after_first": duplicate_count,
            "qualified": qualified,
            "classification": classification,
            "fail_reasons": fail_unique,
        })

    output_rows = sorted(output_rows, key=lambda r: (r["year"], QNUM[r["quarter"]], r["geography_id"], r["status_penanaman_modal"]))
    out_fields = ["year","quarter","geography_id","canonical_name","status_penanaman_modal","observed_source_row_count","investasi_rp_juta_complete","investasi_rp_juta_missing_rows","investasi_rp_juta_sum","investasi_us_ribu_complete","investasi_us_ribu_missing_rows","investasi_us_ribu_sum"]
    audit_fields = ["year","quarter","sumbar_source_row_count","reconstructed_source_row_count","mapped_geography_count","emitted_geography_status_observation_count","classification","qualified","fail_reasons"]
    rebuilt_out = csv_bytes(out_fields, output_rows)
    rebuilt_audit = csv_bytes(audit_fields, audit_rows)
    committed_out = OUT_CSV.read_bytes()
    committed_audit = OUT_AUDIT.read_bytes()

    if rebuilt_out != committed_out:
        raise OfflineError("quarterly output is not byte-identical to offline rebuild")
    if rebuilt_audit != committed_audit:
        raise OfflineError("quarter audit is not byte-identical to offline rebuild")
    if len(output_rows) != 1440:
        raise OfflineError(f"unexpected rebuilt observation count: {len(output_rows)}")

    manifest = {
        "schema": "ranah-observatory/milestone27-bkpm-offline-reproducibility/v1",
        "milestone": 27,
        "stage": "stage1_bounded_history_offline_rebuild",
        "offline_only": True,
        "network_requests_performed": False,
        "quarter_count": len(rebuilt_quarters),
        "qualified_quarter_count": sum(1 for r in rebuilt_quarters if r["qualified"]),
        "held_quarter_count": sum(1 for r in rebuilt_quarters if not r["qualified"]),
        "materialized_observation_count": len(output_rows),
        "quarterly_output_byte_identical": True,
        "quarter_audit_byte_identical": True,
        "quarterly_output_sha256": sha256_bytes(rebuilt_out),
        "quarter_audit_sha256": sha256_bytes(rebuilt_audit),
        "rebuild_success": True,
        "held_quarters": [r for r in rebuilt_quarters if not r["qualified"]],
        "missing_values_coerced_to_zero": False,
        "pma_pmdn_combination_performed": False,
        "cross_quarter_addition_performed": False,
        "annual_sum_performed": False,
        "external_fx_conversion_performed": False,
        "statistical_model_fit": False,
        "causal_claim_created": False,
        "monetary_wasted_potential_estimated": False,
        "live_manifest_sha256": sha256_path(LIVE_MANIFEST),
        "qualification_sha256": sha256_path(QUALIFICATION),
        "duplicate_diagnostic_sha256": sha256_path(DUP_DIAG),
    }
    OUT_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "rebuild_success": True,
        "qualified_quarters": manifest["qualified_quarter_count"],
        "held_quarters": manifest["held_quarter_count"],
        "observations": len(output_rows),
        "output_sha256": manifest["quarterly_output_sha256"],
        "audit_sha256": manifest["quarter_audit_sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError, OfflineError) as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
