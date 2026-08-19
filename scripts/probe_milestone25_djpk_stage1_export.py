#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

from milestone25_djpk_html_compat import install_djpk_html_compat

install_djpk_html_compat()

import probe_milestone25_djpk_stage1 as stage1
from milestone25_djpk_export import (
    M25DJPKExportError,
    build_export_url,
    exact_account_map,
    find_same_selector_export_url,
    html_display_matches_exact,
    parse_exact_rupiah,
    rupiah_to_idr_billion,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CROSSWALK = ROOT / "data/registries/djpk_sumbar_pemda.csv"
DEFAULT_CONTRACTS = ROOT / "data/registries/djpk_m25_stage1_account_contracts.csv"
DEFAULT_CONTRACT_MANIFEST = ROOT / "data/manifests/milestone25_stage1_contracts.json"
DEFAULT_TRANSPORT = ROOT / "data/manifests/milestone25_transport_amendment.json"
DEFAULT_COVERAGE = ROOT / "data/analysis/engine/djpk_finance_v1/m25-stage1-full-coverage.csv"
DEFAULT_VALUES = ROOT / "data/analysis/engine/djpk_finance_v1/m25-stage1-full-values.csv"
DEFAULT_MANIFEST = ROOT / "data/manifests/milestone25_stage1_full_export.json"
DEFAULT_RAW_DIR = ROOT / "data/processed/djpk/public_finance/source"
YEARS = list(range(2018, 2026))


class M25Stage1ExportError(RuntimeError):
    pass


def write_csv(path: Path, fields: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def sha256_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def fetch_export(url: str, *, timeout: float = 45.0, retries: int = 3) -> tuple[int, str, str, bytes]:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "ranah-observatory/0.1 (+https://github.com/nabilrn/ranah-observatory)",
                    "Accept": "application/vnd.ms-excel,application/xml,text/xml,*/*",
                },
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return (
                    int(response.status),
                    str(response.geturl()),
                    str(response.headers.get("Content-Type", "")),
                    response.read(),
                )
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt >= retries:
                break
            time.sleep(1.0 * (2**attempt))
    raise M25Stage1ExportError(f"DJPK export request failed: {url}") from last_error


def load_transport(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "ranah-observatory/milestone25-transport-amendment/v1":
        raise M25Stage1ExportError("unexpected M25 transport amendment schema")
    required_false = (
        "scientific_design_changed",
        "account_family_set_changed",
        "target_years_changed",
        "geography_set_changed",
        "period_selector_changed",
        "province_selector_changed",
        "posthoc_account_family_search_performed",
        "explicit_taxonomy_bridge_promoted",
        "derived_ratio_authorized",
        "statistical_model_fit_authorized",
        "causal_claim_authorized",
        "imputation_performed",
        "historical_boundary_reconstruction_performed",
        "user_contribution_required",
    )
    if any(payload.get(key) is not False for key in required_false):
        raise M25Stage1ExportError("M25 transport amendment changed a locked scientific boundary")
    if payload.get("representation_amendment_after_transport_failure") is not True:
        raise M25Stage1ExportError("M25 transport amendment is not explicitly representation-only")
    if payload.get("html_export_selector_match_required") is not True:
        raise M25Stage1ExportError("same-selector HTML export link is not required")
    if payload.get("html_table_value_crosscheck_required_when_parseable") is not True:
        raise M25Stage1ExportError("HTML value cross-check is not required when parseable")
    return payload


def parse_optional_html_accounts(body: bytes) -> tuple[bool, dict[str, dict[str, str]]]:
    parser = stage1.HTMLTableParser()
    parser.feed(body.decode("utf-8", errors="replace"))
    try:
        header, rows = stage1.find_postur_table(parser.tables)
        accounts = stage1.table_to_accounts(header, rows)
    except ValueError:
        return False, {}
    by_label = {row["account_label_normalized"]: row for row in accounts}
    if len(by_label) != len(accounts):
        raise M25Stage1ExportError("HTML duplicate-resolution keys remain ambiguous")
    return True, by_label


def run_probe(
    *,
    years: list[int],
    crosswalk_path: Path,
    contracts_path: Path,
    contract_manifest_path: Path,
    transport_path: Path,
    coverage_path: Path,
    values_path: Path,
    manifest_path: Path,
    raw_dir: Path,
) -> dict[str, Any]:
    transport = load_transport(transport_path)
    crosswalk = stage1.validate_crosswalk(crosswalk_path)
    contracts = stage1.load_promoted_contracts(contracts_path, contract_manifest_path)
    expected_families = list(transport["locked_promoted_exact_label_families"])
    if [row["conceptual_family"] for row in contracts] != expected_families:
        raise M25Stage1ExportError("locked promoted account families drifted after transport amendment")
    if years != sorted(set(years)) or any(year not in YEARS for year in years):
        raise M25Stage1ExportError("M25 Stage 1 export years are outside the locked 2018-2025 regime")

    raw_dir.mkdir(parents=True, exist_ok=True)
    coverage_rows: list[dict[str, Any]] = []
    value_rows: list[dict[str, Any]] = []
    raw_responses: list[dict[str, Any]] = []

    for geography in crosswalk:
        pemda = geography["djpk_pemda_selector"]
        for year in years:
            requested_html_url = stage1.build_url(pemda, year)
            html_status, html_body, final_html_url = stage1.fetch_url(requested_html_url)
            if html_status != 200:
                raise M25Stage1ExportError(f"DJPK HTML HTTP {html_status} for {pemda}/{year}")
            html_path = raw_dir / f"pemda-{pemda}-{year}-desember.html"
            html_path.write_bytes(html_body)
            html_sha = sha256_bytes(html_body)

            parser = stage1.HTMLTableParser()
            parser.feed(html_body.decode("utf-8", errors="replace"))
            page_text = parser.all_text
            jurisdiction_ok = stage1.jurisdiction_matches(page_text, geography["djpk_source_name"])
            year_ok = str(year) in page_text
            december_ok = bool(
                re.search(r"realisasi\s+apbd\s+s\.?\s*d\.?\s+desember", page_text, flags=re.IGNORECASE)
            )

            try:
                linked_export_url = find_same_selector_export_url(html_body, pemda, year)
                expected_export_url = build_export_url(pemda, year)
                export_link_ok = linked_export_url == expected_export_url
            except M25DJPKExportError:
                linked_export_url = ""
                expected_export_url = build_export_url(pemda, year)
                export_link_ok = False

            export_status = 0
            final_export_url = ""
            export_content_type = ""
            export_body = b""
            export_sha = ""
            export_valid = False
            export_accounts: dict[str, dict[str, str]] = {}
            if export_link_ok:
                export_status, final_export_url, export_content_type, export_body = fetch_export(linked_export_url)
                export_sha = sha256_bytes(export_body)
                xml_path = raw_dir / f"pemda-{pemda}-{year}-desember.xml"
                xml_path.write_bytes(export_body)
                try:
                    export_accounts = exact_account_map(export_body)
                    export_valid = export_status == 200
                except M25DJPKExportError:
                    export_valid = False
            else:
                xml_path = raw_dir / f"pemda-{pemda}-{year}-desember.xml"

            html_table_parseable = False
            html_accounts: dict[str, dict[str, str]] = {}
            html_table_error = ""
            try:
                html_table_parseable, html_accounts = parse_optional_html_accounts(html_body)
                if not html_table_parseable:
                    html_table_error = "postur_table_not_parseable"
            except (ValueError, M25Stage1ExportError) as exc:
                html_table_error = f"{type(exc).__name__}:{exc}"

            missing_contracts: list[str] = []
            parse_failures: list[str] = []
            html_crosscheck_failures: list[str] = []
            matched_contracts = 0
            page_values: list[dict[str, Any]] = []

            for contract in contracts:
                family = contract["conceptual_family"]
                label = contract["locked_source_label_normalized"]
                source_row = export_accounts.get(label)
                if source_row is None:
                    missing_contracts.append(family)
                    continue
                try:
                    budget_rupiah = parse_exact_rupiah(source_row["budget_rupiah_raw"])
                    realization_rupiah = parse_exact_rupiah(source_row["realization_rupiah_raw"])
                    realization_billion = rupiah_to_idr_billion(realization_rupiah)
                except M25DJPKExportError:
                    parse_failures.append(family)
                    continue

                html_crosscheck_status = "not_available_html_table_unparseable"
                html_display_raw = ""
                if html_table_parseable:
                    html_row = html_accounts.get(label)
                    if html_row is None:
                        html_crosscheck_status = "failed_locked_label_missing_in_html_table"
                        html_crosscheck_failures.append(family)
                    else:
                        html_display_raw = html_row["realization_raw"]
                        try:
                            html_display_billion = stage1.parse_djpk_money_to_idr_billion(html_display_raw)
                            if html_display_matches_exact(html_display_billion, realization_rupiah):
                                html_crosscheck_status = "passed_display_rounding_crosscheck"
                            else:
                                html_crosscheck_status = "failed_display_rounding_crosscheck"
                                html_crosscheck_failures.append(family)
                        except stage1.M25Stage1Error:
                            html_crosscheck_status = "failed_html_display_parse"
                            html_crosscheck_failures.append(family)

                matched_contracts += 1
                page_values.append(
                    {
                        "geography_id": geography["geography_id"],
                        "canonical_name": geography["canonical_name"],
                        "djpk_province_selector": geography["djpk_province_selector"],
                        "djpk_pemda_selector": pemda,
                        "djpk_source_name": geography["djpk_source_name"],
                        "year": year,
                        "period_selector": stage1.PERIOD_SELECTOR,
                        "conceptual_family": family,
                        "source_account_label": source_row["account_label"],
                        "source_account_label_normalized": source_row["account_label_normalized"],
                        "budget_rupiah_raw": source_row["budget_rupiah_raw"],
                        "realization_rupiah_raw": source_row["realization_rupiah_raw"],
                        "realization_idr_billion": format(realization_billion, "f"),
                        "percentage_raw": source_row["percentage_raw"],
                        "html_display_realization_raw": html_display_raw,
                        "html_crosscheck_status": html_crosscheck_status,
                        "taxonomy_contract_type": "exact_label",
                        "claim_type": "observed_recorded_fiscal_realization",
                        "html_response_sha256": html_sha,
                        "export_response_sha256": export_sha,
                    }
                )

            page_pass = (
                jurisdiction_ok
                and year_ok
                and december_ok
                and export_link_ok
                and export_valid
                and not missing_contracts
                and not parse_failures
                and not html_crosscheck_failures
                and matched_contracts == len(contracts)
            )

            coverage_rows.append(
                {
                    "geography_id": geography["geography_id"],
                    "canonical_name": geography["canonical_name"],
                    "djpk_pemda_selector": pemda,
                    "year": year,
                    "requested_html_url": requested_html_url,
                    "final_html_url": final_html_url,
                    "html_http_status": html_status,
                    "jurisdiction_match": jurisdiction_ok,
                    "fiscal_year_match": year_ok,
                    "december_realization_semantics_match": december_ok,
                    "same_selector_export_link_match": export_link_ok,
                    "export_url": linked_export_url,
                    "expected_export_url": expected_export_url,
                    "final_export_url": final_export_url,
                    "export_http_status": export_status,
                    "export_content_type": export_content_type,
                    "export_valid_spreadsheetml": export_valid,
                    "html_table_parseable": html_table_parseable,
                    "html_table_error": html_table_error,
                    "html_value_crosscheck_failure_count": len(html_crosscheck_failures),
                    "html_value_crosscheck_failures": "|".join(html_crosscheck_failures),
                    "locked_contract_count": len(contracts),
                    "matched_contract_count": matched_contracts,
                    "missing_contracts": "|".join(missing_contracts),
                    "parse_failures": "|".join(parse_failures),
                    "html_response_sha256": html_sha,
                    "export_response_sha256": export_sha,
                    "page_pass": page_pass,
                }
            )
            value_rows.extend(page_values)
            raw_responses.append(
                {
                    "geography_id": geography["geography_id"],
                    "djpk_pemda_selector": pemda,
                    "year": year,
                    "html_path": html_path.as_posix(),
                    "html_sha256": html_sha,
                    "export_path": xml_path.as_posix(),
                    "export_sha256": export_sha,
                }
            )

    expected_pages = 19 * len(years)
    if len(coverage_rows) != expected_pages:
        raise M25Stage1ExportError(f"expected {expected_pages} jurisdiction-year rows, got {len(coverage_rows)}")
    failures = [
        f"{row['djpk_pemda_selector']}/{row['year']}"
        for row in coverage_rows
        if not bool(row["page_pass"])
    ]
    if failures:
        # Write diagnostic evidence before failing so a temporary writer or
        # artifact workflow can inspect exactly which locked gate failed.
        write_csv(coverage_path, list(coverage_rows[0].keys()), coverage_rows)
        if value_rows:
            write_csv(values_path, list(value_rows[0].keys()), value_rows)
        raise M25Stage1ExportError(f"M25 dual-representation page qualification failures: {failures}")

    expected_values = expected_pages * len(contracts)
    if len(value_rows) != expected_values:
        raise M25Stage1ExportError(f"expected {expected_values} exact fiscal values, got {len(value_rows)}")

    write_csv(coverage_path, list(coverage_rows[0].keys()), coverage_rows)
    write_csv(values_path, list(value_rows[0].keys()), value_rows)
    manifest = {
        "schema": "ranah-observatory/milestone25-stage1-dual-representation/v1",
        "milestone": 25,
        "stage": 1,
        "phase": "post_phase2_fiscal_evidence_expansion",
        "years": years,
        "geography_count": 19,
        "jurisdiction_year_page_count": expected_pages,
        "promoted_exact_label_family_count": len(contracts),
        "promoted_exact_label_families": [row["conceptual_family"] for row in contracts],
        "value_row_count": len(value_rows),
        "all_pages_pass": True,
        "html_snapshot_count": expected_pages,
        "spreadsheetml_snapshot_count": expected_pages,
        "html_table_parseable_page_count": sum(bool(row["html_table_parseable"]) for row in coverage_rows),
        "html_table_unparseable_page_count": sum(not bool(row["html_table_parseable"]) for row in coverage_rows),
        "same_selector_export_link_required": True,
        "spreadsheetml_is_primary_numeric_evidence": True,
        "html_is_identity_period_and_optional_crosscheck_evidence": True,
        "cross_geography_probe_completed_after_contract_lock": True,
        "explicit_bridge_used": False,
        "derived_ratio_created": False,
        "imputation_performed": False,
        "posthoc_account_family_search_performed": False,
        "statistical_model_fit": False,
        "raw_responses": raw_responses,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze M25 DJPK HTML semantics plus same-selector SpreadsheetML exact values.")
    parser.add_argument("--years", type=int, nargs="+", default=YEARS)
    parser.add_argument("--crosswalk", type=Path, default=DEFAULT_CROSSWALK)
    parser.add_argument("--contracts", type=Path, default=DEFAULT_CONTRACTS)
    parser.add_argument("--contract-manifest", type=Path, default=DEFAULT_CONTRACT_MANIFEST)
    parser.add_argument("--transport", type=Path, default=DEFAULT_TRANSPORT)
    parser.add_argument("--coverage", type=Path, default=DEFAULT_COVERAGE)
    parser.add_argument("--values", type=Path, default=DEFAULT_VALUES)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    args = parser.parse_args()
    try:
        years = sorted(set(args.years))
        result = run_probe(
            years=years,
            crosswalk_path=args.crosswalk,
            contracts_path=args.contracts,
            contract_manifest_path=args.contract_manifest,
            transport_path=args.transport,
            coverage_path=args.coverage,
            values_path=args.values,
            manifest_path=args.manifest,
            raw_dir=args.raw_dir,
        )
    except (OSError, json.JSONDecodeError, ValueError, stage1.M25Stage1Error, M25DJPKExportError, M25Stage1ExportError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "jurisdiction_year_page_count": result["jurisdiction_year_page_count"],
        "value_row_count": result["value_row_count"],
        "html_table_parseable_page_count": result["html_table_parseable_page_count"],
        "html_table_unparseable_page_count": result["html_table_unparseable_page_count"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
