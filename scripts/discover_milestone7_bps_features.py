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

# Four preregistered capability candidates. IDs are all national-domain BPS IDs:
# - 1429 and 398 were discovered and frozen from national WebAPI subject catalogs.
# - 417 and 2273 are national BPS Statistics Table IDs discovered from official
#   www.bps.go.id table pages and are re-probed through WebAPI here. A public table
#   page is discovery evidence only; promotion still requires the exact WebAPI checks.
DIRECT_CANDIDATES: tuple[dict[str, Any], ...] = (
    {
        "subject_id": 28,
        "subject_label": "Pendidikan",
        "var_id": 1429,
        "title": "Rata-Rata Lama Sekolah Penduduk Umur 15 Tahun ke Atas Menurut Provinsi",
        "groups": ["human_capital_schooling"],
        "origin": "national BPS subject 28 catalog; frozen in milestone7 discovery v5",
    },
    {
        "subject_id": 26,
        "subject_label": "Indeks Pembangunan Manusia",
        "var_id": 417,
        "title": "[Metode Baru] Harapan Lama Sekolah",
        "groups": ["human_capital_expected_schooling"],
        "origin": "https://www.bps.go.id/id/statistics-table/2/NDE3IzI%3D/-metode-baru--harapan-lama-sekolah.html",
    },
    {
        "subject_id": 30,
        "subject_label": "Kesehatan",
        "var_id": 2273,
        "title": "Umur Harapan Hidup saat lahir menurut Provinsi dan Jenis Kelamin (menggunakan UHH hasil SP2020 LF)",
        "groups": ["health_life_expectancy"],
        "origin": "https://www.bps.go.id/id/statistics-table/2/MjI3MyMy/umur-harapan-hidup-saat-lahir-menurut-provinsi-dan-jenis-kelamin--menggunakan-uhh-hasil-sp2020-lf-.html",
    },
    {
        "subject_id": 2,
        "subject_label": "Komunikasi",
        "var_id": 398,
        "title": "Persentase Rumah Tangga yang Pernah Mengakses Internet dalam 3 Bulan Terakhir Menurut Provinsi dan Klasifikasi Daerah",
        "groups": ["digital_connectivity"],
        "origin": "national BPS subject 2 catalog; frozen in milestone7 discovery v4/v5",
    },
)

FEATURE_TERMS: dict[str, tuple[str, ...]] = {
    "human_capital_schooling": ("rata-rata lama sekolah", "rata rata lama sekolah"),
    "human_capital_expected_schooling": ("harapan lama sekolah",),
    "health_life_expectancy": ("umur harapan hidup", "angka harapan hidup"),
    "digital_connectivity": ("mengakses internet", "akses internet"),
}


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold().replace("–", "-").replace("—", "-")).strip()


def matched_feature_groups(text: str) -> list[str]:
    norm = normalize(text)
    return [
        group for group, terms in FEATURE_TERMS.items()
        if any(normalize(term) in norm for term in terms)
    ]


def probe_candidate(client: BPSClient, candidate: Mapping[str, Any]) -> dict[str, Any]:
    var_id = int(candidate["var_id"])
    result: dict[str, Any] = {
        "subject_id": int(candidate["subject_id"]),
        "subject_label": str(candidate["subject_label"]),
        "bps_var_id": var_id,
        "catalog_title": str(candidate["title"]),
        "catalog_feature_groups": list(candidate["groups"]),
        "candidate_origin": str(candidate["origin"]),
    }
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
            if all(checks.values()) else "hold_semantics_or_structure"
        )
    except (BPSApiError, ValueError, TypeError) as exc:
        result["probe_status"] = "probe_error"
        result["error"] = str(exc)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe four national BPS capability candidates for Milestone 7.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    api_key = os.environ.get("BPS_API_KEY", "").strip()
    if not api_key:
        print("error: BPS_API_KEY is required", file=sys.stderr)
        return 2
    client = BPSClient(api_key, retries=3, retry_backoff_seconds=1.0)
    results = [probe_candidate(client, candidate) for candidate in DIRECT_CANDIDATES]
    report = {
        "schema": "ranah-observatory/milestone7-bps-feature-discovery/v6",
        "domain": DOMAIN,
        "model_year": MODEL_YEAR,
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
        "candidate_summary": [
            {
                "bps_var_id": row.get("bps_var_id"),
                "source_title": row.get("source_title", row.get("catalog_title", "")),
                "feature_groups": row.get("semantic_feature_groups", row.get("catalog_feature_groups", [])),
                "probe_status": row.get("probe_status"),
                "available_years": row.get("available_years", []),
                "labelvervar": (row.get("geography") or {}).get("labelvervar", ""),
                "non_aggregate_geography_count": (row.get("geography") or {}).get("non_aggregate_geography_count", 0),
                "turvar": row.get("turvar", []),
                "turtahun": row.get("turtahun", []),
            }
            for row in results
        ],
        "results": results,
        "interpretation": (
            "Discovery only. Passing title/period/geography checks are necessary but not sufficient. "
            "Final promotion requires explicit selector, unit, denominator, methodology and frozen values."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "candidate_count": report["candidate_count"],
        "semantic_current38_2024_candidate_count": report["semantic_current38_2024_candidate_count"],
        "feature_candidate_counts": report["feature_candidate_counts"],
        "candidate_summary": report["candidate_summary"],
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
