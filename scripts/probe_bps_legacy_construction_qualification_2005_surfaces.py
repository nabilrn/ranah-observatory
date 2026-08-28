#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from bps_client import BPSApiError, BPSClient

OUTDIR = Path("probe-output")
DOMAINS = ("0000", "1300")
KEYWORDS = (
    "kualifikasi perusahaan konstruksi",
    "jumlah perusahaan konstruksi",
    "perusahaan konstruksi menurut kualifikasi",
    "konstruksi",
)
TARGET_VAR = 216
TARGET_YEAR = "2005"
TARGET_TH_ID = 105


def folded(value: Any) -> str:
    return " ".join(str(value).casefold().split())


def row_text(row: Mapping[str, Any]) -> str:
    return folded(json.dumps(row, ensure_ascii=False, sort_keys=True))


def relevant(text: str) -> bool:
    return "konstruksi" in text and (
        "kualifikasi" in text
        or "jumlah perusahaan" in text
        or "banyaknya perusahaan" in text
        or "usaha/perusahaan" in text
    )


def candidate_id(row: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def source_period_labels(rows: list[Mapping[str, Any]]) -> list[str]:
    labels: set[str] = set()
    for row in rows:
        for key in ("label", "tahun", "year", "th"):
            value = row.get(key)
            if value is not None:
                labels.add(str(value).strip())
    return sorted(x for x in labels if x)


def main() -> int:
    key = os.environ.get("BPS_API_KEY", "").strip()
    if not key:
        raise SystemExit("BPS_API_KEY is required")

    OUTDIR.mkdir(parents=True, exist_ok=True)
    client = BPSClient(key, timeout=60, retries=2, retry_backoff_seconds=1.0)
    report: dict[str, Any] = {
        "schema": "ranah-observatory/bps-legacy-construction-qualification-2005-surfaces/v2",
        "purpose": (
            "Search official central and Sumatera Barat BPS legacy static/dynamic WebAPI surfaces "
            "for construction-establishment qualification data with an explicit source-native 2005 period, "
            "then inspect central variable 216 because its source is Direktori Perusahaan Konstruksi."
        ),
        "api_key_persisted": False,
        "domains": {},
        "target_var_216": {
            "domain": "0000",
            "var_id": TARGET_VAR,
            "year": TARGET_YEAR,
            "th_id": TARGET_TH_ID,
            "derived_variables": [],
            "derived_periods": [],
            "dynamic_2005": None,
            "errors": [],
        },
    }

    for domain in DOMAINS:
        d: dict[str, Any] = {
            "static_searches": [],
            "static_candidates": [],
            "subject_candidates": [],
            "variable_candidates": [],
            "variables_with_2005": [],
            "errors": [],
        }
        static_seen: dict[str, Mapping[str, Any]] = {}
        for keyword in KEYWORDS:
            try:
                rows = client.list_static_tables(
                    domain=domain, lang="ind", keyword=keyword, max_pages=20
                )
            except BPSApiError as exc:
                d["errors"].append({"stage": f"statictable:{keyword}", "error": str(exc)})
                continue
            d["static_searches"].append({"keyword": keyword, "rows": len(rows)})
            for row in rows:
                text = row_text(row)
                if not relevant(text):
                    continue
                rid = candidate_id(row, ("table_id", "id", "sub_id")) or text
                static_seen[rid] = row
        d["static_candidates"] = [dict(x) for x in static_seen.values()]

        try:
            subjects = client.list_subjects(domain=domain, lang="ind", max_pages=30)
        except BPSApiError as exc:
            subjects = []
            d["errors"].append({"stage": "subjects", "error": str(exc)})

        construction_subjects: list[Mapping[str, Any]] = []
        for row in subjects:
            if "konstruksi" in row_text(row):
                construction_subjects.append(row)
        d["subject_candidates"] = [dict(x) for x in construction_subjects]

        variables: dict[str, Mapping[str, Any]] = {}
        for subject in construction_subjects:
            sid = candidate_id(subject, ("sub_id", "subject_id", "id"))
            if sid is None:
                continue
            try:
                rows = client.list_variables(
                    domain=domain, lang="ind", subject=int(sid), max_pages=30
                )
            except (BPSApiError, ValueError) as exc:
                d["errors"].append({"stage": f"variables:{sid}", "error": str(exc)})
                continue
            for row in rows:
                text = row_text(row)
                if relevant(text):
                    vid = candidate_id(row, ("var_id", "id"))
                    if vid is not None:
                        variables[vid] = row
        d["variable_candidates"] = [dict(x) for x in variables.values()]

        for vid, row in variables.items():
            try:
                periods = client.list_periods(
                    domain=domain, lang="ind", var=int(vid), max_pages=30
                )
            except (BPSApiError, ValueError) as exc:
                d["errors"].append({"stage": f"periods:{vid}", "error": str(exc)})
                continue
            labels = source_period_labels(periods)
            if TARGET_YEAR in labels:
                d["variables_with_2005"].append({
                    "variable": dict(row),
                    "period_labels": labels,
                    "period_rows": [dict(x) for x in periods],
                })

        report["domains"][domain] = d

    target = report["target_var_216"]
    try:
        target["derived_variables"] = [
            dict(x) for x in client.list_derived_variables(
                domain="0000", lang="ind", var=TARGET_VAR, max_pages=30
            )
        ]
    except BPSApiError as exc:
        target["errors"].append({"stage": "derived_variables", "error": str(exc)})

    try:
        target["derived_periods"] = [
            dict(x) for x in client.list_derived_periods(
                domain="0000", lang="ind", var=TARGET_VAR, max_pages=30
            )
        ]
    except BPSApiError as exc:
        target["errors"].append({"stage": "derived_periods", "error": str(exc)})

    try:
        target["dynamic_2005"] = dict(client.get_dynamic_data(
            domain="0000", lang="ind", var=TARGET_VAR, th=TARGET_TH_ID
        ))
    except BPSApiError as exc:
        target["errors"].append({"stage": "dynamic_2005_th_id", "error": str(exc)})
        try:
            target["dynamic_2005"] = dict(client.get_dynamic_data(
                domain="0000", lang="ind", var=TARGET_VAR, th=TARGET_YEAR
            ))
        except BPSApiError as exc2:
            target["errors"].append({"stage": "dynamic_2005_year", "error": str(exc2)})

    path = OUTDIR / "bps-legacy-construction-qualification-2005-surfaces.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    dynamic = target["dynamic_2005"]
    dynamic_keys = sorted(dynamic.keys()) if isinstance(dynamic, Mapping) else []
    print(json.dumps({
        "domains": {
            domain: {
                "static_candidates": len(data["static_candidates"]),
                "subject_candidates": len(data["subject_candidates"]),
                "variable_candidates": len(data["variable_candidates"]),
                "variables_with_2005": len(data["variables_with_2005"]),
                "errors": len(data["errors"]),
            }
            for domain, data in report["domains"].items()
        },
        "target_var_216": {
            "derived_variables": len(target["derived_variables"]),
            "derived_periods": len(target["derived_periods"]),
            "dynamic_2005_available": isinstance(dynamic, Mapping),
            "dynamic_keys": dynamic_keys,
            "errors": len(target["errors"]),
        },
        "output": path.as_posix(),
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
