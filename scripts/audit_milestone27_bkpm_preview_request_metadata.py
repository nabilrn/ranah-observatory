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


def extract_target_route_metadata(script: str, target_route: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    route_pattern = re.compile(r"\burl\s*:\s*['\"]([^'\"]+)['\"]", flags=re.IGNORECASE)
    for match in route_pattern.finditer(script):
        route = normalize_route(match.group(1))
        if route != target_route:
            continue

        start = max(0, match.start() - 1800)
        end = min(len(script), match.end() + 2800)
        window = script[start:end]

        method_match = re.search(r"\b(?:type|method)\s*:\s*['\"]([A-Za-z]+)['\"]", window, flags=re.IGNORECASE)
        method = method_match.group(1).upper() if method_match else "unresolved"

        key_names: set[str] = set()

        # Object-style request payload: data: { key: value, ... }
        object_match = re.search(r"\bdata\s*:\s*\{(.{0,1800}?)\}", window, flags=re.IGNORECASE | re.DOTALL)
        if object_match:
            object_text = object_match.group(1)
            for key in re.findall(r"(?:^|[,\n])\s*([A-Za-z_][A-Za-z0-9_]*)\s*:", object_text):
                key_names.add(key)

        # Function-style payload enrichment: d.key = ... or data.key = ...
        for key in re.findall(r"\b(?:d|data)\.([A-Za-z_][A-Za-z0-9_]*)\s*=", window):
            key_names.add(key)

        flags: dict[str, bool | None] = {}
        for flag in ("serverSide", "processing"):
            flag_match = re.search(rf"\b{flag}\s*:\s*(true|false)", window, flags=re.IGNORECASE)
            flags[flag] = None if not flag_match else flag_match.group(1).lower() == "true"

        results.append({
            "route": route,
            "http_method": method,
            "request_parameter_key_names": sorted(key_names),
            "request_parameter_key_count": len(key_names),
            "datatable_flags": flags,
            "request_parameter_values_extracted": False,
            "csrf_or_token_values_extracted": False,
            "table_column_names_extracted": False,
            "table_header_extracted": False,
            "table_body_extracted": False,
            "table_cell_text_extracted": False,
        })
    return results


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
    all_signatures: list[tuple[str, tuple[str, ...], tuple[tuple[str, bool | None], ...]]] = []

    for pilot in route_manifest["pilot_results"]:
        html_path = ROOT / pilot["response_path"]
        if not html_path.is_file():
            raise RequestMetadataError(f"missing frozen HTML: {html_path}")
        if sha256_path(html_path) != pilot["response_sha256"]:
            raise RequestMetadataError(f"frozen HTML hash mismatch: {html_path}")

        parser = ScriptParser()
        parser.feed(html_path.read_text(encoding="utf-8", errors="replace"))
        matches: list[dict[str, Any]] = []
        for script in parser.inline_scripts:
            matches.extend(extract_target_route_metadata(script, target_route))

        if len(matches) != 1:
            raise RequestMetadataError(
                f"expected exactly one target-route request construction for {pilot['year']}-{pilot['quarter']}, found {len(matches)}"
            )
        metadata = matches[0]
        signature = (
            metadata["http_method"],
            tuple(metadata["request_parameter_key_names"]),
            tuple(sorted(metadata["datatable_flags"].items())),
        )
        all_signatures.append(signature)

        pilot_results.append({
            "year": pilot["year"],
            "quarter": pilot["quarter"],
            "pilot_role": pilot["pilot_role"],
            "dataset_identifier": pilot["dataset_identifier"],
            "source_html_path": pilot["response_path"],
            "source_html_sha256": pilot["response_sha256"],
            "target_route_match_count": 1,
            **metadata,
            "client_side_data_endpoint_requested": False,
            "preview_page_live_requested": False,
            "target_investment_values_inspected": False,
            "period_column_inspected": False,
            "csv_schema_inspected": False,
        })

    request_metadata_consistent_across_pilots = len(set(all_signatures)) == 1
    resolved = (
        request_metadata_consistent_across_pilots
        and all(r["http_method"] != "unresolved" for r in pilot_results)
        and all(r["request_parameter_key_count"] > 0 for r in pilot_results)
    )

    payload = {
        "schema": "ranah-observatory/milestone27-bkpm-preview-request-metadata/v1",
        "milestone": 27,
        "stage": "stage0e_frozen_preview_request_metadata",
        "pilot_count": len(pilot_results),
        "target_route": target_route,
        "pilot_results": pilot_results,
        "request_metadata_consistent_across_pilots": request_metadata_consistent_across_pilots,
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
        "request_metadata_consistent_across_pilots": request_metadata_consistent_across_pilots,
        "request_metadata_resolved": resolved,
        "http_methods": sorted({r['http_method'] for r in pilot_results}),
        "parameter_key_sets": sorted({tuple(r['request_parameter_key_names']) for r in pilot_results}),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError, RequestMetadataError) as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
