#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TAXONOMY = ROOT / "data/manifests/milestone25_taxonomy_discovery.json"
OUT = ROOT / "data/registries/djpk_m25_stage1_account_contracts.csv"
MANIFEST = ROOT / "data/manifests/milestone25_stage1_contracts.json"

CONCEPTUAL_ORDER = [
    "total_revenue",
    "own_source_revenue_pad",
    "total_expenditure",
    "capital_expenditure",
    "central_transfer_revenue",
]


class ContractLockError(RuntimeError):
    pass


def normalize_label(text: str) -> str:
    import re
    return re.sub(r"\s+", " ", (text or "").casefold()).strip()


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def lock_contracts() -> dict[str, Any]:
    taxonomy = json.loads(TAXONOMY.read_text(encoding="utf-8"))
    if taxonomy.get("schema") != "ranah-observatory/milestone25-taxonomy-discovery/v1":
        raise ContractLockError("unexpected M25 taxonomy schema")
    if taxonomy.get("stage0_complete") is not True or taxonomy.get("all_pages_pass") is not True:
        raise ContractLockError("M25 Stage 0 must be complete before Stage 1 contract lock")
    if taxonomy.get("cross_geography_values_inspected_before_taxonomy_lock") is not False:
        raise ContractLockError("cross-geography values were inspected before contract lock")
    if taxonomy.get("posthoc_account_family_search_performed") is not False:
        raise ContractLockError("posthoc account-family search detected")

    results = taxonomy.get("conceptual_account_family_results")
    if not isinstance(results, list) or len(results) != 5:
        raise ContractLockError("M25 Stage 0 must classify exact five conceptual families")
    by_family = {str(row["conceptual_family"]): row for row in results}
    if set(by_family) != set(CONCEPTUAL_ORDER):
        raise ContractLockError("M25 conceptual family set drift")

    rows: list[dict[str, Any]] = []
    promoted: list[str] = []
    held: list[str] = []
    for family in CONCEPTUAL_ORDER:
        result = by_family[family]
        status = str(result["status"])
        source_labels = str(result.get("source_labels", ""))
        if status == "exact_label_qualified":
            if not source_labels or "|" in source_labels:
                raise ContractLockError(f"exact-label family {family} must have one source label")
            promotion = "promoted_exact_label"
            promoted.append(family)
            source_label = source_labels
            source_label_normalized = normalize_label(source_label)
        else:
            promotion = "held_stage0_taxonomy_review"
            held.append(family)
            source_label = ""
            source_label_normalized = ""
        rows.append(
            {
                "conceptual_family": family,
                "stage0_status": status,
                "stage1_promotion_status": promotion,
                "locked_source_label": source_label,
                "locked_source_label_normalized": source_label_normalized,
                "stage0_source_labels_seen": source_labels,
                "stage0_years_covered": result.get("years_covered", ""),
                "reference_period": "realisasi_s.d._desember",
                "djpk_period_selector": "12",
                "value_field": "Realisasi",
                "canonical_value_unit": "IDR_billion",
                "taxonomy_contract_type": "exact_label" if promotion == "promoted_exact_label" else "held",
                "cross_geography_values_inspected_before_lock": False,
                "derived_ratio_authorized": False,
            }
        )

    if len(promoted) < 1:
        raise ContractLockError("no exact-label fiscal family qualified for Stage 1")

    write_csv(OUT, list(rows[0].keys()), rows)
    manifest = {
        "schema": "ranah-observatory/milestone25-stage1-account-contracts/v1",
        "milestone": 25,
        "stage": 1,
        "contracts_locked": True,
        "contract_family_count": 5,
        "promoted_exact_label_family_count": len(promoted),
        "promoted_exact_label_families": promoted,
        "held_family_count": len(held),
        "held_families": held,
        "cross_geography_values_inspected_before_lock": False,
        "explicit_bridge_promoted": False,
        "derived_ratio_authorized": False,
        "posthoc_account_family_search_performed": False,
        "statistical_model_fit": False,
        "contract_registry": OUT.relative_to(ROOT).as_posix(),
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    try:
        manifest = lock_contracts()
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ContractLockError) as exc:
        print(f"error: {exc}")
        return 2
    print(json.dumps({
        "contracts_locked": manifest["contracts_locked"],
        "promoted_exact_label_families": manifest["promoted_exact_label_families"],
        "held_families": manifest["held_families"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
