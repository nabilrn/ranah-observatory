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
CONTRACT = ROOT / "data/manifests/milestone26_stage2_event_impact_contract.json"
FROZEN_SURFACE = ROOT / "data/processed/bnpb/m26_source_qualification/bnpb_event_impact_table.html"
PREFLIGHT = ROOT / "data/analysis/engine/disaster_risk_chain_v1/m26-stage2-event-impact-preflight.json"


class EventImpactContractError(RuntimeError):
    pass


class EventImpactHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.form_action = ""
        self.form_method = ""
        self.input_names: set[str] = set()
        self.select_names: set[str] = set()
        self.select_options: dict[str, list[str]] = {}
        self._select_name = ""
        self._option_value: str | None = None
        self._option_text: list[str] = []
        self._in_target_table = False
        self._in_head = False
        self._in_body = False
        self._in_cell = False
        self._cell_text: list[str] = []
        self.headers: list[str] = []
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key: (value or "") for key, value in attrs}
        if tag == "form" and not self.form_action:
            self.form_action = attr.get("action", "")
            self.form_method = attr.get("method", "").lower()
        elif tag == "input" and attr.get("name"):
            self.input_names.add(attr["name"])
        elif tag == "select" and attr.get("name"):
            self._select_name = attr["name"]
            self.select_names.add(self._select_name)
            self.select_options.setdefault(self._select_name, [])
        elif tag == "option" and self._select_name:
            self._option_value = attr.get("value", "")
            self._option_text = []
        elif tag == "table":
            classes = set(attr.get("class", "").split())
            if "datatab" in classes:
                self._in_target_table = True
        elif self._in_target_table and tag == "thead":
            self._in_head = True
        elif self._in_target_table and tag == "tbody":
            self._in_body = True
        elif self._in_target_table and tag == "tr" and self._in_body:
            self._row = []
        elif self._in_target_table and tag in {"td", "th"}:
            self._in_cell = True
            self._cell_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "option" and self._select_name and self._option_value is not None:
            value = self._option_value.strip() or clean_text("".join(self._option_text))
            self.select_options[self._select_name].append(value)
            self._option_value = None
            self._option_text = []
        elif tag == "select":
            self._select_name = ""
        elif self._in_target_table and tag in {"td", "th"} and self._in_cell:
            text = clean_text("".join(self._cell_text))
            if self._in_head:
                self.headers.append(text)
            elif self._in_body and self._row is not None:
                self._row.append(text)
            self._in_cell = False
            self._cell_text = []
        elif self._in_target_table and tag == "tr" and self._in_body and self._row is not None:
            if self._row:
                self.rows.append(self._row)
            self._row = None
        elif self._in_target_table and tag == "thead":
            self._in_head = False
        elif self._in_target_table and tag == "tbody":
            self._in_body = False
        elif self._in_target_table and tag == "table":
            self._in_target_table = False

    def handle_data(self, data: str) -> None:
        if self._option_value is not None:
            self._option_text.append(data)
        if self._in_cell:
            self._cell_text.append(data)


