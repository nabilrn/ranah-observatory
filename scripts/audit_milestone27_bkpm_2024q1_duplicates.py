#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "data/manifests/milestone27_2024q1_duplicate_diagnostic_contract.json"
RAW_DIR = ROOT / "data/processed/bkpm/m27_full_history/2024/q1"
FULL_HISTORY = ROOT / "data/manifests/milestone27_bkpm_full_history.json"
OUT_MANIFEST = ROOT / "data/manifests/milestone27_bkpm_2024q1_duplicate_diagnostic.json"
OUT_CSV = ROOT / "data/analysis/engine/investment_realization_v1/m27-bkpm-2024q1-duplicate-diagnostic.csv"


class DiagnosticError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_tuple(row: dict[str, Any], fields: list[str]) -> tuple[str, ...]:
    return tuple("" if row.get(f) is None else str(row.get(f)) for f in fields)


def tuple_hash(values: tuple[str, ...]) -> str:
    return sha256_text(json.dumps(values, ensure_ascii=False, separators=(",", ":")))


def full_row_hash(row: dict[str, Any], all_fields: list[str]) -> str:
    values = canonical_tuple(row, all_fields)
    return tuple_hash(values)


def main() -> int:
    contract = load_json(CONTRACT)
    if contract.get("schema") != "ranah-observatory/milestone27-2024q1-duplicate-diagnostic-contract/v1":
        raise DiagnosticError("unexpected contract schema")
    if contract.get("diagnostic_locked_before_analysis") is not True:
        raise DiagnosticError("diagnostic contract not locked")
    if contract.get("network_requests_authorized") is not False:
        raise DiagnosticError("network unexpectedly authorized")
    for key in (
        "raw_target_metric_values_in_diagnostic_outputs_authorized",
        "deduplication_authorized",
        "aggregation_contract_amendment_authorized",
        "source_row_deletion_authorized",
        "annual_sum_authorized",
        "cross_quarter_additivity_authorized",
        "pma_pmdn_combination_authorized",
        "external_fx_conversion_authorized",
        "statistical_model_fit_authorized",
        "causal_claim_authorized",
        "monetary_wasted_potential_estimate_authorized",
    ):
        if contract.get(key) is not False:
            raise DiagnosticError(f"forbidden authorization enabled: {key}")

    full_history = load_json(FULL_HISTORY)
    q = next((r for r in full_history.get("quarter_results", []) if r.get("year") == 2024 and r.get("quarter") == "I"), None)
    if q is None:
        raise DiagnosticError("2024-Q1 missing from full-history manifest")
    if q.get("qualified") is not False or "duplicate_complete_source_dimension_tuple" not in q.get("fail_reasons", []):
        raise DiagnosticError("2024-Q1 original failed duplicate state not preserved")

    dimension_fields = list(contract["dimension_fields"])
    non_dimension_fields = list(contract["non_dimension_fields"])
    all_fields = dimension_fields + non_dimension_fields

    page_paths = sorted(RAW_DIR.glob("page-*.json"))
    if not page_paths:
        raise DiagnosticError("no frozen pages found")

    rows: list[dict[str, Any]] = []
    row_meta: list[dict[str, Any]] = []
    expected_columns: list[str] | None = None
    for page_path in page_paths:
        payload = load_json(page_path)
        page_columns = payload.get("columns")
        page_data = payload.get("data")
        if not isinstance(page_columns, list) or not all(isinstance(x, str) for x in page_columns):
            raise DiagnosticError(f"invalid columns in {page_path}")
        if expected_columns is None:
            expected_columns = list(page_columns)
        elif page_columns != expected_columns:
            raise DiagnosticError("schema changes across frozen pages")
        if not isinstance(page_data, list):
            raise DiagnosticError(f"invalid data in {page_path}")
        for page_index, raw_row in enumerate(page_data):
            if not isinstance(raw_row, dict):
                raise DiagnosticError(f"non-object row in {page_path}")
            if set(raw_row.keys()) != set(expected_columns):
                raise DiagnosticError(f"row schema mismatch in {page_path}")
            rows.append(raw_row)
            row_meta.append({
                "page_path": page_path.relative_to(ROOT).as_posix(),
                "page_index": page_index,
                "dimension_hash": tuple_hash(canonical_tuple(raw_row, dimension_fields)),
                "full_row_hash": full_row_hash(raw_row, all_fields),
            })

    expected_count = int(contract["expected_source_row_count"])
    if len(rows) != expected_count:
        raise DiagnosticError(f"expected {expected_count} frozen rows, reconstructed {len(rows)}")

    groups: dict[str, list[int]] = defaultdict(list)
    for idx, meta in enumerate(row_meta):
        groups[meta["dimension_hash"]].append(idx)
    duplicate_groups = {h: idxs for h, idxs in groups.items() if len(idxs) > 1}

    diag_rows: list[dict[str, Any]] = []
    exact_group_count = 0
    divergent_group_count = 0
    cross_page_group_count = 0
    exact_cross_page_group_count = 0
    rows_in_duplicate_groups = 0
    differing_non_dimension_counter: Counter[str] = Counter()
    multiplicity_counter: Counter[int] = Counter()

    for dimension_hash, idxs in sorted(duplicate_groups.items()):
        rows_in_duplicate_groups += len(idxs)
        multiplicity_counter[len(idxs)] += 1
        pages = sorted({row_meta[i]["page_path"] for i in idxs})
        full_hashes = sorted({row_meta[i]["full_row_hash"] for i in idxs})
        cross_page = len(pages) > 1
        exact_full_row = len(full_hashes) == 1
        if cross_page:
            cross_page_group_count += 1
        if exact_full_row:
            exact_group_count += 1
            if cross_page:
                exact_cross_page_group_count += 1
        else:
            divergent_group_count += 1

        differing_fields: list[str] = []
        for field in non_dimension_fields:
            values = {"" if rows[i].get(field) is None else str(rows[i].get(field)) for i in idxs}
            if len(values) > 1:
                differing_fields.append(field)
                differing_non_dimension_counter[field] += 1

        diag_rows.append({
            "dimension_tuple_sha256": dimension_hash,
            "multiplicity": len(idxs),
            "page_count": len(pages),
            "page_paths": "|".join(pages),
            "distinct_full_row_hash_count": len(full_hashes),
            "full_row_hashes": "|".join(full_hashes),
            "exact_full_row_duplicate": str(exact_full_row).lower(),
            "crosses_page_boundary": str(cross_page).lower(),
            "differing_non_dimension_fields": "|".join(differing_fields),
        })

    if exact_group_count and divergent_group_count:
        classification = "mixed_duplicate_mechanisms"
    elif exact_cross_page_group_count:
        classification = "pagination_overlap_candidate"
    elif exact_group_count:
        classification = "source_exact_duplicate_candidate"
    elif divergent_group_count:
        classification = "public_dimension_key_incomplete_candidate"
    else:
        classification = "no_duplicate_reproduced"

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "dimension_tuple_sha256", "multiplicity", "page_count", "page_paths",
        "distinct_full_row_hash_count", "full_row_hashes", "exact_full_row_duplicate",
        "crosses_page_boundary", "differing_non_dimension_fields",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(diag_rows)

    manifest = {
        "schema": "ranah-observatory/milestone27-bkpm-2024q1-duplicate-diagnostic/v1",
        "milestone": 27,
        "stage": "stage1_full_history_2024q1_duplicate_diagnostic",
        "offline_frozen_evidence_only": True,
        "network_requests_performed": False,
        "source_quarter": "2024-Q1",
        "frozen_page_count": len(page_paths),
        "reconstructed_source_row_count": len(rows),
        "dimension_field_count": len(dimension_fields),
        "duplicate_dimension_group_count": len(duplicate_groups),
        "rows_in_duplicate_dimension_groups": rows_in_duplicate_groups,
        "duplicate_group_multiplicity_distribution": {str(k): v for k, v in sorted(multiplicity_counter.items())},
        "exact_full_row_duplicate_group_count": exact_group_count,
        "dimension_collision_with_distinct_full_rows_group_count": divergent_group_count,
        "cross_page_duplicate_dimension_group_count": cross_page_group_count,
        "exact_full_row_cross_page_duplicate_group_count": exact_cross_page_group_count,
        "differing_non_dimension_field_group_counts": dict(sorted(differing_non_dimension_counter.items())),
        "classification": classification,
        "raw_target_metric_values_written_to_diagnostic_outputs": False,
        "deduplication_performed": False,
        "aggregation_contract_amended": False,
        "source_rows_deleted": False,
        "annual_sum_performed": False,
        "cross_quarter_addition_performed": False,
        "pma_pmdn_combination_performed": False,
        "external_fx_conversion_performed": False,
        "statistical_model_fit": False,
        "causal_claim_created": False,
        "monetary_wasted_potential_estimated": False,
        "original_2024q1_failure_preserved": True,
        "diagnostic_csv": {"path": OUT_CSV.relative_to(ROOT).as_posix(), "sha256": sha256_path(OUT_CSV)},
        "contract": {"path": CONTRACT.relative_to(ROOT).as_posix(), "sha256": sha256_path(CONTRACT)},
        "full_history_manifest": {"path": FULL_HISTORY.relative_to(ROOT).as_posix(), "sha256": sha256_path(FULL_HISTORY)},
        "frozen_pages": [
            {"path": p.relative_to(ROOT).as_posix(), "sha256": sha256_path(p), "bytes": p.stat().st_size}
            for p in page_paths
        ],
    }
    OUT_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "classification": classification,
        "duplicate_groups": len(duplicate_groups),
        "rows_in_duplicate_groups": rows_in_duplicate_groups,
        "exact_groups": exact_group_count,
        "divergent_groups": divergent_group_count,
        "cross_page_groups": cross_page_group_count,
        "exact_cross_page_groups": exact_cross_page_group_count,
        "differing_fields": dict(sorted(differing_non_dimension_counter.items())),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError, DiagnosticError) as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
