#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from bps_client import BPSApiError, BPSClient

DOMAIN = "1300"
TARGET_TABLE_ID = 652
TARGET_TITLE = (
    "Banyaknya Usaha/Perusahaan Konstruksi Menurut Kabupaten/Kota dan "
    "Kode Kualifikasi Usaha di Sumatera Barat"
)
PUBLIC_URL = (
    "https://sumbar.bps.go.id/id/statistics-table/2/NjUyIzI=/"
    "banyaknya-usaha-perusahaan-konstruksi-menurut-kabupaten-kota-dan-"
    "kode-kualifikasi-usaha-di-sumatera-barat.html"
)
OUTDIR = Path("probe-output")


def folded(value: Any) -> str:
    return " ".join(str(value).casefold().split())


def row_text(row: Mapping[str, Any]) -> str:
    return folded(json.dumps(row, ensure_ascii=False, sort_keys=True))


def relevant(row: Mapping[str, Any]) -> bool:
    text = row_text(row)
    tokens = ("konstruksi", "kualifikasi")
    return all(token in text for token in tokens)


def collect_year_mentions(node: Any, path: str = "$") -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    if isinstance(node, Mapping):
        for key, value in node.items():
            hits.extend(collect_year_mentions(value, f"{path}.{key}"))
        return hits
    if isinstance(node, list):
        for idx, value in enumerate(node):
            hits.extend(collect_year_mentions(value, f"{path}[{idx}]"))
        return hits
    text = str(node)
    if any(year in text for year in ("2003", "2004", "2005", "2006")):
        hits.append({"path": path, "value": node})
    return hits


def candidate_id(row: Mapping[str, Any]) -> int | None:
    for key in ("var_id", "id", "table_id", "sub_id", "subject_id"):
        value = row.get(key)
        try:
            if value is not None:
                return int(value)
        except (TypeError, ValueError):
            continue
    return None


def main() -> int:
    key = os.environ.get("BPS_API_KEY", "").strip()
    if not key:
        raise SystemExit("BPS_API_KEY is required for this bounded WebAPI probe")

    OUTDIR.mkdir(parents=True, exist_ok=True)
    client = BPSClient(key, timeout=60, retries=2, retry_backoff_seconds=1.0)

    report: dict[str, Any] = {
        "schema": "ranah-observatory/bps-sumbar-construction-qualification-table-652-probe/v1",
        "purpose": (
            "Identify the official BPS WebAPI object backing public Sumatera Barat statistics-table "
            "652#2 and determine whether source-native 2005 data are exposed."
        ),
        "domain": DOMAIN,
        "public_table": {
            "encoded_identity": "652#2",
            "table_id_hypothesis": TARGET_TABLE_ID,
            "title": TARGET_TITLE,
            "url": PUBLIC_URL,
        },
        "api_key_persisted": False,
        "static_table_keyword_candidates": [],
        "static_table_652_view": None,
        "construction_subject_candidates": [],
        "construction_variable_candidates": [],
        "candidate_periods": {},
        "errors": [],
    }

    for keyword in (
        "kualifikasi konstruksi",
        "usaha perusahaan konstruksi",
        "kode kualifikasi usaha",
    ):
        try:
            rows = client.list_static_tables(
                domain=DOMAIN, lang="ind", keyword=keyword, max_pages=3
            )
        except BPSApiError as exc:
            report["errors"].append({"stage": f"statictable-list:{keyword}", "error": str(exc)})
            continue
        for row in rows:
            if relevant(row):
                item = dict(row)
                if item not in report["static_table_keyword_candidates"]:
                    report["static_table_keyword_candidates"].append(item)

    try:
        view = client._request(  # bounded probe of verified numeric hypothesis from public URL
            "api/view/",
            {
                "model": "statictable",
                "domain": DOMAIN,
                "lang": "ind",
                "id": TARGET_TABLE_ID,
            },
        )
        report["static_table_652_view"] = view
    except BPSApiError as exc:
        report["errors"].append({"stage": "statictable-view:652", "error": str(exc)})

    try:
        subjects = client.list_subjects(domain=DOMAIN, lang="ind", max_pages=20)
    except BPSApiError as exc:
        subjects = []
        report["errors"].append({"stage": "subjects", "error": str(exc)})

    for row in subjects:
        if "konstruksi" in row_text(row):
            report["construction_subject_candidates"].append(dict(row))

    seen_vars: dict[int, Mapping[str, Any]] = {}
    for subject in report["construction_subject_candidates"]:
        sid = candidate_id(subject)
        if sid is None:
            continue
        try:
            rows = client.list_variables(
                domain=DOMAIN, lang="ind", subject=sid, max_pages=20
            )
        except BPSApiError as exc:
            report["errors"].append({"stage": f"variables:subject:{sid}", "error": str(exc)})
            continue
        for row in rows:
            if relevant(row):
                vid = candidate_id(row)
                if vid is not None:
                    seen_vars[vid] = row

    report["construction_variable_candidates"] = [
        dict(seen_vars[vid]) for vid in sorted(seen_vars)
    ]

    for vid in sorted(seen_vars):
        try:
            periods = client.list_periods(domain=DOMAIN, lang="ind", var=vid, max_pages=20)
        except BPSApiError as exc:
            report["errors"].append({"stage": f"periods:var:{vid}", "error": str(exc)})
            continue
        report["candidate_periods"][str(vid)] = [dict(row) for row in periods]

    report["year_mentions"] = collect_year_mentions(
        {
            "static_table_keyword_candidates": report["static_table_keyword_candidates"],
            "static_table_652_view": report["static_table_652_view"],
            "construction_variable_candidates": report["construction_variable_candidates"],
            "candidate_periods": report["candidate_periods"],
        }
    )
    report["source_native_2005_mention_present"] = any(
        "2005" in str(hit["value"]) for hit in report["year_mentions"]
    )

    path = OUTDIR / "bps-sumbar-construction-qualification-table-652-probe.json"
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    summary = {
        "static_candidates": len(report["static_table_keyword_candidates"]),
        "table_652_view_available": report["static_table_652_view"] is not None,
        "construction_subjects": len(report["construction_subject_candidates"]),
        "construction_variables": len(report["construction_variable_candidates"]),
        "source_native_2005_mention_present": report["source_native_2005_mention_present"],
        "error_count": len(report["errors"]),
        "output": path.as_posix(),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
