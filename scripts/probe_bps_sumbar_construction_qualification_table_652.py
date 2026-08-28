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


def decode_public_identity() -> str:
    return base64.b64decode(TARGET_ENCODED_ID).decode("utf-8")


def main() -> int:
    key = os.environ.get("BPS_API_KEY", "").strip()
    if not key:
        raise SystemExit("BPS_API_KEY is required for this bounded WebAPI probe")

    OUTDIR.mkdir(parents=True, exist_ok=True)
    client = BPSClient(key, timeout=60, retries=2, retry_backoff_seconds=1.0)

    report: dict[str, Any] = {
        "schema": "ranah-observatory/bps-sumbar-construction-qualification-table-652-probe/v3",
        "purpose": (
            "Resolve the official BPS CSA table object backing public Sumatera Barat statistics-table "
            "652#2 and determine which BPS source family/transport it exposes."
        ),
        "domain": DOMAIN,
        "public_table": {
            "encoded_id": TARGET_ENCODED_ID,
            "decoded_identity": decode_public_identity(),
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

    # Correct current-site contract: statistics-table pages use CSA `tablestatistic`
    # identities. The encoded ID is taken verbatim from the verified public page URL.
    try:
        report["csa_tablestatistic_view"] = client._request(
            "api/view",
            {
                "model": "tablestatistic",
                "domain": DOMAIN,
                "lang": "ind",
                "id": TARGET_ENCODED_ID,
            },
        )
    except BPSApiError as exc:
        report["errors"].append({"stage": "csa-tablestatistic-view", "error": str(exc)})

    # Preserve the disproven legacy hypothesis as an explicit negative control.
    try:
        report["legacy_statictable_652_view"] = client._request(
            "api/view/",
            {
                "model": "statictable",
                "domain": DOMAIN,
                "lang": "ind",
                "id": TARGET_TABLE_ID,
            },
        )
    except BPSApiError as exc:
        report["errors"].append({"stage": "legacy-statictable-view:652", "error": str(exc)})

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
            report["errors"].append({"stage": f"legacy-statictable-list:{keyword}", "error": str(exc)})
            continue
        for row in rows:
            if static_relevant(row):
                item = dict(row)
                if item not in report["legacy_static_table_keyword_candidates"]:
                    report["legacy_static_table_keyword_candidates"].append(item)

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

    report["legacy_construction_variable_candidates"] = [
        dict(seen_vars[vid]) for vid in sorted(seen_vars)
    ]
    for vid in sorted(seen_vars):
        try:
            periods = client.list_periods(domain=DOMAIN, lang="ind", var=vid, max_pages=20)
            report["legacy_candidate_periods"][str(vid)] = [dict(row) for row in periods]
        except BPSApiError as exc:
            report["errors"].append({"stage": f"legacy-periods:var:{vid}", "error": str(exc)})

    report["year_mentions"] = collect_year_mentions(
        {
            "csa_tablestatistic_view": report["csa_tablestatistic_view"],
            "legacy_statictable_652_view": report["legacy_statictable_652_view"],
            "legacy_static_table_keyword_candidates": report["legacy_static_table_keyword_candidates"],
            "legacy_construction_variable_candidates": report["legacy_construction_variable_candidates"],
            "legacy_candidate_periods": report["legacy_candidate_periods"],
        }
    )
    report["source_native_2005_mention_present"] = any(
        "2005" in str(hit["value"]) for hit in report["year_mentions"]
    )

    csa = report["csa_tablestatistic_view"]
    csa_available = isinstance(csa, Mapping) and str(csa.get("data-availability", "")) == "available"
    csa_years = csa.get("available_years", []) if isinstance(csa, Mapping) else []
    csa_variables = csa.get("var", []) if isinstance(csa, Mapping) else []

    path = OUTDIR / "bps-sumbar-construction-qualification-table-652-probe.json"
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    summary = {
        "decoded_identity": report["public_table"]["decoded_identity"],
        "csa_tablestatistic_available": csa_available,
        "csa_available_years": csa_years,
        "csa_variable_labels": [row.get("label") for row in csa_variables if isinstance(row, Mapping)],
        "legacy_statictable_available": (
            isinstance(report["legacy_statictable_652_view"], Mapping)
            and str(report["legacy_statictable_652_view"].get("data-availability", "")) == "available"
        ),
        "source_native_2005_mention_present": report["source_native_2005_mention_present"],
        "error_count": len(report["errors"]),
        "output": path.as_posix(),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
