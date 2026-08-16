#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping

from bps_client import BPSApiError, BPSClient

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "data" / "registries" / "bps_comparative_panel_candidates.csv"
DEFAULT_OUTPUT = ROOT / "data" / "manifests" / "milestone5_bps_comparative_probe.json"
DOMAIN = "0000"
AGGREGATE_LABELS = {"indonesia", "jumlah", "total"}


def read_registry(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def as_list(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def period_candidates(rows: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    parsed: list[dict[str, Any]] = []
    for row in rows:
        raw_id = row.get("th_id", row.get("val", row.get("id")))
        raw_label = row.get("th", row.get("label", row.get("tahun")))
        label = str(raw_label or "").strip()
        if not label:
            continue
        try:
            year = int(label)
        except ValueError:
            year = None
        parsed.append({"period_id": raw_id, "label": label, "year": year})
    parsed.sort(key=lambda item: (item["year"] is None, item["year"] or -1, item["label"]))
    return parsed


def select_probe_period(periods: list[dict[str, Any]]) -> dict[str, Any] | None:
    annual = [item for item in periods if item["year"] is not None]
    preferred = [item for item in annual if 2018 <= int(item["year"]) <= 2025]
    if preferred:
        return max(preferred, key=lambda item: int(item["year"]))
    if annual:
        return max(annual, key=lambda item: int(item["year"]))
    return periods[-1] if periods else None


def label_of(item: Mapping[str, Any]) -> str:
    raw = item.get("label", item.get("vervar", item.get("name", "")))
    return "" if raw is None else str(raw).strip()


def value_of(item: Mapping[str, Any]) -> str:
    raw = item.get("val", item.get("vervar_id", item.get("id", "")))
    return "" if raw is None else str(raw).strip()


def geography_summary(payload: Mapping[str, Any]) -> dict[str, Any]:
    labelvervar = str(payload.get("labelvervar", "") or "").strip()
    rows = as_list(payload.get("vervar"))
    geographies: list[dict[str, str]] = []
    for item in rows:
        label = label_of(item)
        value = value_of(item)
        if not label:
            continue
        geographies.append({"value": value, "label": label})
    non_aggregate = [
        item
        for item in geographies
        if item["label"].casefold() not in AGGREGATE_LABELS and item["value"] != "9999"
    ]
    west_sumatra = [item for item in geographies if "sumatera barat" in item["label"].casefold()]
    return {
        "labelvervar": labelvervar,
        "geography_count_including_aggregates": len(geographies),
        "non_aggregate_geography_count": len(non_aggregate),
        "west_sumatra_entries": west_sumatra,
        "geographies": geographies,
    }


def semantic_digest(payload: Mapping[str, Any]) -> str:
    selected = {
        "var": payload.get("var"),
        "turvar": payload.get("turvar"),
        "labelvervar": payload.get("labelvervar"),
        "vervar": payload.get("vervar"),
        "tahun": payload.get("tahun"),
        "turtahun": payload.get("turtahun"),
        "metadata": payload.get("metadata"),
        "datacontent": payload.get("datacontent"),
    }
    encoded = json.dumps(selected, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def probe_one(client: BPSClient, row: dict[str, str]) -> dict[str, Any]:
    var_id = int(row["bps_var_id"])
    result: dict[str, Any] = {
        "indicator_id": row["indicator_id"],
        "bps_var_id": var_id,
        "candidate_role": row["candidate_role"],
        "canonical_unit": row["canonical_unit"],
        "expected_concept": row["expected_concept"],
    }
    try:
        periods_raw = client.list_periods(domain=DOMAIN, var=var_id)
        periods = period_candidates(periods_raw)
        selected = select_probe_period(periods)
        result["periods"] = periods
        result["selected_probe_period"] = selected
        if selected is None or selected.get("period_id") in (None, ""):
            result["probe_status"] = "hold_no_period"
            return result

        payload = client.get_dynamic_data(domain=DOMAIN, var=var_id, th=selected["period_id"])
        geography = geography_summary(payload)
        var_meta = as_list(payload.get("var"))
        turvar = as_list(payload.get("turvar"))
        turtahun = as_list(payload.get("turtahun"))
        datacontent = payload.get("datacontent")
        data_count = len(datacontent) if isinstance(datacontent, Mapping) else 0
        unit = str(var_meta[0].get("unit", "") if var_meta else "").strip()
        title = str(var_meta[0].get("label", "") if var_meta else "").strip()
        notes = str(var_meta[0].get("note", "") if var_meta else "").strip()

        result.update(
            {
                "source_title": title,
                "source_unit": unit,
                "source_note": notes,
                "geography": geography,
                "turvar": [{"value": value_of(item), "label": label_of(item)} for item in turvar],
                "turtahun": [{"value": value_of(item), "label": label_of(item)} for item in turtahun],
                "datacontent_type": type(datacontent).__name__,
                "datacontent_count": data_count,
                "semantic_sha256": semantic_digest(payload),
            }
        )

        is_province = "provinsi" in geography["labelvervar"].casefold()
        enough_regions = geography["non_aggregate_geography_count"] >= 30
        has_west_sumatra = bool(geography["west_sumatra_entries"])
        has_data = isinstance(datacontent, Mapping) and data_count > 0
        if is_province and enough_regions and has_west_sumatra and has_data:
            result["probe_status"] = "province_panel_candidate"
        else:
            reasons: list[str] = []
            if not is_province:
                reasons.append("vertical_variable_not_province")
            if not enough_regions:
                reasons.append("fewer_than_30_nonaggregate_geographies")
            if not has_west_sumatra:
                reasons.append("west_sumatra_missing")
            if not has_data:
                reasons.append("datacontent_unavailable_or_empty")
            result["probe_status"] = "hold_structure"
            result["hold_reasons"] = reasons
    except (BPSApiError, ValueError, TypeError) as exc:
        result["probe_status"] = "probe_error"
        result["error"] = str(exc)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe national-domain BPS candidates for Milestone 5 province-panel suitability.")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    api_key = os.environ.get("BPS_API_KEY", "").strip()
    if not api_key:
        print("error: BPS_API_KEY is required", file=sys.stderr)
        return 2

    rows = read_registry(args.registry)
    client = BPSClient(api_key, retries=3, retry_backoff_seconds=1.0)
    results = [probe_one(client, row) for row in rows]
    candidate_count = sum(item.get("probe_status") == "province_panel_candidate" for item in results)
    report = {
        "schema": "ranah-observatory/milestone5-bps-comparative-probe/v1",
        "domain": DOMAIN,
        "source_authority": "Badan Pusat Statistik (BPS-Statistics Indonesia)",
        "source_api": "https://webapi.bps.go.id/v1/api/list",
        "candidate_count": len(results),
        "province_panel_candidate_count": candidate_count,
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if candidate_count > 0 else 3


if __name__ == "__main__":
    raise SystemExit(main())
