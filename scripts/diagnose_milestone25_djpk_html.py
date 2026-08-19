#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
from collections import defaultdict
from typing import Any

from probe_milestone25_djpk_taxonomy import YEARS, build_url, fetch_url, normalize_label, normalize_space

ROW_RE = re.compile(r"<tr\b(?P<row_attrs>[^>]*)>(?P<body>.*?)<tr\s*/\s*>", re.I | re.S)
CELL_RE = re.compile(r"<td\b(?P<attrs>[^>]*)>(?P<body>.*?)</td\s*>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>", re.S)
INDENT_RE = re.compile(r"text-indent\s*:\s*([0-9.]+)em", re.I)
TARGET_LABELS = {
    "pendapatan",
    "pendapatan daerah",
    "pad",
    "belanja",
    "belanja daerah",
    "belanja modal",
    "belanja pegawai",
    "dana perimbangan",
    "tkdd",
    "pendapatan transfer pemerintah pusat",
}


def cell_text(fragment: str) -> str:
    plain = TAG_RE.sub(" ", fragment)
    return normalize_space(html.unescape(plain).replace("\xa0", " "))


def extract_rows(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source_order, match in enumerate(ROW_RE.finditer(text), start=1):
        cells = list(CELL_RE.finditer(match.group("body")))
        if len(cells) < 5:
            continue
        label = cell_text(cells[1].group("body"))
        if not label:
            continue
        label_attrs = cells[1].group("attrs")
        indent_match = INDENT_RE.search(label_attrs)
        rows.append(
            {
                "source_order": source_order,
                "account_label": label,
                "account_label_normalized": normalize_label(label),
                "indent_em": float(indent_match.group(1)) if indent_match else 0.0,
                "budget_raw": cell_text(cells[2].group("body")),
                "realization_raw": cell_text(cells[3].group("body")),
                "percent_raw": cell_text(cells[4].group("body")),
                "row_attrs": normalize_space(match.group("row_attrs")),
            }
        )
    return rows


def main() -> int:
    yearly: list[dict[str, Any]] = []
    all_duplicate_groups: list[dict[str, Any]] = []
    cross_year_signature: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for year in YEARS:
        url = build_url(year)
        status, body, final_url = fetch_url(url)
        text = body.decode("utf-8", errors="replace")
        rows = extract_rows(text)
        by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            by_label[row["account_label_normalized"]].append(row)

        duplicates: list[dict[str, Any]] = []
        for label, group in sorted(by_label.items()):
            if len(group) <= 1:
                continue
            values_identical = len({(r["budget_raw"], r["realization_raw"], r["percent_raw"]) for r in group}) == 1
            hierarchy_distinct = len({r["indent_em"] for r in group}) == len(group)
            item = {
                "year": year,
                "label": label,
                "occurrence_count": len(group),
                "values_identical": values_identical,
                "hierarchy_distinct": hierarchy_distinct,
                "rows": group,
            }
            duplicates.append(item)
            all_duplicate_groups.append(item)
            cross_year_signature[label].append(
                {
                    "year": year,
                    "count": len(group),
                    "indents": sorted(r["indent_em"] for r in group),
                    "values_identical": values_identical,
                }
            )

        targets = [row for row in rows if row["account_label_normalized"] in TARGET_LABELS]
        yearly.append(
            {
                "year": year,
                "status": status,
                "final_url": final_url,
                "response_bytes": len(body),
                "parsed_body_row_count": len(rows),
                "duplicate_label_count": len(duplicates),
                "duplicates": duplicates,
                "target_rows": targets,
            }
        )

    unsafe_duplicates = [item for item in all_duplicate_groups if not item["values_identical"]]
    stable_identical_hierarchy_duplicates = {
        label: signatures
        for label, signatures in sorted(cross_year_signature.items())
        if len(signatures) == len(YEARS)
        and all(item["values_identical"] for item in signatures)
        and len({tuple(item["indents"]) for item in signatures}) == 1
    }
    payload = {
        "diagnostic_only": True,
        "years": YEARS,
        "year_count": len(YEARS),
        "total_duplicate_groups": len(all_duplicate_groups),
        "unsafe_nonidentical_duplicate_group_count": len(unsafe_duplicates),
        "unsafe_nonidentical_duplicate_groups": unsafe_duplicates,
        "stable_identical_hierarchy_duplicates": stable_identical_hierarchy_duplicates,
        "yearly": yearly,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
