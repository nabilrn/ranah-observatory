#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from bps_client import BPSApiError, BPSClient

DOMAIN = "1300"
CSA_SUBJECT_ID = 559
OUTDIR = Path("probe-output")
MAX_PAGES = 20
PER_PAGE = 100
MAX_DETAIL_VIEWS = 40


def text(row: Mapping[str, Any]) -> str:
    return " ".join(json.dumps(row, ensure_ascii=False, sort_keys=True).casefold().split())


def relevant(row: Mapping[str, Any]) -> bool:
    value = text(row)
    if "konstruksi" not in value:
        return False
    return any(token in value for token in ("kualifikasi", "perusahaan", "usaha", "direktori"))


def data_parts(response: Mapping[str, Any]) -> tuple[Mapping[str, Any], list[Mapping[str, Any]]]:
    data = response.get("data")
    if isinstance(data, list) and len(data) >= 2:
        info = data[0] if isinstance(data[0], Mapping) else {}
        rows = data[1] if isinstance(data[1], list) else []
        return info, [row for row in rows if isinstance(row, Mapping)]
    return {}, []


def encoded_id(row: Mapping[str, Any]) -> str | None:
    for key in ("id", "table_id", "tableid", "id_tabel"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def exact_years(view: Mapping[str, Any]) -> list[str]:
    years: set[str] = set()
    for value in view.get("available_years", []) or []:
        years.add(str(value).strip())
    for row in view.get("tahun", []) or []:
        if isinstance(row, Mapping) and row.get("label") is not None:
            years.add(str(row["label"]).strip())
    return sorted(year for year in years if year)


def main() -> int:
    key = os.environ.get("BPS_API_KEY", "").strip()
    if not key:
        raise SystemExit("BPS_API_KEY is required")

    OUTDIR.mkdir(parents=True, exist_ok=True)
    client = BPSClient(key, timeout=60, retries=2, retry_backoff_seconds=1.0)
    report: dict[str, Any] = {
        "schema": "ranah-observatory/bps-csa-construction-historical-candidates-probe/v1",
        "purpose": (
            "Enumerate only the official BPS CSA table catalog for Sumatera Barat subject 559, "
            "then resolve construction-establishment/qualification candidates and inspect exact source-native periods."
        ),
        "domain": DOMAIN,
        "csa_subject_id": CSA_SUBJECT_ID,
        "api_key_persisted": False,
        "catalog_pages": [],
        "relevant_catalog_rows": [],
        "candidate_views": [],
        "errors": [],
        "bounds": {"max_pages": MAX_PAGES, "per_page": PER_PAGE, "max_detail_views": MAX_DETAIL_VIEWS},
    }

    all_rows: list[Mapping[str, Any]] = []
    total_pages = 1
    for page in range(1, MAX_PAGES + 1):
        try:
            response = client._request(
                "api/list",
                {
                    "model": "tablestatistic",
                    "domain": DOMAIN,
                    "subject": CSA_SUBJECT_ID,
                    "page": page,
                    "perpage": PER_PAGE,
                },
            )
        except BPSApiError as exc:
            report["errors"].append({"stage": f"catalog-page:{page}", "error": str(exc)})
            break
        info, rows = data_parts(response)
        total_pages = int(info.get("pages", total_pages) or total_pages)
        report["catalog_pages"].append({
            "page": page,
            "pages": total_pages,
            "count": len(rows),
            "data_availability": response.get("data-availability"),
        })
        all_rows.extend(rows)
        if page >= total_pages:
            break

    seen_rows: set[str] = set()
    candidates: list[Mapping[str, Any]] = []
    for row in all_rows:
        fingerprint = json.dumps(row, ensure_ascii=False, sort_keys=True)
        if fingerprint in seen_rows:
            continue
        seen_rows.add(fingerprint)
        if relevant(row):
            candidates.append(row)
            report["relevant_catalog_rows"].append(dict(row))

    for row in candidates[:MAX_DETAIL_VIEWS]:
        tid = encoded_id(row)
        if not tid:
            report["errors"].append({"stage": "candidate-id", "row": dict(row), "error": "no encoded id"})
            continue
        try:
            view = client._request(
                "api/view",
                {"model": "tablestatistic", "domain": DOMAIN, "lang": "ind", "id": tid},
            )
        except BPSApiError as exc:
            report["errors"].append({"stage": f"candidate-view:{tid}", "error": str(exc)})
            continue
        var_rows = view.get("var", []) if isinstance(view, Mapping) else []
        labels = [str(item.get("label", "")) for item in var_rows if isinstance(item, Mapping)]
        years = exact_years(view) if isinstance(view, Mapping) else []
        report["candidate_views"].append({
            "encoded_id": tid,
            "catalog_row": dict(row),
            "status": view.get("status") if isinstance(view, Mapping) else None,
            "data_availability": view.get("data-availability") if isinstance(view, Mapping) else None,
            "available_years": years,
            "contains_2005_period": "2005" in years,
            "variable_labels": labels,
            "subject_texts": [
                str(item.get("label", ""))
                for item in (view.get("subject", []) if isinstance(view, Mapping) else [])
                if isinstance(item, Mapping)
            ],
            "source_subject_texts": [
                str(item.get("subj", "")) for item in var_rows if isinstance(item, Mapping)
            ],
        })

    report["candidate_with_2005_period"] = [
        item for item in report["candidate_views"] if item["contains_2005_period"]
    ]
    report["exact_2005_candidate_count"] = len(report["candidate_with_2005_period"])

    path = OUTDIR / "bps-csa-construction-historical-candidates-probe.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "catalog_rows_seen": len(all_rows),
        "relevant_catalog_rows": len(report["relevant_catalog_rows"]),
        "candidate_views": len(report["candidate_views"]),
        "exact_2005_candidate_count": report["exact_2005_candidate_count"],
        "error_count": len(report["errors"]),
        "output": path.as_posix(),
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
