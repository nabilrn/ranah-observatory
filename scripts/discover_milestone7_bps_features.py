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
from probe_bps_comparative_panel import as_list, geography_summary, label_of, period_candidates, value_of

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "manifests" / "milestone7_bps_feature_discovery.json"
DOMAIN = "0000"
MODEL_YEAR = 2024

# These IDs/labels are frozen from data/manifests/milestone7_bps_subject_catalog.json,
# which was retrieved directly from national BPS domain 0000. They are not inherited
# from the Sumatera Barat domain.
VERIFIED_NATIONAL_SUBJECTS: tuple[tuple[int, str], ...] = (
    (26, "Indeks Pembangunan Manusia"),
    (12, "Kependudukan"),
    (2, "Komunikasi"),
    (52, "Produk Domestik Regional Bruto (Lapangan Usaha)"),
)

FEATURE_TERMS: dict[str, tuple[str, ...]] = {
    "human_capital_schooling": ("rata-rata lama sekolah", "rata rata lama sekolah"),
    "human_capital_expected_schooling": ("harapan lama sekolah",),
    "health_life_expectancy": ("umur harapan hidup", "angka harapan hidup"),
    "population_density": ("kepadatan penduduk",),
    "urbanization": ("persentase penduduk perkotaan", "penduduk perkotaan"),
    "digital_connectivity": ("mengakses internet", "akses internet"),
    "sector_structure": (
        "produk domestik regional bruto menurut lapangan usaha",
        "pdrb menurut lapangan usaha",
    ),
    "population_scale": ("jumlah penduduk", "proyeksi penduduk"),
}


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold().replace("–", "-").replace("—", "-")).strip()


