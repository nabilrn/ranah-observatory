#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from bps_client import BPSApiError, BPSClient

OUTDIR = Path("probe-output")
DOMAIN = "0000"
TARGETS = [
    {
        "key": "outside_java_profile_2005",
        "title": "Profil Perusahaan Konstruksi di Luar Pulau Jawa 2005",
        "publication_number": "05230.0610",
        "isbn": "979-724-565-9",
        "keywords": [
            "Profil Perusahaan Konstruksi di Luar Pulau Jawa 2005",
            "05230.0610",
            "979-724-565-9",
        ],
    },
    {
        "key": "construction_statistics_2005",
        "title": "Statistik Konstruksi 2005",
        "publication_number": "05230.0607",
        "isbn": "979-724-567-5",
        "keywords": [
            "Statistik Konstruksi 2005",
            "05230.0607",
            "979-724-567-5",
        ],
    },
]


def folded(value: Any) -> str:
    return " ".join(str(value).casefold().split())


def row_text(row: Mapping[str, Any]) -> str:
    return folded(json.dumps(row, ensure_ascii=False, sort_keys=True))


def candidate_id(row: Mapping[str, Any]) -> str | None:
    for key in ("pub_id", "id", "publication_id"):
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def redact_detail(detail: Mapping[str, Any]) -> dict[str, Any]:
    # Publication detail is public metadata. Retain source-native fields but never
    # persist API request URLs or credentials. File/download fields are intentionally
    # retained only if returned by the official WebAPI object itself.
    return {str(k): v for k, v in detail.items() if str(k).casefold() not in {"key", "api_key"}}


def main() -> int:
    key = os.environ.get("BPS_API_KEY", "").strip()
    if not key:
        raise SystemExit("BPS_API_KEY is required")

    OUTDIR.mkdir(parents=True, exist_ok=True)
    client = BPSClient(key, timeout=60, retries=2, retry_backoff_seconds=1.0)
    report: dict[str, Any] = {
        "schema": "ranah-observatory/bps-historical-construction-publication-object-probe/v1",
        "purpose": (
            "Resolve exact historical BPS publication objects for Book II 05230.0610 and "
            "Statistik Konstruksi 2005 05230.0607 using the official publication WebAPI model."
        ),
        "domain": DOMAIN,
        "api_key_persisted": False,
        "targets": [],
        "bounds": {"max_pages_per_keyword": 8, "max_detail_views_per_target": 12},
    }

    for target in TARGETS:
        result: dict[str, Any] = {
            "key": target["key"],
            "expected_title": target["title"],
            "expected_publication_number": target["publication_number"],
            "expected_isbn": target["isbn"],
            "searches": [],
            "candidate_rows": [],
            "candidate_details": [],
            "errors": [],
        }
        seen_rows: dict[str, Mapping[str, Any]] = {}
        for keyword in target["keywords"]:
            try:
                rows = client.list_publications(
                    domain=DOMAIN,
                    lang="ind",
                    keyword=keyword,
                    max_pages=8,
                )
            except BPSApiError as exc:
                result["errors"].append({"stage": f"list:{keyword}", "error": str(exc)})
                continue
            result["searches"].append({"keyword": keyword, "row_count": len(rows)})
            for row in rows:
                text = row_text(row)
                # Retain candidates only when at least one target identity element is
                # present in source-native metadata. This prevents broad construction
                # search results from becoming evidence candidates.
                if not any(
                    folded(value) in text
                    for value in (target["title"], target["publication_number"], target["isbn"])
                ):
                    continue
                cid = candidate_id(row) or json.dumps(row, ensure_ascii=False, sort_keys=True)
                seen_rows[cid] = row

        result["candidate_rows"] = [dict(row) for row in seen_rows.values()]
        for row in list(seen_rows.values())[:12]:
            cid = candidate_id(row)
            if not cid:
                continue
            try:
                detail = client.get_publication(domain=DOMAIN, publication_id=cid, lang="ind")
            except BPSApiError as exc:
                result["errors"].append({"stage": f"detail:{cid}", "error": str(exc)})
                continue
            result["candidate_details"].append({
                "publication_id": cid,
                "detail": redact_detail(detail),
            })

        result["exact_identity_hits"] = [
            item for item in result["candidate_details"]
            if target["publication_number"] in row_text(item["detail"])
            or target["isbn"] in row_text(item["detail"])
            or folded(target["title"]) in row_text(item["detail"])
        ]
        report["targets"].append(result)

    path = OUTDIR / "bps-historical-construction-publication-object-probe.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "targets": {
            target["key"]: {
                "candidate_rows": len(target["candidate_rows"]),
                "candidate_details": len(target["candidate_details"]),
                "exact_identity_hits": len(target["exact_identity_hits"]),
                "errors": len(target["errors"]),
            }
            for target in report["targets"]
        },
        "output": path.as_posix(),
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
