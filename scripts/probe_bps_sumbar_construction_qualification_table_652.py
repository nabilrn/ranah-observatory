#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any, Mapping

from bps_client import BPSApiError, BPSClient

DOMAIN = "1300"
TARGET_TABLE_ID = 652
TARGET_SOURCE_NUMBER = 2
TARGET_ENCODED_ID = "NjUyIzI="
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


def static_relevant(row: Mapping[str, Any]) -> bool:
    text = row_text(row)
    return "konstruksi" in text and (
        "kualifikasi" in text or ("usaha" in text and "perusahaan" in text)
    )


def variable_relevant(row: Mapping[str, Any]) -> bool:
    text = row_text(row)
    return (
        "kualifikasi" in text
        or "kode kualifikasi" in text
        or ("usaha" in text and "perusahaan" in text)
        or "banyaknya perusahaan" in text
    )


def candidate_id(row: Mapping[str, Any]) -> int | None:
    for key in ("var_id", "id", "table_id", "sub_id", "subject_id"):
        value = row.get(key)
        try:
            if value is not None:
                return int(value)
        except (TypeError, ValueError):
            continue
    return None


def exact_period_labels(
    csa: Mapping[str, Any] | None,
    legacy_periods: Mapping[str, list[Mapping[str, Any]]],
) -> list[str]:
    """Return only exact source-native period labels; never substring-scan metadata."""
    labels: set[str] = set()
    if isinstance(csa, Mapping):
        for value in csa.get("available_years", []) or []:
            labels.add(str(value).strip())
        for row in csa.get("tahun", []) or []:
            if isinstance(row, Mapping) and row.get("label") is not None:
                labels.add(str(row["label"]).strip())
    for rows in legacy_periods.values():
        for row in rows:
            for key in ("label", "tahun", "year", "th"):
                value = row.get(key)
                if value is not None:
                    labels.add(str(value).strip())
    return sorted(label for label in labels if label)


def main() -> int:
    key = os.environ.get("BPS_API_KEY", "").strip()
    if not key:
        raise SystemExit("BPS_API_KEY is required for this bounded WebAPI probe")

    OUTDIR.mkdir(parents=True, exist_ok=True)
    client = BPSClient(key, timeout=60, retries=2, retry_backoff_seconds=1.0)
    report: dict[str, Any] = {
        "schema": "ranah-observatory/bps-sumbar-construction-qualification-table-652-probe/v4",
        "purpose": (
            "Resolve the official BPS CSA table object backing public Sumatera Barat statistics-table "
            "652#2 and determine which source-native periods it exposes."
        ),
        "domain": DOMAIN,
        "public_table": {
            "encoded_id": TARGET_ENCODED_ID,
            "decoded_identity": base64.b64decode(TARGET_ENCODED_ID).decode("utf-8"),
            "expected_decoded_identity": f"{TARGET_TABLE_ID}#{TARGET_SOURCE_NUMBER}",
            "title": TARGET_TITLE,
            "url": PUBLIC_URL,
        },
        "api_key_persisted": False,
        "csa_tablestatistic_view": None,
        "legacy_statictable_652_view": None,
        "legacy_static_table_keyword_candidates": [],
        "legacy_construction_subject_candidates": [],
        "legacy_construction_subject_variables": [],
        "legacy_construction_variable_candidates": [],
        "legacy_candidate_periods": {},
        "errors": [],
    }

    try:
        report["csa_tablestatistic_view"] = client._request(
            "api/view",
            {"model": "tablestatistic", "domain": DOMAIN, "lang": "ind", "id": TARGET_ENCODED_ID},
        )
    except BPSApiError as exc:
        report["errors"].append({"stage": "csa-tablestatistic-view", "error": str(exc)})

    try:
        report["legacy_statictable_652_view"] = client._request(
            "api/view/",
            {"model": "statictable", "domain": DOMAIN, "lang": "ind", "id": TARGET_TABLE_ID},
        )
    except BPSApiError as exc:
        report["errors"].append({"stage": "legacy-statictable-view:652", "error": str(exc)})

    for keyword in ("kualifikasi konstruksi", "usaha perusahaan konstruksi", "kode kualifikasi usaha"):
        try:
            rows = client.list_static_tables(domain=DOMAIN, lang="ind", keyword=keyword, max_pages=3)
        except BPSApiError as exc:
            report["errors"].append({"stage": f"legacy-statictable-list:{keyword}", "error": str(exc)})
            continue
        for row in rows:
            if static_relevant(row) and dict(row) not in report["legacy_static_table_keyword_candidates"]:
                report["legacy_static_table_keyword_candidates"].append(dict(row))

    try:
        subjects = client.list_subjects(domain=DOMAIN, lang="ind", max_pages=20)
    except BPSApiError as exc:
        subjects = []
        report["errors"].append({"stage": "legacy-subjects", "error": str(exc)})
    for row in subjects:
        if "konstruksi" in row_text(row):
            report["legacy_construction_subject_candidates"].append(dict(row))

    seen_vars: dict[int, Mapping[str, Any]] = {}
    for subject in report["legacy_construction_subject_candidates"]:
        sid = candidate_id(subject)
        if sid is None:
            continue
        try:
            rows = client.list_variables(domain=DOMAIN, lang="ind", subject=sid, max_pages=20)
        except BPSApiError as exc:
            report["errors"].append({"stage": f"legacy-variables:subject:{sid}", "error": str(exc)})
            continue
        report["legacy_construction_subject_variables"].extend(dict(row) for row in rows)
        for row in rows:
            if variable_relevant(row):
                vid = candidate_id(row)
                if vid is not None:
                    seen_vars[vid] = row

    report["legacy_construction_variable_candidates"] = [dict(seen_vars[vid]) for vid in sorted(seen_vars)]
    for vid in sorted(seen_vars):
        try:
            rows = client.list_periods(domain=DOMAIN, lang="ind", var=vid, max_pages=20)
            report["legacy_candidate_periods"][str(vid)] = [dict(row) for row in rows]
        except BPSApiError as exc:
            report["errors"].append({"stage": f"legacy-periods:var:{vid}", "error": str(exc)})

    csa = report["csa_tablestatistic_view"]
    csa_map = csa if isinstance(csa, Mapping) else None
    period_labels = exact_period_labels(csa_map, report["legacy_candidate_periods"])
    report["source_native_period_labels"] = period_labels
    report["source_native_2005_period_present"] = "2005" in period_labels

    csa_available = isinstance(csa, Mapping) and str(csa.get("data-availability", "")) == "available"
    csa_years = csa.get("available_years", []) if isinstance(csa, Mapping) else []
    csa_variables = csa.get("var", []) if isinstance(csa, Mapping) else []

    path = OUTDIR / "bps-sumbar-construction-qualification-table-652-probe.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "decoded_identity": report["public_table"]["decoded_identity"],
        "csa_tablestatistic_available": csa_available,
        "csa_available_years": csa_years,
        "csa_variable_labels": [row.get("label") for row in csa_variables if isinstance(row, Mapping)],
        "legacy_statictable_available": (
            isinstance(report["legacy_statictable_652_view"], Mapping)
            and str(report["legacy_statictable_652_view"].get("data-availability", "")) == "available"
        ),
        "source_native_period_labels": period_labels,
        "source_native_2005_period_present": report["source_native_2005_period_present"],
        "error_count": len(report["errors"]),
        "output": path.as_posix(),
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
