#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from bps_client import BPSApiError, BPSClient
from harvest_bps_series import harvest_series
from normalize_bps_dynamic import BPSDynamicNormalizationError

# Bounded, high-value candidates for Milestone 4. These are probes only: a
# successful transport result never implies canonical qualification.
CANDIDATES: tuple[tuple[int, str], ...] = (
    (512, "urban_population_share"),
    (883, "net_migration_rate"),
    (877, "infant_mortality_rate"),
    (320, "internet_access"),
    (427, "local_government_revenue_expenditure"),
    (555, "road_condition_and_length"),
    (774, "neet_rate"),
    (319, "mobile_phone_use"),
    (289, "average_employee_wage"),
    (875, "dependency_ratio"),
    (876, "total_fertility_rate"),
    (878, "child_mortality_rate"),
    (879, "under_five_mortality_rate"),
    (884, "elderly_population_share"),
    (727, "domestic_investment"),
    (729, "foreign_investment"),
    (492, "household_expenditure_per_capita"),
    (760, "food_inadequacy_prevalence"),
    (473, "labor_force_count"),
    (759, "employment_by_industry"),
    (855, "employment_status"),
    (303, "large_medium_industry_employment_output"),
    (773, "large_medium_industry_value_added"),
    (797, "electricity_customer_count"),
)


def _period_label(row: dict[str, Any]) -> str:
    return str(row.get("th", row.get("label", ""))).strip()


def _choose_latest_period(period_rows: list[dict[str, Any]]) -> str:
    labels = [_period_label(row) for row in period_rows]
    labels = [label for label in labels if label]
    if not labels:
        raise ValueError("no period labels returned")

    def sort_key(label: str) -> tuple[int, int | str]:
        try:
            return (1, int(label))
        except ValueError:
            return (0, label)

    return max(labels, key=sort_key)


def probe(*, api_key: str, domain: str, output_dir: Path) -> dict[str, Any]:
    client = BPSClient(api_key)
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []

    for var_id, target_indicator in CANDIDATES:
        item: dict[str, Any] = {
            "var_id": var_id,
            "target_indicator": target_indicator,
            "status": "probe_failed",
        }
        try:
            periods = client.list_periods(domain=domain, lang="ind", var=var_id)
            labels = [_period_label(row) for row in periods if _period_label(row)]
            latest = _choose_latest_period(periods)
            item["available_period_labels"] = labels
            item["selected_period_label"] = latest
            manifest = harvest_series(
                api_key=api_key,
                domain=domain,
                lang="ind",
                var_id=var_id,
                requested_labels=[latest],
                output_dir=output_dir / f"var-{var_id}",
            )
            item["status"] = "harvested_latest_period"
            item["normalized_rows"] = manifest["normalized_rows"]
        except (BPSApiError, BPSDynamicNormalizationError, OSError, ValueError) as exc:
            # Discovery is deliberately fail-soft per candidate. A variable may
            # exist in BPS metadata while its latest Dynamic Data payload is
            # empty or uses a response shape that cannot be normalized safely.
            item["error_type"] = type(exc).__name__
            item["error"] = str(exc)
        results.append(item)

    successful = [item for item in results if item["status"] == "harvested_latest_period"]
    payload = {
        "schema": "ranah-observatory/milestone4-bps-priority-probe/v1",
        "source_id": "bps_webapi",
        "domain": domain,
        "candidate_count": len(results),
        "successful_probe_count": len(successful),
        "failed_probe_count": len(results) - len(successful),
        "canonical_promotion_performed": False,
        "results": results,
    }
    (output_dir / "milestone4-bps-priority-probe.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe high-value BPS candidates for Ranah Observatory Milestone 4.")
    parser.add_argument("--api-key", default=os.environ.get("BPS_API_KEY"))
    parser.add_argument("--domain", default="1300")
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    if not args.api_key:
        print("error: BPS API key is required; set BPS_API_KEY", file=sys.stderr)
        return 2
    try:
        payload = probe(api_key=args.api_key, domain=str(args.domain), output_dir=args.output_dir)
    except (BPSApiError, BPSDynamicNormalizationError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
