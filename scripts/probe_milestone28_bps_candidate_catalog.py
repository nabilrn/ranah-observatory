#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Mapping

from bps_client import BPSApiError, BPSClient

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "data/manifests/milestone28_design_gate.json"
RAW_CATALOG = ROOT / "data/processed/bps/m28_candidate_discovery/bps-domain1300-variable-catalog.json"
OUT_CSV = ROOT / "data/analysis/engine/broader_panel_v1/m28-candidate-catalog.csv"
OUT_MANIFEST = ROOT / "data/manifests/milestone28_bps_catalog_discovery.json"


class DiscoveryError(RuntimeError):
    pass


def normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).casefold()
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def first_value(row: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in row and row.get(key) not in (None, ""):
            return row.get(key)
    return ""


def parse_var_id(row: Mapping[str, Any]) -> int | None:
    raw = first_value(row, ("var_id", "id", "varid"))
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def title_of(row: Mapping[str, Any]) -> str:
    return str(first_value(row, ("title", "var", "label", "name", "nama")) or "").strip()


def unit_of(row: Mapping[str, Any]) -> str:
    return str(first_value(row, ("unit", "satuan")) or "").strip()


def subject_id_of(row: Mapping[str, Any]) -> str:
    return str(first_value(row, ("sub_id", "subject_id", "subject", "subid")) or "").strip()


def subject_name_of(row: Mapping[str, Any]) -> str:
    return str(first_value(row, ("sub_name", "subject_name", "subject_label", "sub")) or "").strip()


def matched_families(title: str, families: Mapping[str, list[str]]) -> list[str]:
    norm = normalize(title)
    matched: list[str] = []
    for family, terms in families.items():
        if any(normalize(term) in norm for term in terms):
            matched.append(family)
    return matched


def main() -> int:
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    expected = {
        "schema": "ranah-observatory/milestone28-design-gate/v1",
        "design_locked_before_catalog_discovery": True,
        "source_id": "bps_webapi",
        "domain": "1300",
        "stage0_metadata_only": True,
        "dynamic_observation_request_authorized": False,
        "observed_value_based_candidate_selection_authorized": False,
        "global_window_shortening_authorized": False,
        "imputation_authorized": False,
        "missing_as_zero_authorized": False,
        "statistical_model_fit_authorized": False,
        "causal_claim_authorized": False,
        "monetary_wasted_potential_estimate_authorized": False,
    }
    for key, value in expected.items():
        if gate.get(key) != value:
            raise DiscoveryError(f"M28 design gate drift: {key}")

    api_key = os.environ.get("BPS_API_KEY", "").strip()
    if not api_key:
        raise DiscoveryError("BPS_API_KEY is required and must not be persisted")

    client = BPSClient(api_key, retries=3, retry_backoff_seconds=1.0)
    rows = client.list_variables(domain=gate["domain"], lang="ind")
    if not rows:
        raise DiscoveryError("BPS domain-1300 variable catalog returned no rows")
    if not all(isinstance(row, Mapping) for row in rows):
        raise DiscoveryError("BPS variable catalog contains non-object rows")

    raw_payload = {
        "schema": "ranah-observatory/milestone28-bps-variable-catalog/v1",
        "source_id": "bps_webapi",
        "domain": gate["domain"],
        "metadata_only": True,
        "dynamic_observation_requested": False,
        "credential_persisted": False,
        "row_count": len(rows),
        "rows": rows,
    }
    RAW_CATALOG.parent.mkdir(parents=True, exist_ok=True)
    RAW_CATALOG.write_bytes(canonical_json_bytes(raw_payload))

    families: dict[str, list[str]] = {k: list(v) for k, v in gate["candidate_families"].items()}
    seed_ids = {int(x) for x in gate["seed_candidate_var_ids"]}
    candidates: list[dict[str, Any]] = []
    catalog_var_ids: set[int] = set()
    catalog_key_counts: dict[str, int] = {}

    for row in rows:
        var_id = parse_var_id(row)
        title = title_of(row)
        if var_id is not None:
            catalog_var_ids.add(var_id)
        for key in row.keys():
            catalog_key_counts[str(key)] = catalog_key_counts.get(str(key), 0) + 1
        families_hit = matched_families(title, families)
        seed_hit = var_id in seed_ids if var_id is not None else False
        if not families_hit and not seed_hit:
            continue
        row_bytes = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        basis = []
        if families_hit:
            basis.append("keyword_family")
        if seed_hit:
            basis.append("existing_seed_id")
        candidates.append({
            "bps_var_id": "" if var_id is None else var_id,
            "bps_title": title,
            "source_unit": unit_of(row),
            "subject_id": subject_id_of(row),
            "subject_name": subject_name_of(row),
            "matched_families": "|".join(sorted(families_hit)),
            "selection_basis": "|".join(basis),
            "catalog_metadata_sha256": sha256_bytes(row_bytes),
            "stage0_status": "metadata_discovery_candidate",
        })

    candidates.sort(key=lambda r: (str(r["matched_families"]), int(r["bps_var_id"]) if str(r["bps_var_id"]).isdigit() else 10**9, r["bps_title"]))
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fields = ["bps_var_id","bps_title","source_unit","subject_id","subject_name","matched_families","selection_basis","catalog_metadata_sha256","stage0_status"]
    with OUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(candidates)

    family_counts = {
        family: sum(family in str(row["matched_families"]).split("|") for row in candidates)
        for family in families
    }
    seed_presence = {str(var_id): var_id in catalog_var_ids for var_id in sorted(seed_ids)}
    manifest = {
        "schema": "ranah-observatory/milestone28-bps-catalog-discovery/v1",
        "milestone": 28,
        "stage": "stage0_metadata_catalog_discovery",
        "domain": gate["domain"],
        "metadata_only": True,
        "dynamic_observation_requested": False,
        "target_values_inspected": False,
        "credential_persisted": False,
        "catalog_row_count": len(rows),
        "candidate_count": len(candidates),
        "candidate_family_counts": family_counts,
        "seed_candidate_presence": seed_presence,
        "catalog_observed_key_counts": dict(sorted(catalog_key_counts.items())),
        "raw_catalog": {"path": RAW_CATALOG.relative_to(ROOT).as_posix(), "sha256": sha256_path(RAW_CATALOG)},
        "candidate_csv": {"path": OUT_CSV.relative_to(ROOT).as_posix(), "sha256": sha256_path(OUT_CSV)},
        "design_gate": {"path": GATE.relative_to(ROOT).as_posix(), "sha256": sha256_path(GATE)},
        "global_window_shortening_performed": False,
        "imputation_performed": False,
        "missing_values_coerced_to_zero": False,
        "derived_indicator_materialized": False,
        "statistical_model_fit": False,
        "causal_claim_created": False,
        "monetary_wasted_potential_estimated": False,
        "next_gate": "period and dynamic-structure qualification for a preregistered subset of metadata candidates; no values before selector/unit/methodology contracts are locked",
    }
    OUT_MANIFEST.write_bytes(canonical_json_bytes(manifest))
    print(json.dumps({
        "catalog_rows": len(rows),
        "candidates": len(candidates),
        "family_counts": family_counts,
        "seed_presence": seed_presence,
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BPSApiError, OSError, ValueError, json.JSONDecodeError, DiscoveryError) as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
