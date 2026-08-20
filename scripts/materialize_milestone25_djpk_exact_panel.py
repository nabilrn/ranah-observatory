#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

from milestone25_djpk_html_compat import install_djpk_html_compat

install_djpk_html_compat()

import probe_milestone25_djpk_stage1 as stage1
from milestone25_djpk_period_semantics import classify_annual_final_realization
from milestone25_djpk_export import (
    M25DJPKExportError,
    exact_account_map,
    find_same_selector_export_url,
    html_display_matches_exact,
    parse_exact_rupiah,
    rupiah_to_idr_billion,
)

ROOT = Path(__file__).resolve().parents[1]
CROSSWALK = ROOT / "data/registries/djpk_sumbar_pemda.csv"
CONTRACTS = ROOT / "data/registries/djpk_m25_stage1_account_contracts.csv"
CONTRACT_MANIFEST = ROOT / "data/manifests/milestone25_stage1_contracts.json"
TRANSPORT = ROOT / "data/manifests/milestone25_transport_amendment.json"
COVERAGE = ROOT / "data/analysis/engine/djpk_finance_v1/m25-stage1-full-coverage.csv"
PROBE_VALUES = ROOT / "data/analysis/engine/djpk_finance_v1/m25-stage1-full-values.csv"
STAGE1_MANIFEST = ROOT / "data/manifests/milestone25_stage1_full_export.json"
RAW_ROOT = ROOT / "data/processed/djpk/public_finance/source"
OUT_DIR = ROOT / "data/processed/djpk/public_finance"
OBS_OUT = OUT_DIR / "djpk-fiscal-canonical-observations.csv"
PROV_OUT = OUT_DIR / "djpk-fiscal-provenance.csv"
MANIFEST_OUT = OUT_DIR / "djpk-fiscal-panel.manifest.json"

YEARS = list(range(2018, 2026))
REGIME_ID = "sumbar_current_kabkota_djpk_realization_2018_2025_v2"


