#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

PAGE_URL = (
    "https://sumbar.bps.go.id/id/statistics-table/2/NjUyIzI=/"
    "banyaknya-usaha-perusahaan-konstruksi-menurut-kabupaten-kota-dan-"
    "kode-kualifikasi-usaha-di-sumatera-barat.html"
)
OUTDIR = Path("probe-output")
USER_AGENT = "ranah-observatory/0.1 (+https://github.com/nabilrn/ranah-observatory)"
MAX_HTML_BYTES = 8_000_000
MAX_SCRIPT_BYTES = 6_000_000
MAX_SCRIPTS = 24
MAX_MATCHES_PER_SCRIPT = 40

INTEREST_TERMS = (
    "statistics-table",
    "statistics_table",
    "statisticstable",
    "statistik",
    "web-api.bps.go.id",
    "webapi.bps.go.id",
    "api.bps.go.id",
    "fetch(",
    "axios",
    "graphql",
    "NjUyIzI",
    "652#2",
)

ABS_URL_RE = re.compile(r"https://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+")
REL_API_RE = re.compile(
    r"[\"']((?:/|\\/)(?:api|statistics|statistic|table|statistik)[^\"']{0,240})[\"']",
    re.I,
)
NEXT_DATA_RE = re.compile(
    r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
    re.I | re.S,
)


def official_bps_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    return parsed.scheme == "https" and (host == "bps.go.id" or host.endswith(".bps.go.id"))


class OfficialRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request | None:
        absolute = urllib.parse.urljoin(req.full_url, newurl)
        if not official_bps_url(absolute):
            raise urllib.error.HTTPError(
                absolute, code, "refusing redirect outside bps.go.id", headers, fp
            )
        return super().redirect_request(req, fp, code, msg, headers, absolute)


class ScriptParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.script_srcs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "script":
            return
        values = {key.lower(): (value or "") for key, value in attrs}
        if values.get("src"):
            self.script_srcs.append(values["src"])


