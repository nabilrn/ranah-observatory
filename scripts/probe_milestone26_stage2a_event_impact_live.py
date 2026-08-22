#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from scripts.probe_milestone26_event_impact_retrieval import (
    EventImpactContractError,
    clean_text,
    impact_cell_state,
    load_contract,
    parse_html,
    source_row_fingerprint,
)

ROOT = Path(__file__).resolve().parents[1]
M16_FRAME = ROOT / "data/analysis/engine/spatial_climate_risk_v1/m16-spatial-component-frame.csv"
RAW_ROOT = ROOT / "data/processed/bnpb/m26_stage2_event_impact_2024"
ROWS_PATH = ROOT / "data/analysis/engine/disaster_risk_chain_v1/m26-stage2a-event-impact-row-diagnostics.jsonl"
MANIFEST_PATH = ROOT / "data/manifests/milestone26_stage2a_event_impact_retrieval.json"


class Stage2aRetrievalError(RuntimeError):
    pass


def sha256_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def slug_event_type(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def load_geography_contract() -> dict[int, dict[str, str]]:
    with M16_FRAME.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 19:
        raise Stage2aRetrievalError(f"M16 geography frame count drift: {len(rows)} != 19")
    result: dict[int, dict[str, str]] = {}
    for row in rows:
        geography_id = row.get("geography_id", "")
        match = re.fullmatch(r"idn\.13\.(\d{4})", geography_id)
        if not match:
            raise Stage2aRetrievalError(f"unexpected M16 geography id: {geography_id!r}")
        code = int(match.group(1))
        if code in result:
            raise Stage2aRetrievalError(f"duplicate M16 geography code: {code}")
        if row.get("spatial_frame") != "BIG_June_2026_fixed_current_boundary":
            raise Stage2aRetrievalError("M16 geography frame semantic drift")
        result[code] = {
            "geography_id": geography_id,
            "geography_name": row.get("geography_name", ""),
        }
    return result


def parse_source_date(value: str) -> str:
    text = clean_text(value)
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    raise Stage2aRetrievalError(f"unparseable source event date: {value!r}")


def post_html(url: str, form: dict[str, str], timeout: float = 120.0) -> tuple[str, str, bytes]:
    data = urllib.parse.urlencode(form).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "User-Agent": "ranah-observatory/0.1 (+https://github.com/nabilrn/ranah-observatory)",
            "Accept": "text/html,application/xhtml+xml,*/*",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if int(response.status) != 200:
            raise Stage2aRetrievalError(f"HTTP {response.status}: {url}")
        return str(response.geturl()), str(response.headers.get("Content-Type", "")), response.read()


def validate_parser_surface(parser: Any, contract: dict[str, Any], event_type: str) -> None:
    expected_headers = contract["expected_table_columns"]
    if parser.headers != expected_headers:
        raise Stage2aRetrievalError(f"event-impact table header drift for {event_type}: {parser.headers}")
    if any(len(row) != len(expected_headers) for row in parser.rows):
        raise Stage2aRetrievalError(f"malformed event-impact row width for {event_type}")


def build_form(contract: dict[str, Any], event_type: str) -> dict[str, str]:
    source = contract["official_source"]
    target = contract["target_regime"]
    params = source["form_parameters"]
    return {
        params["event_type"]: event_type,
        params["start_date"]: target["start_date"],
        params["end_date"]: target["end_date"],
        params["submit"]: source["submit_value"],
    }


def acquire_or_load(
    *, contract: dict[str, Any], event_type: str, mode: str
) -> tuple[Path, Path, dict[str, Any], bytes]:
    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    slug = slug_event_type(event_type)
    html_path = RAW_ROOT / f"{slug}.html"
    sidecar_path = RAW_ROOT / f"{slug}.request.json"
    form = build_form(contract, event_type)
    url = contract["official_source"]["url"]

    if mode == "live":
        final_url, content_type, body = post_html(url, form)
        if "html" not in content_type.casefold():
            raise Stage2aRetrievalError(f"unexpected content type for {event_type}: {content_type}")
        html_path.write_bytes(body)
        sidecar = {
            "schema": "ranah-observatory/milestone26-stage2a-event-impact-request/v1",
            "source_url": url,
            "final_url": final_url,
            "method": "POST",
            "content_type": content_type,
            "event_type": event_type,
            "form": form,
            "response_path": rel(html_path),
            "response_sha256": sha256_bytes(body),
            "response_bytes": len(body),
        }
        write_json(sidecar_path, sidecar)
    else:
        if not html_path.exists() or not sidecar_path.exists():
            raise Stage2aRetrievalError(f"offline Stage 2a evidence missing for {event_type}")
        body = html_path.read_bytes()
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        if sidecar.get("schema") != "ranah-observatory/milestone26-stage2a-event-impact-request/v1":
            raise Stage2aRetrievalError(f"unexpected request-sidecar schema for {event_type}")
        if sidecar.get("source_url") != url or sidecar.get("method") != "POST":
            raise Stage2aRetrievalError(f"offline request endpoint/method drift for {event_type}")
        if sidecar.get("event_type") != event_type or sidecar.get("form") != form:
            raise Stage2aRetrievalError(f"offline request form drift for {event_type}")
        if sidecar.get("response_sha256") != sha256_path(html_path):
            raise Stage2aRetrievalError(f"offline raw HTML checksum mismatch for {event_type}")
        if int(sidecar.get("response_bytes", -1)) != html_path.stat().st_size:
            raise Stage2aRetrievalError(f"offline raw HTML byte-count mismatch for {event_type}")
    return html_path, sidecar_path, sidecar, body


def parse_target_rows(
    *,
    parser: Any,
    contract: dict[str, Any],
    geography: dict[int, dict[str, str]],
    query_event_type: str,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    headers = contract["expected_table_columns"]
    impact_fields = contract["impact_fields"]
    target_year = int(contract["target_regime"]["year"])
    diagnostics = {
        "source_row_count": len(parser.rows),
        "retained_sumbar_row_count": 0,
        "blank_impact_cells": 0,
        "explicit_zero_impact_cells": 0,
        "positive_impact_cells": 0,
        "blank_source_event_ids": 0,
    }
    retained: list[dict[str, Any]] = []

    for source_index, row in enumerate(parser.rows, start=1):
        record = dict(zip(headers, row, strict=True))
        source_event_type = clean_text(record["Kejadian"]).upper()
        if source_event_type != query_event_type.upper():
            raise Stage2aRetrievalError(
                f"server event-type filter drift for {query_event_type}: returned {source_event_type!r}"
            )
        iso_date = parse_source_date(record["Tanggal Kejadian"])
        if int(iso_date[:4]) != target_year:
            raise Stage2aRetrievalError(
                f"server date-range filter drift for {query_event_type}: returned {iso_date}"
            )

        id_text = clean_text(record["ID Kabupaten"])
        if not re.fullmatch(r"[0-9]+", id_text):
            continue
        code = int(id_text)
        if code not in geography:
            continue
        if clean_text(record["Provinsi"]).upper() != "SUMATERA BARAT":
            raise Stage2aRetrievalError(
                f"target ID Kabupaten {code} returned non-Sumbar province {record['Provinsi']!r}"
            )

        impact: dict[str, dict[str, Any]] = {}
        for field in impact_fields:
            state, number = impact_cell_state(record[field])
            impact[field] = {"state": state, "value": number}
            if state == "not_reported_or_missing":
                diagnostics["blank_impact_cells"] += 1
            elif state == "explicit_reported_zero":
                diagnostics["explicit_zero_impact_cells"] += 1
            else:
                diagnostics["positive_impact_cells"] += 1

        source_event_id = clean_text(record["Kode Identitas Bencana"])
        if source_event_id == "":
            diagnostics["blank_source_event_ids"] += 1
        fingerprint = source_row_fingerprint(headers, row, contract)
        retained.append(
            {
                "query_event_type": query_event_type,
                "source_row_index": source_index,
                "geography_id": geography[code]["geography_id"],
                "geography_name_locked": geography[code]["geography_name"],
                "source_id_kabupaten": code,
                "source_kabupaten": clean_text(record["Kabupaten"]),
                "source_provinsi": clean_text(record["Provinsi"]),
                "source_event_date": iso_date,
                "source_event_type": source_event_type,
                "source_event_id": source_event_id or None,
                "source_location": clean_text(record["Lokasi"]),
                "fallback_row_fingerprint_sha256": fingerprint,
                "impact": impact,
                "diagnostic_only": True,
                "automatic_duplicate_collapse_authorized": False,
                "impact_aggregation_authorized": False,
            }
        )

    diagnostics["retained_sumbar_row_count"] = len(retained)
    return retained, diagnostics


def write_rows(rows: list[dict[str, Any]]) -> None:
    ROWS_PATH.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(
        rows,
        key=lambda row: (
            row["query_event_type"],
            row["source_event_date"],
            row["source_id_kabupaten"],
            row["fallback_row_fingerprint_sha256"],
            row["source_row_index"],
        ),
    )
    with ROWS_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        for row in ordered:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def build(mode: str) -> dict[str, Any]:
    try:
        contract = load_contract()
    except EventImpactContractError as exc:
        raise Stage2aRetrievalError(str(exc)) from exc
    geography = load_geography_contract()
    if int(contract["target_regime"]["geography_count"]) != len(geography):
        raise Stage2aRetrievalError("Stage 2 contract geography count drift")

    all_rows: list[dict[str, Any]] = []
    retrievals: list[dict[str, Any]] = []
    combined_profile = Counter()

    for event_type in contract["target_regime"]["event_types"]:
        html_path, sidecar_path, sidecar, body = acquire_or_load(
            contract=contract,
            event_type=event_type,
            mode=mode,
        )
        parser = parse_html(body)
        validate_parser_surface(parser, contract, event_type)
        rows, profile = parse_target_rows(
            parser=parser,
            contract=contract,
            geography=geography,
            query_event_type=event_type,
        )
        all_rows.extend(rows)
        combined_profile.update(profile)
        retrievals.append(
            {
                "event_type": event_type,
                "raw_html_path": rel(html_path),
                "raw_html_sha256": sha256_path(html_path),
                "raw_html_bytes": html_path.stat().st_size,
                "request_sidecar_path": rel(sidecar_path),
                "request_sidecar_sha256": sha256_path(sidecar_path),
                "source_row_count": profile["source_row_count"],
                "retained_sumbar_row_count": profile["retained_sumbar_row_count"],
            }
        )

    write_rows(all_rows)
    fingerprints = [row["fallback_row_fingerprint_sha256"] for row in all_rows]
    fingerprint_counts = Counter(fingerprints)
    duplicate_fingerprints = sorted(key for key, count in fingerprint_counts.items() if count > 1)
    nonblank_ids = [row["source_event_id"] for row in all_rows if row["source_event_id"]]
    source_id_counts = Counter(nonblank_ids)
    duplicate_source_ids = sorted(key for key, count in source_id_counts.items() if count > 1)
    represented_geographies = sorted({row["geography_id"] for row in all_rows})

    manifest = {
        "schema": "ranah-observatory/milestone26-stage2a-event-impact-retrieval/v1",
        "milestone": 26,
        "stage": "2a_live_retrieval_qualification",
        "mode_last_built": mode,
        "target_regime": contract["target_regime"],
        "geography_contract_source": rel(M16_FRAME),
        "geography_contract_source_sha256": sha256_path(M16_FRAME),
        "retrievals": retrievals,
        "retained_row_count": len(all_rows),
        "represented_geography_count": len(represented_geographies),
        "represented_geography_ids": represented_geographies,
        "impact_cell_profile": {
            "blank_not_reported_or_missing": combined_profile["blank_impact_cells"],
            "explicit_reported_zero": combined_profile["explicit_zero_impact_cells"],
            "reported_positive_count": combined_profile["positive_impact_cells"],
        },
        "blank_source_event_id_count": combined_profile["blank_source_event_ids"],
        "exact_duplicate_fingerprint_count": sum(count - 1 for count in fingerprint_counts.values() if count > 1),
        "exact_duplicate_fingerprints": duplicate_fingerprints,
        "duplicate_nonblank_source_event_id_count": sum(count - 1 for count in source_id_counts.values() if count > 1),
        "duplicate_nonblank_source_event_ids": duplicate_source_ids,
        "row_diagnostics": {
            "path": rel(ROWS_PATH),
            "sha256": sha256_path(ROWS_PATH),
        },
        "exact_table_schema_required": True,
        "target_date_range_validation_passed": True,
        "source_event_type_validation_passed": True,
        "geography_id_mapping_passed_for_all_retained_rows": True,
        "impact_cell_type_profile_completed": True,
        "blank_interpreted_as_zero": False,
        "automatic_duplicate_collapse_performed": False,
        "duplicate_resolution_decision": "pending_explicit_stage2b_decision",
        "stage2b_promotion_authorized": False,
        "impact_aggregation_performed": False,
        "historical_boundary_reconstruction_performed": False,
        "cross_component_temporal_aggregation_performed": False,
        "risk_synthesis_authorized": False,
        "statistical_model_fit": False,
        "causal_claim_created": False,
        "monetary_loss_inferred": False,
        "monetary_wasted_potential_estimated": False,
    }
    write_json(MANIFEST_PATH, manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Qualify BNPB 2024 flood/landslide event-impact retrieval without aggregation")
    parser.add_argument("--mode", choices=("live", "offline"), default="offline")
    args = parser.parse_args()
    try:
        payload = build(args.mode)
    except (OSError, ValueError, json.JSONDecodeError, Stage2aRetrievalError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "mode": args.mode,
        "retained_row_count": payload["retained_row_count"],
        "represented_geography_count": payload["represented_geography_count"],
        "exact_duplicate_fingerprint_count": payload["exact_duplicate_fingerprint_count"],
        "stage2b_promotion_authorized": payload["stage2b_promotion_authorized"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
