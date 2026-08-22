#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "data/manifests/milestone27_preview_route_discovery_contract.json"
INVENTORY = ROOT / "data/analysis/engine/investment_realization_v1/m27-bkpm-resource-inventory.csv"
OUT = ROOT / "data/manifests/milestone27_bkpm_preview_route_discovery.json"
RAW_ROOT = ROOT / "data/processed/bkpm/m27_preview_route_discovery"
USER_AGENT = "ranah-observatory/1.0 (+https://github.com/nabilrn/ranah-observatory)"


class PreviewRouteError(RuntimeError):
    pass


class ScriptOnlyParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.script_srcs: list[str] = []
        self.inline_scripts: list[str] = []
        self._in_script = False
        self._script_buffer: list[str] = []
        self._heading_tag = ""
        self._heading_buffer: list[str] = []
        self.headings: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {k: (v or "") for k, v in attrs}
        if tag == "script":
            src = attr.get("src", "").strip()
            if src:
                self.script_srcs.append(html.unescape(src))
            self._in_script = True
            self._script_buffer = []
        elif tag in {"h1", "h2", "h3", "h4"}:
            self._heading_tag = tag
            self._heading_buffer = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._in_script:
            text = "".join(self._script_buffer).strip()
            if text:
                self.inline_scripts.append(text)
            self._in_script = False
            self._script_buffer = []
        elif tag == self._heading_tag and self._heading_tag:
            text = re.sub(r"\s+", " ", html.unescape("".join(self._heading_buffer))).strip()
            if text:
                self.headings.append(text)
            self._heading_tag = ""
            self._heading_buffer = []

    def handle_data(self, data: str) -> None:
        if self._in_script:
            self._script_buffer.append(data)
        elif self._heading_tag:
            self._heading_buffer.append(data)


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [{k: (v or "") for k, v in row.items()} for row in csv.DictReader(handle)]


def load_contract() -> dict[str, Any]:
    c = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if c.get("schema") != "ranah-observatory/milestone27-preview-route-discovery-contract/v1":
        raise PreviewRouteError("unexpected preview-route contract schema")
    if c.get("contract_locked_before_live_preview_page_retrieval") is not True:
        raise PreviewRouteError("preview-route contract not locked before retrieval")
    if c.get("preview_page_get_authorized") is not True:
        raise PreviewRouteError("preview page GET is not authorized")
    for key in (
        "table_header_extraction_authorized",
        "table_body_extraction_authorized",
        "table_cell_text_extraction_authorized",
        "client_side_data_endpoint_request_authorized",
        "zip_resource_request_authorized",
        "interactive_disclaimer_form_submission_authorized",
        "synthetic_personal_information_submission_authorized",
        "target_investment_values_inspection_authorized",
        "period_column_inspection_authorized",
        "csv_schema_inspection_authorized",
        "source_selection_uses_target_values",
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
            raise PreviewRouteError(f"forbidden preview-route authorization enabled: {key}")
    return c


def request_bytes(url: str, attempts: int = 3) -> tuple[str, str, bytes]:
    error: Exception | None = None
    for attempt in range(attempts):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*;q=0.8"})
        try:
            with urllib.request.urlopen(req, timeout=40) as response:
                final_url = response.geturl()
                body = response.read()
                if not body:
                    raise PreviewRouteError("empty preview page response")
                return final_url, response.headers.get("Content-Type", ""), body
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, PreviewRouteError) as exc:
            error = exc
            if attempt + 1 < attempts:
                time.sleep(1.5 * (attempt + 1))
    raise PreviewRouteError(f"preview request failed: {url}: {error}")


def extract_route_literals(script: str, base_url: str) -> list[dict[str, str]]:
    found: dict[str, str] = {}
    patterns = [
        ("fetch_literal", r"fetch\(\s*['\"]([^'\"]+)['\"]"),
        ("ajax_url_literal", r"\burl\s*:\s*['\"]([^'\"]+)['\"]"),
        ("axios_literal", r"axios\.(?:get|post)\(\s*['\"]([^'\"]+)['\"]"),
    ]
    for kind, pattern in patterns:
        for match in re.finditer(pattern, script, flags=re.IGNORECASE):
            raw = html.unescape(match.group(1)).strip()
            if not raw or raw.startswith(("javascript:", "#")):
                continue
            absolute = urllib.parse.urljoin(base_url, raw)
            host = urllib.parse.urlparse(absolute).hostname
            if host != "data.bkpm.go.id":
                continue
            lower = absolute.lower()
            if not any(token in lower for token in ("dataset", "data", "preview", "view", "table", "ajax", "api")):
                continue
            found.setdefault(absolute, kind)
    return [{"url": url, "discovery_kind": found[url]} for url in sorted(found)]


