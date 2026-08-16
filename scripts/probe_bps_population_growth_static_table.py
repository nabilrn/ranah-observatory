#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Mapping

from scripts.bps_client import BPSApiError, BPSClient

DOMAIN = "1300"
TARGET_PHRASES = ("laju pertumbuhan penduduk", "kabupaten/kota")
KEYWORDS = ("laju pertumbuhan penduduk", "pertumbuhan penduduk")


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def is_relevant_title(title: str) -> bool:
    lowered = title.casefold()
    return all(phrase in lowered for phrase in TARGET_PHRASES)


def detail_static_table(client: BPSClient, table_id: str) -> Mapping[str, Any]:
    payload = client._request(  # bounded probe; uses the client's retry/auth transport contract
        "view",
        {"model": "statictable", "domain": DOMAIN, "lang": "ind", "id": table_id},
    )
    if str(payload.get("data-availability", "")) != "available":
        raise BPSApiError(f"static table {table_id} is not available")
    data = payload.get("data")
    if not isinstance(data, Mapping):
        raise BPSApiError(f"static table {table_id} detail is missing its data object")
    return data


def collect_relevant(rows: list[Mapping[str, Any]], discovered: dict[str, Mapping[str, Any]]) -> list[dict[str, str]]:
    relevant: list[dict[str, str]] = []
    for row in rows:
        table_id = normalize_text(row.get("table_id") or row.get("id"))
        title = normalize_text(row.get("title"))
        if not table_id or not is_relevant_title(title):
            continue
        discovered[table_id] = row
        relevant.append({"table_id": table_id, "title": title})
    return relevant


def discover(client: BPSClient) -> dict[str, Any]:
    discovered: dict[str, Mapping[str, Any]] = {}
    search_evidence: list[dict[str, Any]] = []

    for keyword in KEYWORDS:
        rows = client.list_static_tables(domain=DOMAIN, keyword=keyword, max_pages=20)
        search_evidence.append(
            {
                "mode": "keyword",
                "keyword": keyword,
                "api_rows_returned": len(rows),
                "relevant_rows": collect_relevant(rows, discovered),
            }
        )

    # New-generation website tables may not be indexed by the legacy keyword
    # endpoint. Enumerate the bounded 2020 static-table slice before concluding
    # that the WebAPI lane does not expose the known official website table.
    year_rows = client.list_static_tables(domain=DOMAIN, year=2020, max_pages=100)
    search_evidence.append(
        {
            "mode": "year_enumeration",
            "year": 2020,
            "api_rows_returned": len(year_rows),
            "relevant_rows": collect_relevant(year_rows, discovered),
        }
    )

    candidates: list[dict[str, Any]] = []
    for table_id, list_row in sorted(discovered.items(), key=lambda item: item[0]):
        detail = detail_static_table(client, table_id)
        title = normalize_text(detail.get("title") or list_row.get("title"))
        table_html = str(detail.get("table") or "")
        excel = normalize_text(detail.get("excel"))
        candidates.append(
            {
                "table_id": table_id,
                "title": title,
                "subject_id": normalize_text(detail.get("subj_id") or list_row.get("subj_id")),
                "created_at": normalize_text(detail.get("cr_date")),
                "updated_at": normalize_text(detail.get("updt_date")),
                "excel_locator": excel,
                "has_html_table": bool(table_html.strip()),
                "html_table_length": len(table_html),
                "html_table_sha256": hashlib.sha256(table_html.encode("utf-8")).hexdigest() if table_html else "",
                "mentions_2010_2020": "2010" in table_html and "2020" in table_html,
                "mentions_population_growth": "laju pertumbuhan" in table_html.casefold(),
                "raw_detail": dict(detail),
            }
        )

    return {
        "schema": "ranah-observatory/bps-population-growth-static-table-probe/v1",
        "domain": DOMAIN,
        "source": "BPS WebAPI official Static Table API",
        "search_evidence": search_evidence,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "lane_decision": (
            "official_machine_readable_static_table_candidates_found"
            if candidates
            else "official_web_table_known_but_legacy_webapi_static_table_index_does_not_expose_candidate"
        ),
        "canonical_promotion_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover official BPS Sumbar static-table lane for population growth")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    api_key = os.getenv("BPS_API_KEY", "").strip()
    if not api_key:
        print("error: BPS_API_KEY is required", file=sys.stderr)
        return 2

    try:
        report = discover(BPSClient(api_key))
    except (BPSApiError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "candidates"}, ensure_ascii=False, indent=2))
    print(f"candidate_count={report['candidate_count']}")
    for candidate in report["candidates"]:
        print(f"candidate {candidate['table_id']}: {candidate['title']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
