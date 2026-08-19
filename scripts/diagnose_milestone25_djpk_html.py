#!/usr/bin/env python3
from __future__ import annotations

import json
from probe_milestone25_djpk_taxonomy import HTMLTableParser, build_url, fetch_url, normalize_space


def main() -> int:
    url = build_url(2024)
    status, body, final_url = fetch_url(url)
    text = body.decode('utf-8', errors='replace')
    parser = HTMLTableParser()
    parser.feed(text)
    print(json.dumps({
        'status': status,
        'url': url,
        'final_url': final_url,
        'bytes': len(body),
        'title': parser.title,
        'table_count': len(parser.tables),
        'table_row_counts': [len(t) for t in parser.tables],
        'text_prefix': normalize_space(parser.all_text)[:1000],
        'tables_preview': [t[:8] for t in parser.tables[:8]],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