def fetch(url: str, max_bytes: int) -> dict[str, Any]:
    if not official_bps_url(url):
        raise ValueError(f"non-BPS URL: {url}")
    opener = urllib.request.build_opener(OfficialRedirectHandler())
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/javascript,text/javascript,*/*",
        },
    )
    try:
        with opener.open(request, timeout=90) as response:
            final_url = str(response.geturl())
            if not official_bps_url(final_url):
                raise ValueError(f"non-BPS final URL: {final_url}")
            body = response.read(max_bytes + 1)
            truncated = len(body) > max_bytes
            if truncated:
                body = body[:max_bytes]
            return {
                "status": int(response.status),
                "requested_url": url,
                "final_url": final_url,
                "content_type": str(response.headers.get("Content-Type", "")),
                "body": body,
                "truncated": truncated,
                "error": None,
            }
    except urllib.error.HTTPError as exc:
        body = exc.read(max_bytes + 1) if exc.fp is not None else b""
        truncated = len(body) > max_bytes
        if truncated:
            body = body[:max_bytes]
        return {
            "status": int(exc.code),
            "requested_url": url,
            "final_url": str(exc.geturl()),
            "content_type": str(exc.headers.get("Content-Type", "")) if exc.headers else "",
            "body": body,
            "truncated": truncated,
            "error": f"HTTPError:{exc.code}",
        }
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return {
            "status": None,
            "requested_url": url,
            "final_url": None,
            "content_type": "",
            "body": b"",
            "truncated": False,
            "error": f"{type(exc).__name__}:{exc}",
        }


def summarize_response(result: dict[str, Any]) -> dict[str, Any]:
    body = result.get("body") or b""
    return {
        "status": result.get("status"),
        "requested_url": result.get("requested_url"),
        "final_url": result.get("final_url"),
        "content_type": result.get("content_type"),
        "body_bytes": len(body),
        "body_sha256": hashlib.sha256(body).hexdigest() if body else None,
        "truncated": result.get("truncated"),
        "error": result.get("error"),
    }


def snippets(text: str) -> list[dict[str, str]]:
    folded = text.casefold()
    found: list[dict[str, str]] = []
    seen: set[tuple[str, int]] = set()
    for term in INTEREST_TERMS:
        needle = term.casefold()
        start = 0
        while len(found) < MAX_MATCHES_PER_SCRIPT:
            idx = folded.find(needle, start)
            if idx < 0:
                break
            key = (needle, idx)
            if key not in seen:
                seen.add(key)
                left = max(0, idx - 220)
                right = min(len(text), idx + len(term) + 360)
                snippet = re.sub(r"\s+", " ", text[left:right]).strip()
                found.append({"term": term, "snippet": snippet})
            start = idx + max(1, len(needle))
    return found[:MAX_MATCHES_PER_SCRIPT]


def explicit_routes(text: str, base_url: str) -> list[str]:
    routes: list[str] = []
    for match in ABS_URL_RE.findall(text):
        cleaned = match.rstrip(".)]},;\\")
        if official_bps_url(cleaned) and cleaned not in routes:
            routes.append(cleaned)
    for match in REL_API_RE.finditer(text):
        raw = match.group(1).replace("\\/", "/")
        absolute = urllib.parse.urljoin(base_url, raw)
        if official_bps_url(absolute) and absolute not in routes:
            routes.append(absolute)
    return routes[:80]


def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    page = fetch(PAGE_URL, MAX_HTML_BYTES)
    page_body = page.get("body") or b""
    page_text = page_body.decode("utf-8", errors="replace")

    parser = ScriptParser()
    if page_text:
        parser.feed(page_text)

    script_urls: list[str] = []
    page_base = str(page.get("final_url") or PAGE_URL)
    for src in parser.script_srcs:
        absolute = urllib.parse.urljoin(page_base, src)
        if official_bps_url(absolute) and absolute not in script_urls:
            script_urls.append(absolute)
        if len(script_urls) >= MAX_SCRIPTS:
            break

    next_data: Any = None
    next_match = NEXT_DATA_RE.search(page_text)
    if next_match:
        try:
            next_data = json.loads(next_match.group(1))
        except json.JSONDecodeError:
            next_data = {"parse_error": True, "sha256": hashlib.sha256(next_match.group(1).encode()).hexdigest()}

    script_reports: list[dict[str, Any]] = []
    discovered_routes: list[str] = explicit_routes(page_text, page_base)
    for url in script_urls:
        result = fetch(url, MAX_SCRIPT_BYTES)
        body = result.get("body") or b""
        text = body.decode("utf-8", errors="replace")
        report = summarize_response(result)
        report["matches"] = snippets(text)
        report["explicit_official_routes"] = explicit_routes(text, str(result.get("final_url") or url))
        script_reports.append(report)
        for route in report["explicit_official_routes"]:
            if route not in discovered_routes:
                discovered_routes.append(route)

    page_title_present = "banyaknya usaha/perusahaan konstruksi" in page_text.casefold()
    report = {
        "schema": "ranah-observatory/bps-statistics-table-frontend-transport-probe/v1",
        "purpose": (
            "Inspect only the verified BPS statistics-table page and script resources directly referenced "
            "by that page to identify explicit official data transport routes."
        ),
        "target": {
            "url": PAGE_URL,
            "encoded_identity": "652#2",
            "expected_title_prefix": "Banyaknya Usaha/Perusahaan Konstruksi",
        },
        "page_response": summarize_response(page),
        "page_title_present": page_title_present,
        "page_interest_matches": snippets(page_text),
        "page_explicit_official_routes": explicit_routes(page_text, page_base),
        "script_src_count_in_html": len(parser.script_srcs),
        "official_scripts_inspected": len(script_reports),
        "script_limit": MAX_SCRIPTS,
        "scripts": script_reports,
        "next_data_present": next_match is not None,
        "next_data": next_data,
        "discovered_explicit_official_routes": discovered_routes[:160],
        "hidden_endpoint_guessing_performed": False,
        "authentication_bypass_attempted": False,
        "non_bps_resource_followed": False,
    }

    path = OUTDIR / "bps-statistics-table-frontend-transport-probe.json"
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "page_status": report["page_response"]["status"],
                "page_title_present": report["page_title_present"],
                "official_scripts_inspected": report["official_scripts_inspected"],
                "next_data_present": report["next_data_present"],
                "explicit_route_count": len(report["discovered_explicit_official_routes"]),
                "output": path.as_posix(),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
