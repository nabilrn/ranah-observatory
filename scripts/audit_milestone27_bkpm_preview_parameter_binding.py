#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "data/manifests/milestone27_preview_parameter_binding_contract.json"
ROUTE_MANIFEST = ROOT / "data/manifests/milestone27_bkpm_preview_route_discovery.json"
INVENTORY = ROOT / "data/analysis/engine/investment_realization_v1/m27-bkpm-resource-inventory.csv"
OUT = ROOT / "data/manifests/milestone27_bkpm_preview_parameter_binding.json"


class BindingError(RuntimeError):
    pass


class HiddenInputParser(HTMLParser):
    def __init__(self, target_id: str) -> None:
        super().__init__(convert_charrefs=True)
        self.target_id = target_id
        self.values: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "input":
            return
        attr = {k: (v or "") for k, v in attrs}
        if attr.get("id") == self.target_id:
            self.values.append(attr.get("value", "").strip())


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_inventory() -> dict[tuple[int, str], dict[str, str]]:
    with INVENTORY.open(newline="", encoding="utf-8") as handle:
        rows = [{k: (v or "") for k, v in row.items()} for row in csv.DictReader(handle)]
    keyed = {(int(r["year"]), r["quarter"]): r for r in rows}
    if len(keyed) != 64:
        raise BindingError("inventory does not contain 64 unique year-quarter rows")
    return keyed


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_contract() -> dict[str, Any]:
    c = load_json(CONTRACT)
    if c.get("schema") != "ranah-observatory/milestone27-preview-parameter-binding-contract/v1":
        raise BindingError("unexpected binding contract schema")
    if c.get("contract_locked_before_systematic_parameter_value_extraction") is not True:
        raise BindingError("binding contract not locked")
    if c.get("offline_frozen_evidence_only") is not True:
        raise BindingError("offline-only boundary missing")
    if c.get("hidden_input_parameter_value_extraction_authorized") is not True:
        raise BindingError("hidden-input value extraction not authorized")
    if c.get("inventory_uuid_comparison_authorized") is not True:
        raise BindingError("inventory UUID comparison not authorized")
    for key in (
        "source_selection_uses_parameter_values",
        "preview_page_live_request_authorized",
        "client_side_data_endpoint_request_authorized",
        "request_parameter_submission_authorized",
        "table_column_name_extraction_authorized",
        "table_header_extraction_authorized",
        "table_body_extraction_authorized",
        "table_cell_text_extraction_authorized",
        "target_investment_values_inspection_authorized",
        "period_column_inspection_authorized",
        "csv_schema_inspection_authorized",
        "zip_resource_request_authorized",
        "interactive_disclaimer_form_submission_authorized",
        "synthetic_personal_information_submission_authorized",
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
            raise BindingError(f"forbidden authorization enabled: {key}")
    return c


def main() -> int:
    contract = load_contract()
    route_manifest = load_json(ROUTE_MANIFEST)
    inventory = read_inventory()

    if route_manifest.get("schema") != "ranah-observatory/milestone27-bkpm-preview-route-discovery/v1":
        raise BindingError("unexpected route manifest schema")
    if route_manifest.get("client_side_data_endpoint_requested") is not False:
        raise BindingError("route evidence already requested client endpoint")

    route_by_period = {
        (int(r["year"]), str(r["quarter"])): r
        for r in route_manifest["pilot_results"]
    }

    results: list[dict[str, Any]] = []
    for pilot in contract["pilot_periods"]:
        key = (int(pilot["year"]), str(pilot["quarter"]))
        route_row = route_by_period.get(key)
        inv_row = inventory.get(key)
        if route_row is None or inv_row is None:
            raise BindingError(f"pilot missing from frozen evidence: {key}")

        html_path = ROOT / route_row["response_path"]
        if not html_path.is_file():
            raise BindingError(f"missing frozen preview HTML: {html_path}")
        if sha256_path(html_path) != route_row["response_sha256"]:
            raise BindingError(f"preview HTML hash mismatch: {html_path}")

        parser = HiddenInputParser(contract["frozen_preview_hidden_input_id"])
        parser.feed(html_path.read_text(encoding="utf-8", errors="replace"))
        values = parser.values
        if len(values) != 1 or not values[0]:
            raise BindingError(f"expected exactly one non-empty hidden parameter for {key}, found {values}")

        preview_value = values[0]
        inventory_value = inv_row[contract["inventory_comparison_field"]]
        if not inventory_value:
            raise BindingError(f"inventory comparison UUID missing for {key}")
        exact_match = preview_value == inventory_value

        results.append({
            "year": key[0],
            "quarter": key[1],
            "dataset_identifier": route_row["dataset_identifier"],
            "source_html_path": route_row["response_path"],
            "source_html_sha256": route_row["response_sha256"],
            "parameter_name": contract["parameter_name"],
            "hidden_input_match_count": 1,
            "preview_parameter_value": preview_value,
            "inventory_resource_file_uuid": inventory_value,
            "exact_uuid_match": exact_match,
            "source_selection_uses_parameter_values": False,
            "preview_page_live_requested": False,
            "client_side_data_endpoint_requested": False,
            "request_parameter_submitted": False,
            "table_column_names_extracted": False,
            "table_header_extracted": False,
            "table_body_extracted": False,
            "table_cell_text_extracted": False,
            "target_investment_values_inspected": False,
        })

    binding_qualified = len(results) == 3 and all(r["exact_uuid_match"] for r in results)
    payload = {
        "schema": "ranah-observatory/milestone27-bkpm-preview-parameter-binding/v1",
        "milestone": 27,
        "stage": "stage0f_frozen_preview_parameter_binding",
        "pilot_count": len(results),
        "pilot_results": results,
        "binding_qualified": binding_qualified,
        "parameter_name": contract["parameter_name"],
        "inventory_comparison_field": contract["inventory_comparison_field"],
        "offline_frozen_evidence_only": True,
        "source_selection_uses_parameter_values": False,
        "preview_page_live_requested": False,
        "client_side_data_endpoint_requested": False,
        "request_parameter_submitted": False,
        "table_column_names_extracted": False,
        "table_header_extracted": False,
        "table_body_extracted": False,
        "table_cell_text_extracted": False,
        "target_investment_values_inspected": False,
        "period_column_inspected": False,
        "csv_schema_inspected": False,
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
        "route_manifest": {"path": rel(ROUTE_MANIFEST), "sha256": sha256_path(ROUTE_MANIFEST)},
        "inventory": {"path": rel(INVENTORY), "sha256": sha256_path(INVENTORY)},
    }
    write_json(OUT, payload)
    print(json.dumps({
        "pilot_count": len(results),
        "binding_qualified": binding_qualified,
        "exact_match_count": sum(1 for r in results if r["exact_uuid_match"]),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError, BindingError) as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
