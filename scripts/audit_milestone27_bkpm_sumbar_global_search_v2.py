#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "data/manifests/milestone27_bkpm_sumbar_global_search_probe.json"
AMENDMENT = ROOT / "data/manifests/milestone27_sumbar_global_search_representation_amendment.json"
OUT = ROOT / "data/manifests/milestone27_bkpm_sumbar_global_search_qualified.json"


class AuditError(RuntimeError):
    pass


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    probe = load_json(PROBE)
    amendment = load_json(AMENDMENT)
    if probe.get("schema") != "ranah-observatory/milestone27-bkpm-sumbar-global-search-probe/v1":
        raise AuditError("unexpected probe schema")
    if amendment.get("schema") != "ranah-observatory/milestone27-sumbar-global-search-representation-amendment/v1":
        raise AuditError("unexpected amendment schema")
    if amendment.get("original_qualification_rule_retained_as_historical_record") is not True:
        raise AuditError("original result must remain retained")
    for key in (
        "source_selection_uses_target_investment_values",
        "target_investment_values_inspection_authorized",
        "numeric_materialization_authorized",
        "quarterly_flow_interpretation_authorized",
        "cross_quarter_additivity_authorized",
        "annual_sum_authorized",
        "geography_mapping_authorized",
        "statistical_model_fit_authorized",
        "causal_claim_authorized",
        "monetary_wasted_potential_estimate_authorized",
    ):
        if amendment.get(key) is not False:
            raise AuditError(f"forbidden amendment authorization enabled: {key}")

    rows: list[dict[str, Any]] = []
    for row in probe["pilot_results"]:
        baseline = row["baseline_records_total"]
        pos = row["positive_search"]
        neg = row["negative_control_search"]
        qualified = (
            pos["status"] == 200
            and pos["data_array_empty"] is True
            and isinstance(pos["records_filtered"], int)
            and 0 < pos["records_filtered"] < baseline
            and pos["records_total"] == pos["records_filtered"]
            and neg["status"] == 200
            and neg["data_array_empty"] is True
            and neg["records_total"] == 0
            and neg["records_filtered"] == 0
            and pos["data_array_elements_inspected"] is False
            and neg["data_array_elements_inspected"] is False
            and pos["target_investment_values_inspected"] is False
            and neg["target_investment_values_inspected"] is False
        )
        rows.append({
            "year": row["year"],
            "quarter": row["quarter"],
            "dataset_identifier": row["dataset_identifier"],
            "unfiltered_baseline_records_total": baseline,
            "sumbar_post_search_count": pos["records_filtered"],
            "positive_records_total": pos["records_total"],
            "positive_records_filtered": pos["records_filtered"],
            "negative_records_total": neg["records_total"],
            "negative_records_filtered": neg["records_filtered"],
            "positive_data_array_empty": pos["data_array_empty"],
            "negative_data_array_empty": neg["data_array_empty"],
            "global_search_transport_qualified": qualified,
        })

    all_qualified = all(r["global_search_transport_qualified"] for r in rows)
    payload = {
        "schema": "ranah-observatory/milestone27-bkpm-sumbar-global-search-qualified/v1",
        "milestone": 27,
        "stage": "stage0k_representation_amended_qualification",
        "pilot_count": len(rows),
        "pilot_results": rows,
        "global_search_transport_qualified_all_pilots": all_qualified,
        "server_count_semantics": "recordsTotal_and_recordsFiltered_are_post_search_counts_on_the_observed_BKPM_route",
        "original_probe_result_preserved": True,
        "target_investment_values_inspected": False,
        "data_array_elements_inspected": False,
        "numeric_materialization_authorized": False,
        "quarterly_flow_interpretation_authorized": False,
        "cross_quarter_additivity_authorized": False,
        "annual_sum_authorized": False,
        "geography_mapping_authorized": False,
        "statistical_model_fit": False,
        "causal_claim_created": False,
        "monetary_wasted_potential_estimated": False,
        "probe": {"path": rel(PROBE), "sha256": sha256_path(PROBE)},
        "amendment": {"path": rel(AMENDMENT), "sha256": sha256_path(AMENDMENT)},
    }
    write_json(OUT, payload)
    print(json.dumps({
        "all_qualified": all_qualified,
        "sumbar_counts": {f"{r['year']}-{r['quarter']}": r['sumbar_post_search_count'] for r in rows},
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError, AuditError) as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
