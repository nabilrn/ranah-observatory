#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

import probe_milestone25_djpk_taxonomy as legacy
from milestone25_djpk_export import (
    M25DJPKExportError,
    exact_account_map,
    find_same_selector_export_url,
)
from probe_milestone25_djpk_stage1_export import fetch_export

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GATE = ROOT / "data/manifests/milestone25_design_gate.json"
DEFAULT_CROSSWALK = ROOT / "data/registries/djpk_sumbar_pemda.csv"
DEFAULT_DISCOVERY = ROOT / "data/analysis/engine/djpk_finance_v1/m25-taxonomy-discovery.csv"
DEFAULT_PRESENCE = ROOT / "data/analysis/engine/djpk_finance_v1/m25-account-presence.csv"
DEFAULT_MANIFEST = ROOT / "data/manifests/milestone25_taxonomy_discovery.json"
DEFAULT_RAW_DIR = ROOT / "data/processed/djpk/taxonomy_probe"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def run_probe(
    gate_path: Path,
    crosswalk_path: Path,
    discovery_path: Path,
    presence_path: Path,
    manifest_path: Path,
    raw_dir: Path,
) -> dict[str, Any]:
    gate = legacy.validate_gate(gate_path)
    legacy.validate_crosswalk(crosswalk_path)
    raw_dir.mkdir(parents=True, exist_ok=True)

    discovery_rows: list[dict[str, Any]] = []
    labels_by_year: dict[int, set[str]] = {}
    account_details_by_year: dict[int, list[dict[str, str]]] = {}
    raw_responses: list[dict[str, Any]] = []

    for year in legacy.YEARS:
        html_url = legacy.build_url(year)
        html_status, html_body, final_html_url = legacy.fetch_url(html_url)
        if html_status != 200:
            raise RuntimeError(f"DJPK returned HTTP {html_status} for Stage0 HTML year {year}")

        parser = legacy.HTMLTableParser()
        parser.feed(html_body.decode("utf-8", errors="replace"))
        page_text = parser.all_text
        jurisdiction_ok = legacy.normalize_label(legacy.EXPECTED_JURISDICTION) in legacy.normalize_label(page_text)
        year_ok = str(year) in page_text
        december_ok = bool(
            re.search(r"realisasi\s+apbd\s+s\.?\s*d\.?\s+desember", page_text, flags=re.IGNORECASE)
        )
        try:
            export_url = find_same_selector_export_url(html_body, legacy.PEMDA_SELECTOR, year)
        except M25DJPKExportError as exc:
            raise RuntimeError(f"DJPK Stage0 same-selector export link missing for {year}") from exc

        export_status, final_export_url, export_content_type, export_body = fetch_export(export_url)
        if export_status != 200:
            raise RuntimeError(f"DJPK returned HTTP {export_status} for Stage0 export year {year}")
        try:
            export_accounts = exact_account_map(export_body)
        except M25DJPKExportError as exc:
            raise RuntimeError(f"DJPK Stage0 SpreadsheetML invalid for {year}") from exc
        if not export_accounts:
            raise RuntimeError(f"DJPK Stage0 SpreadsheetML yielded no accounts for {year}")

        account_details = [
            {
                "account_label": row["account_label"],
                "account_label_normalized": row["account_label_normalized"],
            }
            for row in export_accounts.values()
        ]
        labels_by_year[year] = set(export_accounts)
        account_details_by_year[year] = account_details

        page_pass = jurisdiction_ok and year_ok and december_ok and bool(export_accounts)
        if not page_pass:
            raise RuntimeError(
                f"DJPK Stage0 identity/period/export failure year={year}: "
                f"jurisdiction={jurisdiction_ok} year={year_ok} december={december_ok} accounts={len(export_accounts)}"
            )

        html_path = raw_dir / f"kota-padang-apbd-{year}-desember.html"
        xml_path = raw_dir / f"kota-padang-apbd-{year}-desember.xml"
        html_path.write_bytes(html_body)
        xml_path.write_bytes(export_body)
        html_sha = sha256_bytes(html_body)
        export_sha = sha256_bytes(export_body)

        discovery_rows.append(
            {
                "year": year,
                "requested_html_url": html_url,
                "final_html_url": final_html_url,
                "html_http_status": html_status,
                "page_title": parser.title,
                "jurisdiction_expected": legacy.EXPECTED_JURISDICTION,
                "jurisdiction_match": jurisdiction_ok,
                "fiscal_year_match": year_ok,
                "december_realization_semantics_match": december_ok,
                "same_selector_export_link_match": True,
                "export_url": export_url,
                "final_export_url": final_export_url,
                "export_http_status": export_status,
                "export_content_type": export_content_type,
                "account_count": len(export_accounts),
                "taxonomy_numeric_representation": "djpk_csv_apbd_spreadsheetml_exact_rupiah",
                "html_role": "identity_year_december_same_selector_link",
                "html_response_sha256": html_sha,
                "export_response_sha256": export_sha,
                "html_snapshot": html_path.relative_to(ROOT).as_posix(),
                "export_snapshot": xml_path.relative_to(ROOT).as_posix(),
                "page_pass": page_pass,
            }
        )
        raw_responses.append(
            {
                "year": year,
                "html_path": html_path.relative_to(ROOT).as_posix(),
                "html_sha256": html_sha,
                "export_path": xml_path.relative_to(ROOT).as_posix(),
                "export_sha256": export_sha,
            }
        )

    all_labels = sorted({label for labels in labels_by_year.values() for label in labels})
    presence_rows: list[dict[str, Any]] = []
    for label in all_labels:
        years_present = [year for year in legacy.YEARS if label in labels_by_year[year]]
        source_labels = sorted(
            {
                item["account_label"]
                for year in years_present
                for item in account_details_by_year[year]
                if item["account_label_normalized"] == label
            }
        )
        presence_rows.append(
            {
                "account_label_normalized": label,
                "source_labels": "|".join(source_labels),
                "year_count": len(years_present),
                "years_present": "|".join(str(year) for year in years_present),
                "present_all_2018_2025": years_present == legacy.YEARS,
                **{f"present_{year}": year in years_present for year in legacy.YEARS},
            }
        )

    conceptual = legacy.classify_conceptual_families(labels_by_year)
    write_csv(discovery_path, list(discovery_rows[0].keys()), discovery_rows)
    write_csv(presence_path, list(presence_rows[0].keys()), presence_rows)

    manifest = {
        "schema": "ranah-observatory/milestone25-taxonomy-discovery/v1",
        "milestone": 25,
        "stage": 0,
        "phase": "post_phase2_fiscal_evidence_expansion",
        "criterion": "eight-year reference-jurisdiction taxonomy discovery before cross-geography fiscal extraction",
        "stage0_complete": True,
        "source_id": "djpk_sikd_apbd_portal",
        "reference_geography_id": "idn.13.1371",
        "reference_name": "Padang",
        "reference_djpk_province_selector": legacy.PROVINCE_SELECTOR,
        "reference_djpk_pemda_selector": legacy.PEMDA_SELECTOR,
        "period_selector": legacy.PERIOD_SELECTOR,
        "years": legacy.YEARS,
        "page_count": len(discovery_rows),
        "all_pages_pass": all(bool(row["page_pass"]) for row in discovery_rows),
        "unique_normalized_account_label_count": len(all_labels),
        "conceptual_account_family_results": conceptual,
        "taxonomy_primary_representation": "djpk_csv_apbd_spreadsheetml_exact_rupiah",
        "html_semantic_role": "identity_year_december_same_selector_export_link",
        "html_body_table_required": False,
        "spreadsheetml_account_table_required": True,
        "cross_geography_values_inspected_before_taxonomy_lock": False,
        "statistical_model_fit": False,
        "derived_ratio_created": False,
        "imputation_performed": False,
        "historical_boundary_reconstruction_performed": False,
        "posthoc_account_family_search_performed": False,
        "inputs": {
            "design_gate": {"path": gate_path.relative_to(ROOT).as_posix(), "sha256": legacy.sha256(gate_path)},
            "crosswalk": {"path": crosswalk_path.relative_to(ROOT).as_posix(), "sha256": legacy.sha256(crosswalk_path)},
        },
        "outputs": {
            "taxonomy_discovery": {"path": discovery_path.relative_to(ROOT).as_posix(), "sha256": legacy.sha256(discovery_path)},
            "account_presence": {"path": presence_path.relative_to(ROOT).as_posix(), "sha256": legacy.sha256(presence_path)},
        },
        "raw_responses": raw_responses,
        "design_gate_schema": gate["schema"],
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe DJPK Kota Padang Stage0 taxonomy using same-selector SpreadsheetML.")
    parser.add_argument("--design-gate", type=Path, default=DEFAULT_GATE)
    parser.add_argument("--crosswalk", type=Path, default=DEFAULT_CROSSWALK)
    parser.add_argument("--discovery", type=Path, default=DEFAULT_DISCOVERY)
    parser.add_argument("--presence", type=Path, default=DEFAULT_PRESENCE)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    args = parser.parse_args()
    try:
        result = run_probe(args.design_gate, args.crosswalk, args.discovery, args.presence, args.manifest, args.raw_dir)
    except (OSError, ValueError, RuntimeError, M25DJPKExportError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "stage0_complete": result["stage0_complete"],
        "page_count": result["page_count"],
        "taxonomy_primary_representation": result["taxonomy_primary_representation"],
        "conceptual_account_family_results": result["conceptual_account_family_results"],
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
