#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import html
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "data/manifests/milestone27_preview_request_metadata_contract.json"
ROUTE_MANIFEST = ROOT / "data/manifests/milestone27_bkpm_preview_route_discovery.json"
OUT = ROOT / "data/manifests/milestone27_bkpm_preview_request_metadata.json"


class RequestMetadataError(RuntimeError):
    pass


class ScriptParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.inline_scripts: list[str] = []
        self._in_script = False
        self._buffer: list[str] = []
        self._has_src = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "script":
            return
        attr = {k: (v or "") for k, v in attrs}
        self._in_script = True
        self._buffer = []
        self._has_src = bool(attr.get("src", "").strip())

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._in_script:
            text = "".join(self._buffer)
            if text.strip() and not self._has_src:
                self.inline_scripts.append(text)
            self._in_script = False
            self._buffer = []
            self._has_src = False

    def handle_data(self, data: str) -> None:
        if self._in_script:
            self._buffer.append(data)


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
    if c.get("schema") != "ranah-observatory/milestone27-preview-request-metadata-contract/v1":
        raise RequestMetadataError("unexpected contract schema")
    if c.get("contract_locked_before_request_construction_inspection") is not True:
        raise RequestMetadataError("contract not locked")
    if c.get("offline_frozen_html_only") is not True:
        raise RequestMetadataError("offline-only boundary missing")
    for key in (
        "request_parameter_values_extraction_authorized",
        "csrf_or_token_value_extraction_authorized",
        "table_column_name_extraction_authorized",
        "table_header_extraction_authorized",
        "table_body_extraction_authorized",
        "table_cell_text_extraction_authorized",
        "client_side_data_endpoint_request_authorized",
        "preview_page_live_request_authorized",
        "zip_resource_request_authorized",
        "interactive_disclaimer_form_submission_authorized",
        "synthetic_personal_information_submission_authorized",
        "target_investment_values_inspection_authorized",
        "period_column_inspection_authorized",
        "csv_schema_inspection_authorized",
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
            raise RequestMetadataError(f"forbidden authorization enabled: {key}")
    return c


def normalize_route(raw: str) -> str:
    raw = html.unescape(raw.strip())
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    if not raw.startswith("/"):
        raw = "/" + raw
    return "https://data.bkpm.go.id" + raw


def extract_request_metadata(scripts: list[str], target_route: str) -> dict[str, Any]:
    route_pattern = re.compile(r"\burl\s*:\s*['\"]([^'\"]+)['\"]", flags=re.IGNORECASE)
    constructions: list[dict[str, Any]] = []
    any_server_side: bool | None = None
    any_processing: bool | None = None

    for script in scripts:
        script_has_target = False
        for match in route_pattern.finditer(script):
            route = normalize_route(match.group(1))
            if route != target_route:
                continue
            script_has_target = True

            # Only inspect the bounded request-construction region after this route literal.
            start = match.end()
            end = min(len(script), match.end() + 900)
            window = script[start:end]

            method_match = re.search(r"\b(?:type|method)\s*:\s*['\"]([A-Za-z]+)['\"]", window, flags=re.IGNORECASE)
            method = method_match.group(1).upper() if method_match else "unresolved"

            key_names: set[str] = set()
            object_match = re.search(r"\bdata\s*:\s*\{(.{0,500}?)\}", window, flags=re.IGNORECASE | re.DOTALL)
            if object_match:
                object_text = object_match.group(1)
                for key in re.findall(r"(?:^|[,\n])\s*([A-Za-z_][A-Za-z0-9_]*)\s*:", object_text):
                    key_names.add(key)
            for key in re.findall(r"\b(?:d|data)\.([A-Za-z_][A-Za-z0-9_]*)\s*=", window):
                key_names.add(key)

            constructions.append({
                "http_method": method,
                "request_parameter_key_names": sorted(key_names),
                "request_parameter_values_extracted": False,
            })

        if script_has_target:
            for flag in ("serverSide", "processing"):
                flag_match = re.search(rf"\b{flag}\s*:\s*(true|false)", script, flags=re.IGNORECASE)
                if flag_match:
                    value = flag_match.group(1).lower() == "true"
                    if flag == "serverSide":
                        any_server_side = value
                    else:
                        any_processing = value

    if not constructions:
        raise RequestMetadataError("target route request construction not found")

    methods = sorted({item["http_method"] for item in constructions})
    key_sets = sorted({tuple(item["request_parameter_key_names"]) for item in constructions})
    union_keys = sorted({key for item in constructions for key in item["request_parameter_key_names"]})

    return {
        "target_route_match_count": len(constructions),
        "http_methods": methods,
        "request_parameter_key_sets": [list(keys) for keys in key_sets],
        "request_parameter_key_names": union_keys,
        "request_parameter_key_count": len(union_keys),
        "datatable_flags": {
            "serverSide": any_server_side,
            "processing": any_processing,
        },
        "request_parameter_values_extracted": False,
        "csrf_or_token_values_extracted": False,
        "table_column_names_extracted": False,
        "table_header_extracted": False,
        "table_body_extracted": False,
        "table_cell_text_extracted": False,
    }


def main() -> int:
    contract = load_contract()
    route_manifest = load_json(ROUTE_MANIFEST)
    if route_manifest.get("schema") != "ranah-observatory/milestone27-bkpm-preview-route-discovery/v1":
        raise RequestMetadataError("unexpected route-discovery manifest schema")
    if route_manifest.get("client_side_data_endpoint_requested") is not False:
        raise RequestMetadataError("route-discovery evidence already requested client endpoint")

    target_route = contract["target_route"]
    if target_route not in route_manifest.get("common_route_literal_candidates", []):
        raise RequestMetadataError("target route not common across frozen pilots")

    pilot_results: list[dict[str, Any]] = []
    signatures: list[tuple[Any, ...]] = []

    for pilot in route_manifest["pilot_results"]:
        html_path = ROOT / pilot["response_path"]
        if not html_path.is_file():
            raise RequestMetadataError(f"missing frozen HTML: {html_path}")
        if sha256_path(html_path) != pilot["response_sha256"]:
            raise RequestMetadataError(f"frozen HTML hash mismatch: {html_path}")

        parser = ScriptParser()
        parser.feed(html_path.read_text(encoding="utf-8", errors="replace"))
        metadata = extract_request_metadata(parser.inline_scripts, target_route)
        signature = (
            metadata["target_route_match_count"],
            tuple(metadata["http_methods"]),
            tuple(tuple(keys) for keys in metadata["request_parameter_key_sets"]),
            tuple(sorted(metadata["datatable_flags"].items())),
        )
        signatures.append(signature)

        pilot_results.append({
            "year": pilot["year"],
            "quarter": pilot["quarter"],
            "pilot_role": pilot["pilot_role"],
            "dataset_identifier": pilot["dataset_identifier"],
            "source_html_path": pilot["response_path"],
            "source_html_sha256": pilot["response_sha256"],
            **metadata,
            "client_side_data_endpoint_requested": False,
            "preview_page_live_requested": False,
            "target_investment_values_inspected": False,
            "period_column_inspected": False,
            "csv_schema_inspected": False,
        })

    consistent = len(set(signatures)) == 1
    resolved = (
        consistent
        and all(r["target_route_match_count"] >= 1 for r in pilot_results)
        and all(r["http_methods"] == ["GET"] for r in pilot_results)
        and all(r["request_parameter_key_names"] == ["dataset_detail_parent_id"] for r in pilot_results)
        and all(r["datatable_flags"]["serverSide"] is True for r in pilot_results)
    )

    payload = {
        "schema": "ranah-observatory/milestone27-bkpm-preview-request-metadata/v1",
        "milestone": 27,
        "stage": "stage0e_frozen_preview_request_metadata",
        "pilot_count": len(pilot_results),
        "target_route": target_route,
        "pilot_results": pilot_results,
        "request_metadata_consistent_across_pilots": consistent,
        "request_metadata_resolved": resolved,
        "offline_frozen_html_only": True,
        "request_parameter_values_extracted": False,
        "csrf_or_token_values_extracted": False,
        "table_column_names_extracted": False,
        "table_header_extracted": False,
        "table_body_extracted": False,
        "table_cell_text_extracted": False,
        "client_side_data_endpoint_requested": False,
        "preview_page_live_requested": False,
        "zip_resource_requested": False,
        "interactive_disclaimer_form_submitted": False,
        "synthetic_personal_information_submitted": False,
        "target_investment_values_inspected": False,
        "period_column_inspected": False,
        "csv_schema_inspected": False,
        "investment_value_aggregation_performed": False,
        "quarterly_flow_interpretation_authorized": False,
        "cross_quarter_additivity_authorized": False,
        "annual_sum_authorized": False,
        "geography_mapping_authorized": False,
        "statistical_model_fit": False,
        "causal_claim_created": False,
        "monetary_wasted_potential_estimated": False,
        "contract": {"path": rel(CONTRACT), "sha256": sha256_path(CONTRACT)},
        "route_discovery_manifest": {"path": rel(ROUTE_MANIFEST), "sha256": sha256_path(ROUTE_MANIFEST)},
    }
    write_json(OUT, payload)
    print(json.dumps({
        "pilot_count": len(pilot_results),
        "request_metadata_consistent_across_pilots": consistent,
        "request_metadata_resolved": resolved,
        "target_route_match_counts": sorted({r['target_route_match_count'] for r in pilot_results}),
        "http_methods": sorted({tuple(r['http_methods']) for r in pilot_results}),
        "parameter_key_sets": sorted({tuple(r['request_parameter_key_names']) for r in pilot_results}),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError, RequestMetadataError) as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
