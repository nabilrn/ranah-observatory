#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping

from bps_client import BPSApiError, BPSClient
from probe_bps_comparative_panel import as_list, geography_summary, label_of, period_candidates, select_probe_period, value_of

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "manifests" / "milestone7_bps_feature_discovery.json"
DOMAIN = "0000"

# IDs are preregistered from BPS variables already encountered in Ranah Observatory's
# Sumatera Barat source inventory. National-domain suitability is NOT assumed; this
# script explicitly probes domain 0000 and holds any ID whose semantics/geography fail.
KNOWN_CANDIDATES: tuple[dict[str, Any], ...] = (
    {"bps_var_id": 361, "feature_groups": ["human_capital_expected_schooling"], "origin": "bps_live_candidates: expected_years_schooling"},
    {"bps_var_id": 363, "feature_groups": ["human_capital_schooling"], "origin": "bps_live_candidates: mean_years_schooling"},
    {"bps_var_id": 752, "feature_groups": ["health_life_expectancy"], "origin": "bps_live_candidates: life_expectancy LF-SP2020"},
    {"bps_var_id": 512, "feature_groups": ["urbanization"], "origin": "bps_live_candidates: urban_population_share"},
    {"bps_var_id": 320, "feature_groups": ["digital_connectivity"], "origin": "bps_live_candidates: internet_access"},
    {"bps_var_id": 282, "feature_groups": ["sector_structure"], "origin": "bps_expansion_series: PDRB ADHB by industry"},
    {"bps_var_id": 755, "feature_groups": ["population_scale"], "origin": "bps_live_candidates: population projection 2020-2035"},
)


def probe(client: BPSClient, candidate: Mapping[str, Any]) -> dict[str, Any]:
    var_id = int(candidate["bps_var_id"])
    result: dict[str, Any] = {
        "bps_var_id": var_id,
        "feature_groups": list(candidate["feature_groups"]),
        "candidate_origin": str(candidate["origin"]),
    }
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
        result["structure_checks"] = {
            "vertical_is_province": is_province,
            "exactly_38_nonaggregate_geographies": has_38,
            "west_sumatra_present": has_sumbar,
            "datacontent_present": has_data,
        }
        result["probe_status"] = (
            "current_38_province_candidate"
            if is_province and has_38 and has_sumbar and has_data
            else "hold_structure"
        )
    except (BPSApiError, ValueError, TypeError) as exc:
        result["probe_status"] = "probe_error"
        result["error"] = str(exc)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe preregistered national BPS structural feature candidates for Milestone 7.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    api_key = os.environ.get("BPS_API_KEY", "").strip()
    if not api_key:
        print("error: BPS_API_KEY is required", file=sys.stderr)
        return 2
    client = BPSClient(api_key, retries=3, retry_backoff_seconds=1.0)
    results = [probe(client, candidate) for candidate in KNOWN_CANDIDATES]
    report = {
        "schema": "ranah-observatory/milestone7-bps-feature-discovery/v2",
        "domain": DOMAIN,
        "source_authority": "Badan Pusat Statistik (BPS-Statistics Indonesia)",
        "candidate_count": len(results),
        "current_38_province_candidate_count": sum(
            row.get("probe_status") == "current_38_province_candidate" for row in results
        ),
        "results": results,
        "interpretation": "Discovery only. Candidate IDs come from previously encountered BPS variables; national-domain structural compatibility does not by itself qualify semantics, selector, period, or model use.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
