#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Mapping

from bps_client import BPSApiError, BPSClient
from probe_bps_comparative_panel import as_list, geography_summary, label_of, period_candidates, select_probe_period, value_of

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "manifests" / "milestone7_bps_feature_discovery.json"
DOMAIN = "0000"

FEATURE_GROUPS: dict[str, tuple[str, ...]] = {
    "human_capital_schooling": (
        "rata-rata lama sekolah",
        "rata rata lama sekolah",
        "mean years of schooling",
    ),
    "human_capital_expected_schooling": (
        "harapan lama sekolah",
        "expected years of schooling",
    ),
    "health_life_expectancy": (
        "umur harapan hidup",
        "angka harapan hidup",
        "life expectancy",
    ),
    "population_density": (
        "kepadatan penduduk",
        "population density",
    ),
    "dependency_ratio": (
        "rasio ketergantungan",
        "dependency ratio",
    ),
    "urbanization": (
        "penduduk perkotaan",
        "urban population",
        "perkotaan",
    ),
    "digital_connectivity": (
        "akses internet",
        "mengakses internet",
        "internet",
    ),
    "electricity_access": (
        "sumber penerangan listrik",
        "akses listrik",
        "listrik pln",
        "electricity",
    ),
    "road_connectivity": (
        "panjang jalan",
        "road length",
    ),
    "sector_structure": (
        "produk domestik regional bruto menurut lapangan usaha",
        "pdrb menurut lapangan usaha",
        "lapangan usaha",
    ),
}


def text_of(row: Mapping[str, Any]) -> str:
    parts = []
    for key in ("label", "title", "var", "name", "note", "subject", "subj"):
        value = row.get(key)
        if value not in (None, ""):
            parts.append(str(value))
    return " ".join(parts).strip()


def var_id_of(row: Mapping[str, Any]) -> int | None:
    for key in ("var_id", "val", "id", "var"):
        raw = row.get(key)
        if raw in (None, ""):
            continue
        try:
            return int(str(raw).strip())
        except ValueError:
            continue
    return None


def normalize(value: str) -> str:
    value = value.casefold()
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def matched_groups(text: str) -> list[str]:
    norm = normalize(text)
    out = []
    for group, needles in FEATURE_GROUPS.items():
        if any(normalize(needle) in norm for needle in needles):
            out.append(group)
    return out


def probe(client: BPSClient, row: Mapping[str, Any], groups: list[str]) -> dict[str, Any]:
    var_id = var_id_of(row)
    result: dict[str, Any] = {
        "bps_var_id": var_id,
        "feature_groups": groups,
        "variable_metadata": dict(row),
        "variable_text": text_of(row),
    }
    if var_id is None:
        result["probe_status"] = "hold_missing_var_id"
        return result
    try:
        periods = period_candidates(client.list_periods(domain=DOMAIN, var=var_id))
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
        source_title = str(var_meta[0].get("label", "") if var_meta else "").strip()
        source_unit = str(var_meta[0].get("unit", "") if var_meta else "").strip()
        source_note = str(var_meta[0].get("note", "") if var_meta else "").strip()
        result.update(
            {
                "source_title": source_title,
                "source_unit": source_unit,
                "source_note": source_note,
                "geography": geography,
                "turvar": [{"value": value_of(item), "label": label_of(item)} for item in turvar],
                "turtahun": [{"value": value_of(item), "label": label_of(item)} for item in turtahun],
                "datacontent_count": len(datacontent) if isinstance(datacontent, Mapping) else 0,
            }
        )
        is_province = "provinsi" in geography["labelvervar"].casefold()
        has_38 = geography["non_aggregate_geography_count"] == 38
        has_sumbar = bool(geography["west_sumatra_entries"])
        has_data = isinstance(datacontent, Mapping) and len(datacontent) > 0
        result["probe_status"] = (
            "current_38_province_candidate"
            if is_province and has_38 and has_sumbar and has_data
            else "hold_structure"
        )
        result["structure_checks"] = {
            "vertical_is_province": is_province,
            "exactly_38_nonaggregate_geographies": has_38,
            "west_sumatra_present": has_sumbar,
            "datacontent_present": has_data,
        }
    except (BPSApiError, ValueError, TypeError) as exc:
        result["probe_status"] = "probe_error"
        result["error"] = str(exc)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover national BPS structural feature candidates for Milestone 7.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-probes", type=int, default=80)
    args = parser.parse_args()

    api_key = os.environ.get("BPS_API_KEY", "").strip()
    if not api_key:
        print("error: BPS_API_KEY is required", file=sys.stderr)
        return 2
    client = BPSClient(api_key, retries=3, retry_backoff_seconds=1.0)
    try:
        variables = client.list_variables(domain=DOMAIN)
    except BPSApiError as exc:
        print(f"error: unable to list national BPS variables: {exc}", file=sys.stderr)
        return 2

    matches: list[tuple[Mapping[str, Any], list[str]]] = []
    seen: set[int] = set()
    for row in variables:
        groups = matched_groups(text_of(row))
        var_id = var_id_of(row)
        if not groups or var_id is None or var_id in seen:
            continue
        seen.add(var_id)
        matches.append((row, groups))
    matches.sort(key=lambda item: (item[1][0], var_id_of(item[0]) or 0))
    selected = matches[: max(0, args.max_probes)]
    results = [probe(client, row, groups) for row, groups in selected]
    report = {
        "schema": "ranah-observatory/milestone7-bps-feature-discovery/v1",
        "domain": DOMAIN,
        "source_authority": "Badan Pusat Statistik (BPS-Statistics Indonesia)",
        "variable_count_scanned": len(variables),
        "keyword_match_count": len(matches),
        "probed_count": len(results),
        "current_38_province_candidate_count": sum(
            row.get("probe_status") == "current_38_province_candidate" for row in results
        ),
        "feature_groups": {key: list(value) for key, value in FEATURE_GROUPS.items()},
        "results": results,
        "interpretation": "Discovery only. A structural match does not qualify semantics, period, denominator, or model use.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if results else 3


if __name__ == "__main__":
    raise SystemExit(main())