def main() -> int:
    contract = load_contract()
    rows = read_csv(INVENTORY)
    by_period = {(int(r["year"]), r["quarter"]): r for r in rows}
    if len(by_period) != 64:
        raise PreviewRouteError("inventory does not contain 64 unique periods")

    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    endpoint_sets: list[set[str]] = []

    for pilot in contract["pilot_periods_locked_before_probe"]:
        year = int(pilot["year"])
        quarter = str(pilot["quarter"])
        row = by_period.get((year, quarter))
        if row is None:
            raise PreviewRouteError(f"pilot missing from inventory: {year}-{quarter}")
        detail_url = row["dataset_detail_url"]
        if "/dataset-detail/" not in detail_url:
            raise PreviewRouteError(f"unexpected detail URL: {detail_url}")
        preview_url = detail_url.replace("/dataset-detail/", "/dataset-view/", 1)
        final_url, content_type, body = request_bytes(preview_url)
        parsed = urllib.parse.urlparse(final_url)
        if parsed.scheme != "https" or parsed.hostname != contract["official_domain"]:
            raise PreviewRouteError(f"preview escaped official domain: {final_url}")

        parser = ScriptOnlyParser()
        parser.feed(body.decode("utf-8", errors="replace"))
        expected_title = row["dataset_title"]
        title_match = any(expected_title.lower() in heading.lower() for heading in parser.headings)
        if not title_match:
            raise PreviewRouteError(f"preview page title mismatch for {year}-{quarter}: {parser.headings}")

        routes: list[dict[str, str]] = []
        for script in parser.inline_scripts:
            routes.extend(extract_route_literals(script, final_url))
        dedup = {item["url"]: item for item in routes}
        routes = [dedup[url] for url in sorted(dedup)]
        endpoint_sets.append(set(dedup))

        raw_path = RAW_ROOT / f"{year}-q{row['quarter_number']}-preview.html"
        raw_path.write_bytes(body)
        script_path = RAW_ROOT / f"{year}-q{row['quarter_number']}-script-routes.json"
        script_payload = {
            "schema": "ranah-observatory/milestone27-preview-script-routes/v1",
            "year": year,
            "quarter": quarter,
            "pilot_role": pilot["role"],
            "preview_url": preview_url,
            "final_url": final_url,
            "title_match": title_match,
            "headings": parser.headings,
            "external_script_srcs": sorted(set(urllib.parse.urljoin(final_url, src) for src in parser.script_srcs)),
            "inline_script_count": len(parser.inline_scripts),
            "route_literal_candidates": routes,
            "table_header_extracted": False,
            "table_body_extracted": False,
            "table_cell_text_extracted": False,
            "client_side_data_endpoint_requested": False,
            "target_investment_values_inspected": False,
        }
        write_json(script_path, script_payload)
        results.append({
            "year": year,
            "quarter": quarter,
            "quarter_number": int(row["quarter_number"]),
            "pilot_role": pilot["role"],
            "dataset_identifier": row["dataset_identifier"],
            "semantic_family_state": row["semantic_family_state"],
            "preview_url": preview_url,
            "final_url": final_url,
            "content_type": content_type,
            "response_path": rel(raw_path),
            "response_sha256": sha256_path(raw_path),
            "response_bytes": len(body),
            "title_match": title_match,
            "external_script_src_count": len(set(parser.script_srcs)),
            "inline_script_count": len(parser.inline_scripts),
            "route_literal_candidate_count": len(routes),
            "route_literal_candidates": routes,
            "script_route_evidence_path": rel(script_path),
            "script_route_evidence_sha256": sha256_path(script_path),
            "table_header_extracted": False,
            "table_body_extracted": False,
            "table_cell_text_extracted": False,
            "client_side_data_endpoint_requested": False,
            "zip_resource_requested": False,
            "disclaimer_form_submitted": False,
            "target_investment_values_inspected": False,
        })

    common_routes = sorted(set.intersection(*endpoint_sets)) if endpoint_sets else []
    payload = {
        "schema": "ranah-observatory/milestone27-bkpm-preview-route-discovery/v1",
        "milestone": 27,
        "stage": "stage0d_public_preview_route_discovery",
        "pilot_count": len(results),
        "pilot_results": results,
        "common_route_literal_candidates": common_routes,
        "common_route_literal_candidate_count": len(common_routes),
        "route_candidate_found": any(item["route_literal_candidate_count"] > 0 for item in results),
        "preview_page_html_retrieved": True,
        "table_header_extracted": False,
        "table_body_extracted": False,
        "table_cell_text_extracted": False,
        "client_side_data_endpoint_requested": False,
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
        "inventory": {"path": rel(INVENTORY), "sha256": sha256_path(INVENTORY)},
    }
    write_json(OUT, payload)
    print(json.dumps({
        "pilot_count": len(results),
        "route_candidate_found": payload["route_candidate_found"],
        "common_route_literal_candidate_count": len(common_routes),
        "target_investment_values_inspected": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError, PreviewRouteError) as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
