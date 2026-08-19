#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from milestone25_djpk_html_compat import install_djpk_html_compat

install_djpk_html_compat()

import probe_milestone25_djpk_stage1 as stage1

TARGET_LABELS = {
    "pendapatan daerah",
    "pad",
    "belanja daerah",
    "belanja modal",
}


def main() -> int:
    crosswalk = {row["djpk_pemda_selector"]: row for row in stage1.validate_crosswalk(stage1.DEFAULT_CROSSWALK)}
    results = []
    for pemda in ("01", "10"):
        geo = crosswalk[pemda]
        url = stage1.build_url(pemda, 2024)
        status, body, final_url = stage1.fetch_url(url)
        parser = stage1.HTMLTableParser()
        parser.feed(body.decode("utf-8", errors="replace"))
        header, table_rows = stage1.find_postur_table(parser.tables)
        accounts = stage1.table_to_accounts(header, table_rows)
        by_label = {row["account_label_normalized"]: row for row in accounts}
        page_text = stage1.normalize_space(parser.all_text)
        results.append(
            {
                "pemda": pemda,
                "expected_source_name": geo["djpk_source_name"],
                "expected_normalized": stage1.normalize_jurisdiction(geo["djpk_source_name"]),
                "status": status,
                "final_url": final_url,
                "response_bytes": len(body),
                "page_title": parser.title,
                "page_text_prefix": page_text[:1000],
                "page_text_normalized_prefix": stage1.normalize_jurisdiction(page_text)[:1000],
                "jurisdiction_match": stage1.jurisdiction_matches(page_text, geo["djpk_source_name"]),
                "year_match": "2024" in page_text,
                "december_match": bool(stage1.re.search(r"realisasi\s+apbd\s+s\.?\s*d\.?\s+desember", page_text, flags=stage1.re.IGNORECASE)),
                "account_count": len(accounts),
                "target_accounts": {
                    label: by_label.get(label)
                    for label in sorted(TARGET_LABELS)
                },
                "missing_target_labels": sorted(label for label in TARGET_LABELS if label not in by_label),
            }
        )
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
