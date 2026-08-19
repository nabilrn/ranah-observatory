#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from milestone25_djpk_html_compat import install_djpk_html_compat

install_djpk_html_compat()

import probe_milestone25_djpk_stage1 as stage1

TAG_RE = re.compile(r"<[^>]+>", re.S)


def clean(fragment: str) -> str:
    return stage1.normalize_space(html.unescape(TAG_RE.sub(" ", fragment)).replace("\xa0", " "))


def snippets(text: str, pattern: str, radius: int = 260) -> list[str]:
    found: list[str] = []
    for match in re.finditer(pattern, text, flags=re.I):
        lo = max(0, match.start() - radius)
        hi = min(len(text), match.end() + radius)
        found.append(stage1.normalize_space(text[lo:hi]))
        if len(found) == 8:
            break
    return found


def main() -> int:
    crosswalk = {row["djpk_pemda_selector"]: row for row in stage1.validate_crosswalk(stage1.DEFAULT_CROSSWALK)}
    results = []
    for pemda in ("01", "10"):
        geo = crosswalk[pemda]
        url = stage1.build_url(pemda, 2024)
        status, body, final_url = stage1.fetch_url(url)
        source = body.decode("utf-8", errors="replace")
        parser = stage1.HTMLTableParser()
        parser.feed(source)
        header, table_rows = stage1.find_postur_table(parser.tables)
        accounts = stage1.table_to_accounts(header, table_rows)
        by_label = {row["account_label_normalized"]: row for row in accounts}
        page_text = stage1.normalize_space(parser.all_text)

        # Extract likely selected-jurisdiction/headline fragments directly from
        # source HTML instead of relying on the filter dropdown, which lists all
        # jurisdictions and is therefore not identity evidence.
        raw_candidates = []
        for pattern in (
            r"postur\s+apbd.{0,500}",
            r"realisasi\s+apbd.{0,500}",
            r"lima\s*puluh.{0,200}",
            r"lima\s*puluh.{0,200}",
            r"bukit\s*tinggi.{0,200}",
            r"bukittinggi.{0,200}",
        ):
            raw_candidates.extend(snippets(source, pattern))
        text_candidates = []
        for pattern in (
            r"postur\s+apbd.{0,300}",
            r"realisasi\s+apbd.{0,300}",
            r"(?:kab\.?|kabupaten|kota)\s+[^|]{0,100}(?:lima|bukit)[^|]{0,100}",
        ):
            text_candidates.extend(snippets(page_text, pattern))

        # Selected <option> values are strong identity evidence when present.
        selected_options = [
            clean(match.group(1))
            for match in re.finditer(r"<option\b[^>]*selected[^>]*>(.*?)</option>", source, flags=re.I | re.S)
            if clean(match.group(1))
        ]
        headings = [
            clean(match.group(2))
            for match in re.finditer(r"<(h[1-6]|caption|strong|b)\b[^>]*>(.*?)</\1>", source, flags=re.I | re.S)
            if clean(match.group(2))
        ]
        relevant_headings = [
            value for value in headings
            if any(token in value.casefold() for token in ("lima", "bukit", "postur", "realisasi", "apbd"))
        ]

        results.append(
            {
                "pemda": pemda,
                "expected_source_name": geo["djpk_source_name"],
                "expected_normalized": stage1.normalize_jurisdiction(geo["djpk_source_name"]),
                "status": status,
                "final_url": final_url,
                "selected_options": selected_options,
                "relevant_headings": relevant_headings,
                "raw_candidate_snippets": raw_candidates,
                "text_candidate_snippets": text_candidates,
                "jurisdiction_match": stage1.jurisdiction_matches(page_text, geo["djpk_source_name"]),
                "all_four_locked_accounts_present": all(
                    label in by_label
                    for label in ("pendapatan daerah", "pad", "belanja daerah", "belanja modal")
                ),
            }
        )
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
