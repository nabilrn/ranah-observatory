#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from probe_milestone25_djpk_taxonomy import HTMLTableParser, build_url, fetch_url, normalize_space


def snippets(text: str, marker: str, radius: int = 350) -> list[str]:
    out: list[str] = []
    start = 0
    lower = text.casefold()
    needle = marker.casefold()
    while len(out) < 5:
        idx = lower.find(needle, start)
        if idx < 0:
            break
        lo = max(0, idx - radius)
        hi = min(len(text), idx + len(marker) + radius)
        out.append(text[lo:hi].replace('\n', ' ').replace('\r', ' '))
        start = idx + len(marker)
    return out


def main() -> int:
    url = build_url(2024)
    status, body, final_url = fetch_url(url)
    text = body.decode('utf-8', errors='replace')
    parser = HTMLTableParser()
    parser.feed(text)
    markers = ['Pendapatan Daerah', 'PAD', 'Belanja Modal', 'Realisasi', 'datacontent', 'postur', 'tbody', 'ajax', 'apbd']
    payload = {
        'status': status,
        'url': url,
        'final_url': final_url,
        'bytes': len(body),
        'title': parser.title,
        'table_count': len(parser.tables),
        'table_row_counts': [len(t) for t in parser.tables],
        'tag_counts': {
            'tr_open': len(re.findall(r'<tr\\b', text, flags=re.I)),
            'td_open': len(re.findall(r'<td\\b', text, flags=re.I)),
            'tbody_open': len(re.findall(r'<tbody\\b', text, flags=re.I)),
            'script_open': len(re.findall(r'<script\\b', text, flags=re.I)),
        },
        'marker_counts': {marker: text.casefold().count(marker.casefold()) for marker in markers},
        'text_marker_counts': {marker: parser.all_text.casefold().count(marker.casefold()) for marker in markers},
        'marker_snippets': {marker: snippets(text, marker) for marker in markers},
        'text_prefix': normalize_space(parser.all_text)[:1500],
        'text_suffix': normalize_space(parser.all_text)[-3000:],
        'tables_preview': [t[:8] for t in parser.tables[:8]],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