class M25MaterializationError(RuntimeError):
    pass


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def write_csv(path: Path, fields: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_id(prefix: str, *parts: object) -> str:
    payload = "\x1f".join(str(part) for part in parts).encode("utf-8")
    return prefix + hashlib.sha256(payload).hexdigest()[:24]


def load_contracts() -> list[dict[str, str]]:
    manifest = json.loads(CONTRACT_MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("schema") != "ranah-observatory/milestone25-stage1-account-contracts/v1":
        raise M25MaterializationError("unexpected Stage1 contract manifest")
    if manifest.get("contracts_locked") is not True:
        raise M25MaterializationError("Stage1 contracts not locked")
    if manifest.get("cross_geography_values_inspected_before_lock") is not False:
        raise M25MaterializationError("contracts were not locked before cross-geography extraction")
    rows = read_csv(CONTRACTS)
    promoted = [row for row in rows if row["stage1_promotion_status"] == "promoted_exact_label"]
    if not promoted:
        raise M25MaterializationError("no exact-label contracts promoted")
    if len(promoted) != manifest.get("promoted_exact_label_family_count"):
        raise M25MaterializationError("promoted contract cardinality drift")
    for row in promoted:
        if row["taxonomy_contract_type"] != "exact_label" or not row["locked_source_label_normalized"]:
            raise M25MaterializationError("non-exact contract reached exact-panel materializer")
    return promoted


def validate_crosswalk() -> list[dict[str, str]]:
    rows = read_csv(CROSSWALK)
    if len(rows) != 19 or len({row["geography_id"] for row in rows}) != 19:
        raise M25MaterializationError("DJPK crosswalk footprint drift")
    if {row["djpk_pemda_selector"] for row in rows} != {f"{value:02d}" for value in range(1, 20)}:
        raise M25MaterializationError("DJPK selector set drift")
    return sorted(rows, key=lambda row: int(row["djpk_pemda_selector"]))


def optional_html_accounts(body: bytes) -> tuple[bool, dict[str, dict[str, str]]]:
    parser = stage1.HTMLTableParser()
    parser.feed(body.decode("utf-8", errors="replace"))
    try:
        header, source_rows = stage1.find_postur_table(parser.tables)
        accounts = stage1.table_to_accounts(header, source_rows)
    except ValueError:
        return False, {}
    by_label = {row["account_label_normalized"]: row for row in accounts}
    if len(by_label) != len(accounts):
        raise M25MaterializationError("ambiguous HTML account keys after duplicate resolution")
    return True, by_label


def verify_html_semantics(
    *, body: bytes, geography: dict[str, str], year: int, pemda: str
) -> tuple[str, str, bool, dict[str, dict[str, str]]]:
    parser = stage1.HTMLTableParser()
    parser.feed(body.decode("utf-8", errors="replace"))
    page_text = parser.all_text
    if not stage1.jurisdiction_matches(page_text, geography["djpk_source_name"]):
        raise M25MaterializationError(f"frozen HTML jurisdiction identity failed {pemda}/{year}")
    if str(year) not in page_text:
        raise M25MaterializationError(f"frozen HTML year identity failed {pemda}/{year}")
    annual_semantics_class = classify_annual_final_realization(page_text, year)
    if annual_semantics_class is None:
        raise M25MaterializationError(f"frozen HTML annual-final semantics failed {pemda}/{year}")
    try:
        linked_export = find_same_selector_export_url(body, pemda, year)
    except M25DJPKExportError as exc:
        raise M25MaterializationError(f"frozen HTML same-selector export link failed {pemda}/{year}") from exc
    parseable, html_accounts = optional_html_accounts(body)
    return linked_export, annual_semantics_class, parseable, html_accounts


def materialize() -> dict[str, Any]:
    required = [CROSSWALK, CONTRACTS, CONTRACT_MANIFEST, TRANSPORT, COVERAGE, PROBE_VALUES, STAGE1_MANIFEST]
    for path in required:
        if not path.exists():
            raise M25MaterializationError(f"missing M25 materialization input {path}")

    transport = json.loads(TRANSPORT.read_text(encoding="utf-8"))
    if transport.get("schema") != "ranah-observatory/milestone25-transport-amendment/v1":
        raise M25MaterializationError("transport amendment schema drift")
    if transport.get("scientific_design_changed") is not False:
        raise M25MaterializationError("transport amendment changed scientific design")
    stage1_manifest = json.loads(STAGE1_MANIFEST.read_text(encoding="utf-8"))
    if stage1_manifest.get("schema") != "ranah-observatory/milestone25-stage1-dual-representation/v1":
        raise M25MaterializationError("unexpected dual-representation Stage1 manifest")
    if stage1_manifest.get("all_pages_pass") is not True:
        raise M25MaterializationError("dual-representation Stage1 did not pass all pages")

    contracts = load_contracts()
    crosswalk = validate_crosswalk()
    coverage = read_csv(COVERAGE)
    probe_values = read_csv(PROBE_VALUES)

    if len(coverage) != 152 or any(row["page_pass"] != "True" for row in coverage):
        raise M25MaterializationError("full dual-representation coverage is not 152/152 passing")
    coverage_by_key = {(row["geography_id"], int(row["year"])): row for row in coverage}
    if len(coverage_by_key) != 152:
        raise M25MaterializationError("duplicate full-probe coverage keys")

    expected_probe_values = 152 * len(contracts)
    if len(probe_values) != expected_probe_values:
        raise M25MaterializationError(
            f"probe value count drift: expected {expected_probe_values}, got {len(probe_values)}"
        )
    probe_value_by_key = {
        (row["geography_id"], int(row["year"]), row["conceptual_family"]): row
        for row in probe_values
    }
    if len(probe_value_by_key) != expected_probe_values:
        raise M25MaterializationError("duplicate Stage1 probe value keys")

    observations: list[dict[str, Any]] = []
    provenance: list[dict[str, Any]] = []
    html_parseable_count = 0
    html_unparseable_count = 0

    for geography in crosswalk:
        geography_id = geography["geography_id"]
        pemda = geography["djpk_pemda_selector"]
        for year in YEARS:
            coverage_row = coverage_by_key.get((geography_id, year))
            if coverage_row is None:
                raise M25MaterializationError(f"missing coverage {geography_id}/{year}")
            html_path = RAW_ROOT / f"pemda-{pemda}-{year}-desember.html"
            export_path = RAW_ROOT / f"pemda-{pemda}-{year}-desember.xml"
            for path in (html_path, export_path):
                if not path.exists():
                    raise M25MaterializationError(f"missing frozen DJPK source snapshot {path}")

            html_sha = sha256(html_path)
            export_sha = sha256(export_path)
            if html_sha != coverage_row["html_response_sha256"]:
                raise M25MaterializationError(f"DJPK HTML hash drift {geography_id}/{year}")
            if export_sha != coverage_row["export_response_sha256"]:
                raise M25MaterializationError(f"DJPK export hash drift {geography_id}/{year}")

            html_body = html_path.read_bytes()
            export_body = export_path.read_bytes()
            linked_export, annual_semantics_class, html_parseable, html_accounts = verify_html_semantics(
                body=html_body, geography=geography, year=year, pemda=pemda
            )
            if linked_export != coverage_row["export_url"]:
                raise M25MaterializationError(f"export-link provenance drift {geography_id}/{year}")
            if html_parseable:
                html_parseable_count += 1
            else:
                html_unparseable_count += 1

            try:
                export_accounts = exact_account_map(export_body)
            except M25DJPKExportError as exc:
                raise M25MaterializationError(f"frozen SpreadsheetML invalid {geography_id}/{year}") from exc

            provenance_id = stable_id("m25prov_", geography_id, year, html_sha, export_sha)
            provenance.append(
                {
                    "fiscal_provenance_id": provenance_id,
                    "geography_id": geography_id,
                    "canonical_name": geography["canonical_name"],
                    "djpk_province_selector": geography["djpk_province_selector"],
                    "djpk_pemda_selector": pemda,
                    "year": year,
                    "period_selector": "12",
                    "reference_period": "annual_final_realization",
                    "source_realization_semantics_class": annual_semantics_class,
                    "html_snapshot": html_path.relative_to(ROOT).as_posix(),
                    "html_snapshot_sha256": html_sha,
                    "html_source_url": coverage_row["final_html_url"],
                    "export_snapshot": export_path.relative_to(ROOT).as_posix(),
                    "export_snapshot_sha256": export_sha,
                    "export_source_url": coverage_row["export_url"],
                    "html_table_parseable": html_parseable,
                    "same_selector_export_link_verified": True,
                    "claim_type": "observed_recorded_fiscal_realization",
                    "comparability_regime": REGIME_ID,
                }
            )

            for contract in contracts:
                family = contract["conceptual_family"]
                label = contract["locked_source_label_normalized"]
                source = export_accounts.get(label)
                if source is None:
                    raise M25MaterializationError(f"locked export label missing {family} {geography_id}/{year}")
                budget_rupiah = parse_exact_rupiah(source["budget_rupiah_raw"])
                realization_rupiah = parse_exact_rupiah(source["realization_rupiah_raw"])
                amount = rupiah_to_idr_billion(realization_rupiah)

                probe_row = probe_value_by_key.get((geography_id, year, family))
                if probe_row is None:
                    raise M25MaterializationError(f"probe value missing {family} {geography_id}/{year}")
                if Decimal(probe_row["realization_rupiah_raw"]) != realization_rupiah:
                    raise M25MaterializationError(f"exact probe/export realization drift {family} {geography_id}/{year}")
                if Decimal(probe_row["budget_rupiah_raw"]) != budget_rupiah:
                    raise M25MaterializationError(f"exact probe/export budget drift {family} {geography_id}/{year}")
                if Decimal(probe_row["realization_idr_billion"]) != amount:
                    raise M25MaterializationError(f"canonical conversion drift {family} {geography_id}/{year}")

                html_crosscheck_status = "not_available_html_table_unparseable"
                if html_parseable:
                    html_row = html_accounts.get(label)
                    if html_row is None:
                        html_crosscheck_status = "diagnostic_locked_label_missing_in_html_table"
                    else:
                        try:
                            display_amount = stage1.parse_djpk_money_to_idr_billion(html_row["realization_raw"])
                            if html_display_matches_exact(display_amount, realization_rupiah):
                                html_crosscheck_status = "passed_display_rounding_crosscheck"
                            else:
                                html_crosscheck_status = "diagnostic_display_rounding_mismatch"
                        except stage1.M25Stage1Error:
                            html_crosscheck_status = "diagnostic_html_display_parse_failure"

                probe_status_map = {
                    "failed_locked_label_missing_in_html_table": "diagnostic_locked_label_missing_in_html_table",
                    "failed_display_rounding_crosscheck": "diagnostic_display_rounding_mismatch",
                    "failed_html_display_parse": "diagnostic_html_display_parse_failure",
                }
                expected_probe_status = probe_status_map.get(probe_row["html_crosscheck_status"], probe_row["html_crosscheck_status"])
                if expected_probe_status != html_crosscheck_status:
                    raise M25MaterializationError(f"HTML diagnostic status drift {family} {geography_id}/{year}")

                observations.append(
                    {
                        "observation_id": stable_id("m25obs_", family, geography_id, year),
                        "fiscal_account_id": family,
                        "geography_id": geography_id,
                        "geography_name": geography["canonical_name"],
                        "djpk_province_selector": geography["djpk_province_selector"],
                        "djpk_pemda_selector": pemda,
                        "year": year,
                        "reference_period": "annual_final_realization",
                        "source_account_label": source["account_label"],
                        "budget_rupiah_exact": format(budget_rupiah, "f"),
                        "realization_rupiah_exact": format(realization_rupiah, "f"),
                        "realization_idr_billion": format(amount, "f"),
                        "unit": "IDR_billion",
                        "claim_type": "observed_recorded_fiscal_realization",
                        "taxonomy_contract_type": "exact_label",
                        "taxonomy_contract_status": contract["stage1_promotion_status"],
                        "numeric_evidence_representation": "djpk_csv_apbd_spreadsheetml_exact_rupiah",
                        "html_crosscheck_status": html_crosscheck_status,
                        "fiscal_provenance_id": provenance_id,
                        "comparability_regime": REGIME_ID,
                        "imputation_performed": False,
                        "historical_boundary_reconstruction_performed": False,
                    }
                )

    observations.sort(key=lambda row: (row["fiscal_account_id"], row["geography_id"], row["year"]))
    provenance.sort(key=lambda row: (row["geography_id"], row["year"]))
    expected_observations = 152 * len(contracts)
    if len(observations) != expected_observations:
        raise M25MaterializationError("canonical fiscal observation count drift")
    if len(provenance) != 152:
        raise M25MaterializationError("fiscal provenance count drift")
    if html_parseable_count + html_unparseable_count != 152:
        raise M25MaterializationError("HTML representation accounting drift")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(OBS_OUT, list(observations[0].keys()), observations)
    write_csv(PROV_OUT, list(provenance[0].keys()), provenance)

    held_rows = [row for row in read_csv(CONTRACTS) if row["stage1_promotion_status"] != "promoted_exact_label"]
    manifest = {
        "schema": "ranah-observatory/djpk-fiscal-panel/v2",
        "milestone": 25,
        "source_id": "djpk_sikd_apbd_portal",
        "comparability_regime": REGIME_ID,
        "geography_level": "kabupaten_kota",
        "geography_count": 19,
        "start_year": 2018,
        "end_year": 2025,
        "year_count": 8,
        "jurisdiction_year_count": 152,
        "promoted_exact_label_family_count": len(contracts),
        "promoted_exact_label_families": [row["conceptual_family"] for row in contracts],
        "held_family_count": len(held_rows),
        "held_families": [row["conceptual_family"] for row in held_rows],
        "observation_count": len(observations),
        "provenance_count": len(provenance),
        "html_snapshot_count": 152,
        "spreadsheetml_snapshot_count": 152,
        "html_table_parseable_page_count": html_parseable_count,
        "html_table_unparseable_page_count": html_unparseable_count,
        "primary_numeric_evidence": "djpk_csv_apbd_spreadsheetml_exact_rupiah",
        "html_semantic_evidence": "identity_year_annual_final_status_same_selector_export_link",
        "annual_final_realization_semantics_required": True,
        "html_rounded_value_crosscheck_is_diagnostic": True,
        "derived_ratio_count": 0,
        "explicit_bridge_used": False,
        "imputation_performed": False,
        "historical_boundary_reconstruction_performed": False,
        "posthoc_account_family_search_performed": False,
        "statistical_model_fit": False,
        "inputs": {
            "crosswalk": {"path": CROSSWALK.relative_to(ROOT).as_posix(), "sha256": sha256(CROSSWALK)},
            "account_contracts": {"path": CONTRACTS.relative_to(ROOT).as_posix(), "sha256": sha256(CONTRACTS)},
            "account_contract_manifest": {"path": CONTRACT_MANIFEST.relative_to(ROOT).as_posix(), "sha256": sha256(CONTRACT_MANIFEST)},
            "transport_amendment": {"path": TRANSPORT.relative_to(ROOT).as_posix(), "sha256": sha256(TRANSPORT)},
            "full_probe_coverage": {"path": COVERAGE.relative_to(ROOT).as_posix(), "sha256": sha256(COVERAGE)},
            "full_probe_values": {"path": PROBE_VALUES.relative_to(ROOT).as_posix(), "sha256": sha256(PROBE_VALUES)},
            "stage1_manifest": {"path": STAGE1_MANIFEST.relative_to(ROOT).as_posix(), "sha256": sha256(STAGE1_MANIFEST)},
        },
        "outputs": {
            "canonical_observations": {"path": OBS_OUT.relative_to(ROOT).as_posix(), "sha256": sha256(OBS_OUT)},
            "provenance": {"path": PROV_OUT.relative_to(ROOT).as_posix(), "sha256": sha256(PROV_OUT)},
        },
    }
    MANIFEST_OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    try:
        manifest = materialize()
    except (OSError, json.JSONDecodeError, ValueError, M25MaterializationError, stage1.M25Stage1Error, M25DJPKExportError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "promoted_exact_label_families": manifest["promoted_exact_label_families"],
        "observation_count": manifest["observation_count"],
        "html_table_parseable_page_count": manifest["html_table_parseable_page_count"],
        "html_table_unparseable_page_count": manifest["html_table_unparseable_page_count"],
        "held_families": manifest["held_families"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
