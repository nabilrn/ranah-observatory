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
GEO_CONTRACT_PATH = ROOT / "data/manifests/milestone26_stage2a_geography_crosswalk_contract.json"
CROSSWALK_PATH = ROOT / "data/registries/bnpb_geography_map.csv"
M16_FRAME_PATH = ROOT / "data/analysis/engine/spatial_climate_risk_v1/m16-spatial-component-frame.csv"
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


def normalize_identity_name(value: str) -> str:
    text = " ".join(value.strip().upper().split())
    text = re.sub(r"^KAB\.\s*", "", text)
    text = re.sub(r"^KABUPATEN\s+", "", text)
    text = re.sub(r"^KOTA\s+", "", text)
    return text


def slug_event_type(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def load_geography_mapping() -> tuple[dict[int, dict[str, str]], dict[str, str]]:
    cfg = json.loads(GEO_CONTRACT_PATH.read_text(encoding="utf-8"))
    if cfg.get("schema") != "ranah-observatory/milestone26-stage2a-geography-crosswalk-contract/v1":
        raise Stage2aRetrievalError("unexpected Stage 2a geography contract schema")
    if cfg.get("locked_before_target_period_live_retrieval") is not True:
        raise Stage2aRetrievalError("Stage 2a geography contract was not locked before live retrieval")
    if cfg.get("source_id_is_canonical_bps_code") is not False:
        raise Stage2aRetrievalError("source ID Kabupaten must not be treated as canonical BPS code")
    for flag in (
        "historical_boundary_reconstruction_authorized",
        "automatic_duplicate_collapse_authorized",
        "impact_aggregation_authorized",
        "blank_impact_cell_as_zero_authorized",
        "cross_component_temporal_aggregation_authorized",
        "risk_synthesis_authorized",
        "statistical_model_fit_authorized",
        "causal_claim_authorized",
        "monetary_loss_inference_authorized",
        "monetary_wasted_potential_estimate_authorized",
    ):
        if cfg.get(flag) is not False:
            raise Stage2aRetrievalError(f"unexpected Stage 2a authorization: {flag}")

    cross_cfg = cfg["qualified_crosswalk"]
    with CROSSWALK_PATH.open(newline="", encoding="utf-8") as handle:
        cross_rows = list(csv.DictReader(handle))
    if len(cross_rows) != int(cross_cfg["expected_row_count"]):
        raise Stage2aRetrievalError("BNPB geography crosswalk row-count drift")

    mapping: dict[int, dict[str, str]] = {}
    for row in cross_rows:
        if row["mapping_status"] != cross_cfg["required_mapping_status"]:
            raise Stage2aRetrievalError(f"unqualified BNPB geography mapping: {row}")
        if row["source_system"] != cross_cfg["required_source_system"]:
            raise Stage2aRetrievalError(f"unexpected BNPB geography source system: {row}")
        year = int(cross_cfg["required_applicable_year"])
        if not int(row["applicable_start_year"]) <= year <= int(row["applicable_end_year"]):
            raise Stage2aRetrievalError(f"BNPB geography mapping does not cover {year}: {row}")
        code = int(row["source_code_normalized"])
        if code in mapping:
            raise Stage2aRetrievalError(f"duplicate BNPB source geography code: {code}")
        mapping[code] = row

    with M16_FRAME_PATH.open(newline="", encoding="utf-8") as handle:
        m16_rows = list(csv.DictReader(handle))
    if len(m16_rows) != 19:
        raise Stage2aRetrievalError("M16 current geography frame count drift")
    canonical_names = {row["geography_id"]: row["geography_name"] for row in m16_rows}
    if len(canonical_names) != 19:
        raise Stage2aRetrievalError("M16 canonical geography ids are not unique")
    if {row["spatial_frame"] for row in m16_rows} != {cfg["canonical_frame"]["required_spatial_frame"]}:
        raise Stage2aRetrievalError("M16 canonical spatial frame drift")
    if {row["canonical_geography_id"] for row in mapping.values()} != set(canonical_names):
        raise Stage2aRetrievalError("qualified BNPB crosswalk canonical set does not match M16 current frame")
    return mapping, canonical_names


def parse_source_date(value: str) -> str:
    text = clean_text(value)
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    raise Stage2aRetrievalError(f"unparseable source event date: {value!r}")


def request_html(url: str, form: dict[str, str], retries: int = 3, timeout: float = 120.0) -> tuple[str, str, bytes]:
    data = urllib.parse.urlencode(form).encode("utf-8")
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
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
        except (urllib.error.URLError, TimeoutError, Stage2aRetrievalError) as exc:
            last_error = exc
            if attempt >= retries:
                break
            time.sleep(2**attempt)
    raise Stage2aRetrievalError(f"request failed after retries: {url}") from last_error


def build_form(contract: dict[str, Any], event_type: str) -> dict[str, str]:
    params = contract["official_source"]["form_parameters"]
    target = contract["target_regime"]
    return {
        params["event_type"]: event_type,
        params["start_date"]: target["start_date"],
        params["end_date"]: target["end_date"],
        params["submit"]: contract["official_source"]["submit_value"],
    }


def acquire_or_load(contract: dict[str, Any], event_type: str, mode: str) -> tuple[Path, Path, bytes]:
    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    slug = slug_event_type(event_type)
    html_path = RAW_ROOT / f"{slug}.html"
    sidecar_path = RAW_ROOT / f"{slug}.request.json"
    source_url = contract["official_source"]["url"]
    form = build_form(contract, event_type)

    if mode == "live":
        final_url, content_type, body = request_html(source_url, form)
        if "html" not in content_type.casefold():
            raise Stage2aRetrievalError(f"unexpected content type for {event_type}: {content_type}")
        html_path.write_bytes(body)
        write_json(sidecar_path, {
            "schema": "ranah-observatory/milestone26-stage2a-event-impact-request/v2",
            "source_url": source_url,
            "final_url": final_url,
            "method": "POST",
            "content_type": content_type,
            "event_type": event_type,
            "form": form,
            "response_path": rel(html_path),
            "response_sha256": sha256_bytes(body),
            "response_bytes": len(body),
            "stage2_contract_path": "data/manifests/milestone26_stage2_event_impact_contract.json",
            "stage2a_geography_contract_path": rel(GEO_CONTRACT_PATH),
            "qualified_crosswalk_path": rel(CROSSWALK_PATH),
            "qualified_crosswalk_sha256": sha256_path(CROSSWALK_PATH),
        })
    else:
        if not html_path.exists() or not sidecar_path.exists():
            raise Stage2aRetrievalError(f"offline Stage 2a evidence missing for {event_type}")
        body = html_path.read_bytes()
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        if sidecar.get("schema") != "ranah-observatory/milestone26-stage2a-event-impact-request/v2":
            raise Stage2aRetrievalError(f"unexpected frozen Stage 2a request schema for {event_type}")
        if sidecar.get("source_url") != source_url or sidecar.get("method") != "POST":
            raise Stage2aRetrievalError(f"frozen request endpoint/method drift for {event_type}")
        if sidecar.get("event_type") != event_type or sidecar.get("form") != form:
            raise Stage2aRetrievalError(f"frozen request form drift for {event_type}")
        if sidecar.get("qualified_crosswalk_sha256") != sha256_path(CROSSWALK_PATH):
            raise Stage2aRetrievalError(f"qualified crosswalk checksum drift for {event_type}")
        if sidecar.get("response_sha256") != sha256_path(html_path):
            raise Stage2aRetrievalError(f"raw HTML checksum mismatch for {event_type}")
        if int(sidecar.get("response_bytes", -1)) != html_path.stat().st_size:
            raise Stage2aRetrievalError(f"raw HTML byte-count mismatch for {event_type}")
    return html_path, sidecar_path, body


def validate_table(parser: Any, contract: dict[str, Any], event_type: str) -> None:
    if parser.headers != contract["expected_table_columns"]:
        raise Stage2aRetrievalError(f"event-impact table header drift for {event_type}: {parser.headers}")
    if any(len(row) != len(parser.headers) for row in parser.rows):
        raise Stage2aRetrievalError(f"malformed event-impact table row for {event_type}")


def parse_rows(
    parser: Any,
    contract: dict[str, Any],
    event_type: str,
    mapping: dict[int, dict[str, str]],
    canonical_names: dict[str, str],
) -> tuple[list[dict[str, Any]], Counter[str]]:
    headers = contract["expected_table_columns"]
    target_year = int(contract["target_regime"]["year"])
    profile: Counter[str] = Counter()
    profile["source_row_count"] = len(parser.rows)
    retained: list[dict[str, Any]] = []

    for source_index, row in enumerate(parser.rows, start=1):
        record = dict(zip(headers, row, strict=True))
        source_event_type = clean_text(record["Kejadian"]).upper()
        if source_event_type != event_type.upper():
            raise Stage2aRetrievalError(
                f"event-type server filter drift: queried {event_type!r}, received {source_event_type!r}"
            )
        iso_date = parse_source_date(record["Tanggal Kejadian"])
        if int(iso_date[:4]) != target_year:
            raise Stage2aRetrievalError(f"date-range server filter drift: received {iso_date}")

        province = clean_text(record["Provinsi"]).upper()
        id_text = clean_text(record["ID Kabupaten"])
        if province != "SUMATERA BARAT":
            if re.fullmatch(r"[0-9]+", id_text) and int(id_text) in mapping:
                raise Stage2aRetrievalError(f"known Sumbar BNPB source code {id_text} returned province {province!r}")
            continue

        profile["sumbar_source_rows"] += 1
        if not re.fullmatch(r"[0-9]+", id_text):
            raise Stage2aRetrievalError(f"Sumbar row has nonnumeric ID Kabupaten: {id_text!r}")
        source_code = int(id_text)
        cross = mapping.get(source_code)
        if cross is None:
            raise Stage2aRetrievalError(f"unmapped Sumbar BNPB ID Kabupaten: {source_code}")
        source_name = normalize_identity_name(clean_text(record["Kabupaten"]))
        expected_name = normalize_identity_name(cross["source_name_expected"])
        if source_name != expected_name:
            raise Stage2aRetrievalError(
                f"BNPB source-name mismatch for {source_code}: {source_name!r} != {expected_name!r}"
            )
        canonical_id = cross["canonical_geography_id"]
        if canonical_id not in canonical_names:
            raise Stage2aRetrievalError(f"crosswalk produced non-M16 canonical id: {canonical_id}")

        impact: dict[str, dict[str, Any]] = {}
        for field in contract["impact_fields"]:
            try:
                state, number = impact_cell_state(record[field])
            except EventImpactContractError as exc:
                raise Stage2aRetrievalError(str(exc)) from exc
            impact[field] = {"state": state, "value": number}
            if state == "not_reported_or_missing":
                profile["blank_impact_cells"] += 1
            elif state == "explicit_reported_zero":
                profile["explicit_zero_impact_cells"] += 1
            else:
                profile["positive_impact_cells"] += 1

        source_event_id = clean_text(record["Kode Identitas Bencana"])
        if source_event_id == "":
            profile["blank_source_event_ids"] += 1
        fingerprint = source_row_fingerprint(headers, row, contract)
        retained.append({
            "query_event_type": event_type,
            "source_row_index": source_index,
            "source_id_kabupaten": source_code,
            "source_kabupaten": clean_text(record["Kabupaten"]),
            "source_provinsi": clean_text(record["Provinsi"]),
            "canonical_geography_id": canonical_id,
            "canonical_geography_name": canonical_names[canonical_id],
            "source_event_date": iso_date,
            "source_event_type": source_event_type,
            "source_event_id": source_event_id or None,
            "source_location": clean_text(record["Lokasi"]),
            "fallback_row_fingerprint_sha256": fingerprint,
            "impact": impact,
            "diagnostic_only": True,
            "source_id_assumed_canonical": False,
            "automatic_duplicate_collapse_authorized": False,
            "impact_aggregation_authorized": False,
        })
    profile["retained_sumbar_rows"] = len(retained)
    return retained, profile


def write_rows(rows: list[dict[str, Any]]) -> None:
    ordered = sorted(rows, key=lambda row: (
        row["query_event_type"], row["source_event_date"], row["canonical_geography_id"],
        row["fallback_row_fingerprint_sha256"], row["source_row_index"],
    ))
    ROWS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with ROWS_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        for row in ordered:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def build(mode: str) -> dict[str, Any]:
    contract = load_contract()
    mapping, canonical_names = load_geography_mapping()
    if int(contract["target_regime"]["year"]) != 2024:
        raise Stage2aRetrievalError("Stage 2a geography crosswalk is locked only for target year 2024")

    all_rows: list[dict[str, Any]] = []
    retrievals: list[dict[str, Any]] = []
    totals: Counter[str] = Counter()
    for event_type in contract["target_regime"]["event_types"]:
        html_path, sidecar_path, body = acquire_or_load(contract, event_type, mode)
        parser = parse_html(body)
        validate_table(parser, contract, event_type)
        rows, profile = parse_rows(parser, contract, event_type, mapping, canonical_names)
        all_rows.extend(rows)
        totals.update(profile)
        retrievals.append({
            "event_type": event_type,
            "raw_html_path": rel(html_path),
            "raw_html_sha256": sha256_path(html_path),
            "raw_html_bytes": html_path.stat().st_size,
            "request_sidecar_path": rel(sidecar_path),
            "request_sidecar_sha256": sha256_path(sidecar_path),
            "source_row_count": profile["source_row_count"],
            "retained_sumbar_row_count": profile["retained_sumbar_rows"],
        })

    write_rows(all_rows)
    fingerprints = [row["fallback_row_fingerprint_sha256"] for row in all_rows]
    fingerprint_counts = Counter(fingerprints)
    nonblank_ids = [row["source_event_id"] for row in all_rows if row["source_event_id"]]
    source_id_counts = Counter(nonblank_ids)
    represented = sorted({row["canonical_geography_id"] for row in all_rows})

    manifest = {
        "schema": "ranah-observatory/milestone26-stage2a-event-impact-retrieval/v2",
        "milestone": 26,
        "stage": "2a_live_retrieval_qualification",
        "target_regime": contract["target_regime"],
        "stage2a_geography_contract": {"path": rel(GEO_CONTRACT_PATH), "sha256": sha256_path(GEO_CONTRACT_PATH)},
        "qualified_bnpb_crosswalk": {"path": rel(CROSSWALK_PATH), "sha256": sha256_path(CROSSWALK_PATH)},
        "canonical_frame": {"path": rel(M16_FRAME_PATH), "sha256": sha256_path(M16_FRAME_PATH)},
        "source_id_assumed_canonical": False,
        "retrievals": retrievals,
        "retained_row_count": len(all_rows),
        "represented_geography_count": len(represented),
        "represented_geography_ids": represented,
        "impact_cell_profile": {
            "blank_not_reported_or_missing": totals["blank_impact_cells"],
            "explicit_reported_zero": totals["explicit_zero_impact_cells"],
            "reported_positive_count": totals["positive_impact_cells"],
        },
        "blank_source_event_id_count": totals["blank_source_event_ids"],
        "exact_duplicate_fingerprint_count": sum(count - 1 for count in fingerprint_counts.values() if count > 1),
        "exact_duplicate_fingerprints": sorted(key for key, count in fingerprint_counts.items() if count > 1),
        "duplicate_nonblank_source_event_id_count": sum(count - 1 for count in source_id_counts.values() if count > 1),
        "duplicate_nonblank_source_event_ids": sorted(key for key, count in source_id_counts.items() if count > 1),
        "row_diagnostics": {"path": rel(ROWS_PATH), "sha256": sha256_path(ROWS_PATH)},
        "exact_table_schema_required": True,
        "target_date_range_validation_passed": True,
        "source_event_type_validation_passed": True,
        "all_retained_sumbar_rows_crosswalked": True,
        "source_name_crosscheck_passed": True,
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
    parser = argparse.ArgumentParser(description="Qualify 2024 BNPB flood/landslide impact retrieval with the prequalified BNPB geography crosswalk")
    parser.add_argument("--mode", choices=("live", "offline"), default="offline")
    args = parser.parse_args()
    try:
        payload = build(args.mode)
    except (OSError, ValueError, json.JSONDecodeError, EventImpactContractError, Stage2aRetrievalError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "mode": args.mode,
        "retained_row_count": payload["retained_row_count"],
        "represented_geography_count": payload["represented_geography_count"],
        "exact_duplicate_fingerprint_count": payload["exact_duplicate_fingerprint_count"],
        "stage2b_promotion_authorized": payload["stage2b_promotion_authorized"]
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