def clean_text(value: str) -> str:
    value = html.unescape(value)
    value = value.replace("\r", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", value).strip()


def load_contract() -> dict[str, Any]:
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if payload.get("schema") != "ranah-observatory/milestone26-stage2-event-impact-contract/v1":
        raise EventImpactContractError("unexpected Stage 2 event-impact contract schema")
    if payload.get("contract_locked_before_target_period_event_impact_retrieval") is not True:
        raise EventImpactContractError("Stage 2 contract is not locked before target retrieval")
    if payload["stage2a_retrieval_qualification"].get("impact_aggregation_authorized") is not False:
        raise EventImpactContractError("Stage 2a cannot aggregate impact")
    for key in (
        "cross_component_temporal_aggregation_authorized",
        "risk_synthesis_authorized",
        "statistical_model_fit_authorized",
        "causal_claim_authorized",
        "monetary_loss_inference_authorized",
        "monetary_wasted_potential_estimate_authorized",
    ):
        if payload.get(key) is not False:
            raise EventImpactContractError(f"forbidden Stage 2 authorization enabled: {key}")
    return payload


def parse_html(body: bytes) -> EventImpactHTMLParser:
    parser = EventImpactHTMLParser()
    parser.feed(body.decode("utf-8", errors="replace"))
    return parser


def impact_cell_state(raw: str) -> tuple[str, int | None]:
    value = clean_text(raw)
    if value == "":
        return "not_reported_or_missing", None
    if not re.fullmatch(r"[0-9]+", value):
        raise EventImpactContractError(f"impact cell is not a nonnegative integer or blank: {raw!r}")
    number = int(value)
    return ("explicit_reported_zero", 0) if number == 0 else ("reported_count", number)


def source_row_fingerprint(headers: list[str], row: list[str], contract: dict[str, Any]) -> str:
    if len(headers) != len(row):
        raise EventImpactContractError("row/header length mismatch")
    record = dict(zip(headers, row, strict=True))
    fields = contract["event_identity_rule"]["fallback_row_fingerprint_fields"]
    token = "|".join(clean_text(record[field]) for field in fields)
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def run_preflight() -> dict[str, Any]:
    contract = load_contract()
    body = FROZEN_SURFACE.read_bytes()
    parser = parse_html(body)
    expected_headers = contract["expected_table_columns"]
    if parser.form_action != "/databencana/tabel/pencarian.php" or parser.form_method != "post":
        raise EventImpactContractError("frozen BNPB form action/method drift")
    required_inputs = {"tgl_awal", "tgl_akhir", "submit"}
    if not required_inputs.issubset(parser.input_names):
        raise EventImpactContractError("frozen BNPB date/submit input surface incomplete")
    if "s_kejadian" not in parser.select_names:
        raise EventImpactContractError("frozen BNPB event-type selector missing")
    options = set(parser.select_options.get("s_kejadian", []))
    for event_type in contract["target_regime"]["event_types"]:
        if event_type not in options:
            raise EventImpactContractError(f"locked event type missing from source selector: {event_type}")
    if parser.headers != expected_headers:
        raise EventImpactContractError(f"event-impact table header drift: {parser.headers}")
    if not parser.rows:
        raise EventImpactContractError("frozen source surface contains no table rows for parser validation")
    if any(len(row) != len(expected_headers) for row in parser.rows):
        raise EventImpactContractError("frozen source surface contains malformed row width")

    blank_impact_cells = 0
    explicit_zero_impact_cells = 0
    positive_impact_cells = 0
    nonparseable_impact_cells = 0
    fingerprints: list[str] = []
    for row in parser.rows:
        record = dict(zip(expected_headers, row, strict=True))
        fingerprints.append(source_row_fingerprint(expected_headers, row, contract))
        for field in contract["impact_fields"]:
            try:
                state, _number = impact_cell_state(record[field])
            except EventImpactContractError:
                nonparseable_impact_cells += 1
                continue
            if state == "not_reported_or_missing":
                blank_impact_cells += 1
            elif state == "explicit_reported_zero":
                explicit_zero_impact_cells += 1
            else:
                positive_impact_cells += 1

    payload = {
        "schema": "ranah-observatory/milestone26-stage2-event-impact-preflight/v1",
        "milestone": 26,
        "stage": "2a_preflight_only",
        "frozen_surface_path": FROZEN_SURFACE.relative_to(ROOT).as_posix(),
        "frozen_surface_sha256": hashlib.sha256(body).hexdigest(),
        "form_action": parser.form_action,
        "form_method": parser.form_method,
        "event_type_selector": "s_kejadian",
        "locked_event_types_present": True,
        "header_count": len(parser.headers),
        "header_contract_match": True,
        "sample_row_count": len(parser.rows),
        "sample_exact_duplicate_fingerprint_count": len(fingerprints) - len(set(fingerprints)),
        "sample_blank_impact_cells": blank_impact_cells,
        "sample_explicit_zero_impact_cells": explicit_zero_impact_cells,
        "sample_positive_impact_cells": positive_impact_cells,
        "sample_nonparseable_impact_cells": nonparseable_impact_cells,
        "target_period_live_retrieval_performed": False,
        "impact_aggregation_performed": False,
        "blank_interpreted_as_zero": False,
        "automatic_duplicate_collapse_performed": False,
        "risk_synthesis_authorized": False,
        "causal_claim_created": False,
        "monetary_loss_inferred": False,
    }
    PREFLIGHT.parent.mkdir(parents=True, exist_ok=True)
    PREFLIGHT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    try:
        payload = run_preflight()
    except (OSError, ValueError, json.JSONDecodeError, EventImpactContractError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "header_contract_match": payload["header_contract_match"],
        "sample_row_count": payload["sample_row_count"],
        "target_period_live_retrieval_performed": payload["target_period_live_retrieval_performed"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
