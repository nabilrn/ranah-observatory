#!/usr/bin/env python3
from __future__ import annotations

import base64
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
TARGET_TURVARS = {
    454: "Kecil",
    455: "Menengah",
    456: "Besar",
    457: "Jumlah",
}
TARGET_SUMBAR_VERVAR = 1300
TARGET_CSA_ID = "MjE2IzI="


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


def datacontent_key(vervar: int, var: int, turvar: int, th: int, turth: int = 0) -> str:
    return f"{vervar}{var}{turvar}{th}{turth}"


def main() -> int:
    key = os.environ.get("BPS_API_KEY", "").strip()
    if not key:
        raise SystemExit("BPS_API_KEY is required")

    OUTDIR.mkdir(parents=True, exist_ok=True)
    client = BPSClient(key, timeout=60, retries=2, retry_backoff_seconds=1.0)
    report: dict[str, Any] = {
        "schema": "ranah-observatory/bps-legacy-construction-qualification-2005-surfaces/v4",
        "purpose": (
            "Search official BPS legacy WebAPI surfaces for 2005 construction qualification data, "
            "inspect variable 216 sourced from Direktori Perusahaan Konstruksi, and resolve its "
            "public CSA statistics-table object 216#2."
        ),
        "api_key_persisted": False,
        "domains": {},
        "target_var_216": {
            "domain": "0000",
            "var_id": TARGET_VAR,
            "year": TARGET_YEAR,
            "th_id": TARGET_TH_ID,
            "csa_encoded_id": TARGET_CSA_ID,
            "csa_decoded_id": base64.b64decode(TARGET_CSA_ID).decode("utf-8"),
            "csa_tablestatistic_view": None,
            "derived_variables": [],
            "derived_periods": [],
            "dynamic_by_turvar": {},
            "sumbar_2005": {},
            "sumbar_2005_reconciliation": None,
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
        target["csa_tablestatistic_view"] = dict(client._request(
            "api/view",
            {
                "model": "tablestatistic",
                "domain": "0000",
                "lang": "ind",
                "id": TARGET_CSA_ID,
            },
        ))
    except BPSApiError as exc:
        target["errors"].append({"stage": "csa_tablestatistic_view", "error": str(exc)})

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

    for turvar_id, label in TARGET_TURVARS.items():
        try:
            dynamic = dict(client.get_dynamic_data(
                domain="0000",
                lang="ind",
                var=TARGET_VAR,
                th=TARGET_TH_ID,
                turvar=turvar_id,
            ))
        except BPSApiError as exc:
            target["errors"].append({"stage": f"dynamic_2005_turvar:{turvar_id}", "error": str(exc)})
            continue
        target["dynamic_by_turvar"][str(turvar_id)] = dynamic
        content = dynamic.get("datacontent")
        value = None
        if isinstance(content, Mapping):
            key_name = datacontent_key(
                TARGET_SUMBAR_VERVAR, TARGET_VAR, turvar_id, TARGET_TH_ID, 0
            )
            value = content.get(key_name)
        target["sumbar_2005"][label] = value

    values = target["sumbar_2005"]
    small = values.get("Kecil")
    medium = values.get("Menengah")
    large = values.get("Besar")
    total = values.get("Jumlah")
    if all(isinstance(x, (int, float)) for x in (small, medium, large, total)):
        component_sum = small + medium + large
        target["sumbar_2005_reconciliation"] = {
            "component_sum": component_sum,
            "reported_total": total,
            "difference": component_sum - total,
            "exact": component_sum == total,
        }

    path = OUTDIR / "bps-legacy-construction-qualification-2005-surfaces.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    csa = target["csa_tablestatistic_view"]
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
            "csa_available": isinstance(csa, Mapping) and str(csa.get("data-availability", "")) == "available",
            "csa_keys": sorted(csa.keys()) if isinstance(csa, Mapping) else [],
            "derived_variables": len(target["derived_variables"]),
            "sumbar_2005": target["sumbar_2005"],
            "reconciliation": target["sumbar_2005_reconciliation"],
            "errors": len(target["errors"]),
        },
        "output": path.as_posix(),
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
