#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from scripts import audit_milestone27_bkpm_frozen_inventory as base

ROOT = Path(__file__).resolve().parents[1]
AMENDMENT = ROOT / "data/manifests/milestone27_semantic_representation_amendment.json"
_ORIGINAL_SEMANTIC_STATES = base.semantic_states


def semantic_states_v2(raw: str, year: int, quarter: str) -> dict[str, bool]:
    states = _ORIGINAL_SEMANTIC_STATES(raw, year, quarter)
    if states["period_field_semantics_match"]:
        return states

    text = base.clean_text(re.sub(r"<[^>]+>", " ", raw))
    punctuation_only_equivalent = bool(re.search(
        r"periode\s*:\s*Periode dari data yang disajikan\s+sudah dikelompokan berdasarkan tahun dan triwulan",
        text,
        flags=re.IGNORECASE,
    ))
    if punctuation_only_equivalent:
        states["period_field_semantics_match"] = True
    return states


def validate_amendment() -> None:
    amendment = json.loads(AMENDMENT.read_text(encoding="utf-8"))
    if amendment.get("schema") != "ranah-observatory/milestone27-semantic-representation-amendment/v1":
        raise base.AuditError("unexpected M27 semantic representation amendment")
    if amendment.get("target_investment_values_inspected_before_amendment") is not False:
        raise base.AuditError("semantic amendment was made after target-value inspection")
    if amendment.get("resource_file_downloaded_before_amendment") is not False:
        raise base.AuditError("semantic amendment was made after resource download")
    if amendment.get("substantive_semantic_difference_observed") is not False:
        raise base.AuditError("representation amendment records substantive semantic change")
    if amendment.get("unaffected_source_conflict", {}).get("period") != "2025-Q2":
        raise base.AuditError("2025-Q2 source conflict boundary drift")
    if amendment.get("unaffected_source_conflict", {}).get("automatically_resolved_by_this_amendment") is not False:
        raise base.AuditError("representation amendment improperly resolves 2025-Q2 conflict")
    for key in (
        "source_family_changed",
        "target_period_changed",
        "field_set_changed",
        "quarterly_flow_interpretation_authorized",
        "cross_quarter_additivity_authorized",
        "annual_sum_authorized",
        "resource_transport_qualified",
        "resource_header_retrieval_authorized",
        "numeric_value_inspection_authorized",
        "numeric_aggregation_authorized",
        "statistical_model_fit_authorized",
        "causal_claim_authorized",
        "monetary_wasted_potential_estimate_authorized",
    ):
        if amendment.get(key) is not False:
            raise base.AuditError(f"forbidden semantic-amendment expansion: {key}")


def main() -> int:
    validate_amendment()
    base.semantic_states = semantic_states_v2
    return base.main()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError, base.AuditError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