def first_text(row: Mapping[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def first_int(row: Mapping[str, Any], keys: tuple[str, ...]) -> int | None:
    for key in keys:
        value = row.get(key)
        if value in (None, ""):
            continue
        try:
            return int(str(value).strip())
        except ValueError:
            continue
    return None


def var_id_of(row: Mapping[str, Any]) -> int | None:
    return first_int(row, ("var_id", "id", "val", "var"))


def var_label_of(row: Mapping[str, Any]) -> str:
    label = first_text(row, ("title", "label", "var", "name"))
    if label:
        return label
    return " ".join(
        str(value) for value in row.values()
        if isinstance(value, (str, int, float)) and str(value).strip()
    )


def matched_feature_groups(text: str) -> list[str]:
    norm = normalize(text)
    return [
        group
        for group, terms in FEATURE_TERMS.items()
        if any(normalize(term) in norm for term in terms)
    ]


def probe_candidate(
    client: BPSClient,
    *,
    subject_id: int,
    subject_label: str,
    variable_row: Mapping[str, Any],
    discovery_groups: list[str],
) -> dict[str, Any]:
    var_id = var_id_of(variable_row)
    result: dict[str, Any] = {
        "subject_id": subject_id,
        "subject_label": subject_label,
        "bps_var_id": var_id,
        "catalog_title": var_label_of(variable_row),
        "catalog_feature_groups": discovery_groups,
        "catalog_metadata": dict(variable_row),
    }
    if var_id is None:
        result["probe_status"] = "hold_missing_var_id"
        return result

    try:
        periods = period_candidates(client.list_periods(domain=DOMAIN, var=var_id))
        selected = next((row for row in periods if row.get("year") == MODEL_YEAR), None)
        result["available_years"] = sorted(
            {int(row["year"]) for row in periods if isinstance(row.get("year"), int)}
        )
        result["selected_model_period"] = selected
        if selected is None or selected.get("period_id") in (None, ""):
            result["probe_status"] = "hold_no_2024_period"
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
        semantic_groups = matched_feature_groups(source_title)
        result.update(
            {
                "source_title": source_title,
                "source_unit": source_unit,
                "source_note": source_note,
                "semantic_feature_groups": semantic_groups,
                "geography": geography,
                "turvar": [{"value": value_of(item), "label": label_of(item)} for item in turvar],
                "turtahun": [{"value": value_of(item), "label": label_of(item)} for item in turtahun],
                "datacontent_count": len(datacontent) if isinstance(datacontent, Mapping) else 0,
            }
        )
        checks = {
            "semantic_title_match": bool(semantic_groups),
            "vertical_is_province": "provinsi" in geography["labelvervar"].casefold(),
            "exactly_38_nonaggregate_geographies": geography["non_aggregate_geography_count"] == 38,
            "west_sumatra_present": bool(geography["west_sumatra_entries"]),
            "datacontent_present": isinstance(datacontent, Mapping) and len(datacontent) > 0,
            "model_year_is_2024": selected.get("year") == MODEL_YEAR,
        }
        result["structure_checks"] = checks
        result["probe_status"] = (
            "semantic_current38_2024_candidate"
            if all(checks.values())
            else "hold_semantics_or_structure"
        )
    except (BPSApiError, ValueError, TypeError) as exc:
        result["probe_status"] = "probe_error"
        result["error"] = str(exc)
    return result


def list_subject_variables(
    client: BPSClient, subject_id: int
) -> tuple[list[Mapping[str, Any]], str]:
    rows = client.list_variables(domain=DOMAIN, subject=subject_id, year=MODEL_YEAR)
    if rows:
        return rows, "year_2024_catalog_filter"
    return client.list_variables(domain=DOMAIN, subject=subject_id), "unfiltered_catalog_fallback"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Discover 2024 national BPS structural features for the Milestone 7 baseline model."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    api_key = os.environ.get("BPS_API_KEY", "").strip()
    if not api_key:
        print("error: BPS_API_KEY is required", file=sys.stderr)
        return 2
    client = BPSClient(api_key, retries=3, retry_backoff_seconds=1.0)

    variable_candidates: list[tuple[int, str, Mapping[str, Any], list[str]]] = []
    subject_variable_counts: list[dict[str, Any]] = []
    seen_vars: set[int] = set()

    for subject_id, subject_label in VERIFIED_NATIONAL_SUBJECTS:
        try:
            rows, catalog_mode = list_subject_variables(client, subject_id)
        except BPSApiError as exc:
            subject_variable_counts.append(
                {"subject_id": subject_id, "subject_label": subject_label, "error": str(exc)}
            )
            continue
        matched = 0
        for row in rows:
            groups = matched_feature_groups(var_label_of(row))
            var_id = var_id_of(row)
            if not groups or var_id is None or var_id in seen_vars:
                continue
            seen_vars.add(var_id)
            matched += 1
            variable_candidates.append((subject_id, subject_label, row, groups))
        subject_variable_counts.append(
            {
                "subject_id": subject_id,
                "subject_label": subject_label,
                "catalog_mode": catalog_mode,
                "variable_count": len(rows),
                "matched_variable_count": matched,
            }
        )

    variable_candidates.sort(key=lambda item: (item[3][0], item[0], var_id_of(item[2]) or 0))
    results = [
        probe_candidate(
            client,
            subject_id=subject_id,
            subject_label=subject_label,
            variable_row=row,
            discovery_groups=groups,
        )
        for subject_id, subject_label, row, groups in variable_candidates
    ]
    report = {
        "schema": "ranah-observatory/milestone7-bps-feature-discovery/v4",
        "domain": DOMAIN,
        "model_year": MODEL_YEAR,
        "subject_catalog_source": "data/manifests/milestone7_bps_subject_catalog.json",
        "verified_national_subjects": [
            {"subject_id": subject_id, "subject_label": subject_label}
            for subject_id, subject_label in VERIFIED_NATIONAL_SUBJECTS
        ],
        "subject_variable_counts": subject_variable_counts,
        "candidate_count": len(results),
        "semantic_current38_2024_candidate_count": sum(
            row.get("probe_status") == "semantic_current38_2024_candidate" for row in results
        ),
        "feature_candidate_counts": {
            group: sum(
                group in row.get("semantic_feature_groups", [])
                and row.get("probe_status") == "semantic_current38_2024_candidate"
                for row in results
            )
            for group in FEATURE_TERMS
        },
        "results": results,
        "interpretation": (
            "Discovery only. Subject IDs are verified national-domain metadata. Candidate promotion still requires "
            "selector, methodology, unit, denominator and exact 38-province value qualification."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "candidate_count": report["candidate_count"],
        "semantic_current38_2024_candidate_count": report["semantic_current38_2024_candidate_count"],
        "feature_candidate_counts": report["feature_candidate_counts"],
        "subject_variable_counts": report["subject_variable_counts"],
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
