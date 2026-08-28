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

BASE = "https://ppid.sumbarprov.go.id"
RECORD_ID = 8604
TITLE = "Laporan Tahunan Data Kebencanaan Pusdalops PB Sumatera Barat Tahun 2017"
SLUG = "laporan-tahunan-data-kebencanaan-pusdalops-pb-sumatera-barat-tahun-2017"
OUTDIR = Path("probe-output")
USER_AGENT = "ranah-observatory/0.1 (+https://github.com/nabilrn/ranah-observatory)"
MAX_HTML_BODY = 8_000_000
MAX_PDF_BODY = 100_000_000
MAX_SCRIPT_ASSETS = 16
UUID_INFO_RE = re.compile(r"/home/information/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/?$", re.I)


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.scripts: list[str] = []
        self.forms: list[dict[str, Any]] = []
        self.text_parts: list[str] = []
        self._form: dict[str, Any] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {k: (v or "") for k, v in attrs}
        if tag == "a" and values.get("href"):
            self.links.append(values["href"])
        elif tag == "script" and values.get("src"):
            self.scripts.append(values["src"])
        elif tag == "form":
            self._form = {
                "action": values.get("action", ""),
                "method": values.get("method", "get").lower(),
                "fields": [],
            }
            self.forms.append(self._form)
        elif tag in {"input", "select", "textarea"} and self._form is not None:
            self._form["fields"].append(
                {
                    "tag": tag,
                    "name": values.get("name", ""),
                    "type": values.get("type", ""),
                    "value": values.get("value", ""),
                }
            )

    def handle_endtag(self, tag: str) -> None:
        if tag == "form":
            self._form = None

    def handle_data(self, data: str) -> None:
        text = re.sub(r"\s+", " ", data).strip()
        if text:
            self.text_parts.append(text)


def _same_official_host(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    return parsed.scheme == "https" and (host == "sumbarprov.go.id" or host.endswith(".sumbarprov.go.id"))


def fetch(url: str, *, max_body: int = MAX_HTML_BODY) -> dict[str, Any]:
    if not _same_official_host(url):
        raise ValueError(f"refusing non-official URL: {url}")
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/pdf,application/javascript,text/javascript,*/*",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            body = response.read(max_body + 1)
            truncated = len(body) > max_body
            if truncated:
                body = body[:max_body]
            return {
                "requested_url": url,
                "status": int(response.status),
                "final_url": str(response.geturl()),
                "content_type": str(response.headers.get("Content-Type", "")),
                "content_length_header": str(response.headers.get("Content-Length", "")),
                "body": body,
                "body_truncated": truncated,
                "error": None,
            }
    except urllib.error.HTTPError as exc:
        body = exc.read(max_body + 1)
        truncated = len(body) > max_body
        if truncated:
            body = body[:max_body]
        return {
            "requested_url": url,
            "status": int(exc.code),
            "final_url": str(exc.geturl()),
            "content_type": str(exc.headers.get("Content-Type", "")),
            "content_length_header": str(exc.headers.get("Content-Length", "")),
            "body": body,
            "body_truncated": truncated,
            "error": f"HTTPError:{exc.code}",
        }
    except (urllib.error.URLError, TimeoutError) as exc:
        return {
            "requested_url": url,
            "status": None,
            "final_url": None,
            "content_type": "",
            "content_length_header": "",
            "body": b"",
            "body_truncated": False,
            "error": f"{type(exc).__name__}:{exc}",
        }


def summarize_response(result: dict[str, Any]) -> dict[str, Any]:
    body: bytes = result["body"]
    content_type = str(result["content_type"]).casefold()
    summary = {key: result[key] for key in (
        "requested_url", "status", "final_url", "content_type",
        "content_length_header", "body_truncated", "error",
    )}
    summary["body_bytes_read"] = len(body)
    summary["body_sha256_read"] = hashlib.sha256(body).hexdigest() if body else None
    summary["is_pdf"] = body.startswith(b"%PDF-") or "application/pdf" in content_type
    summary["is_html"] = "text/html" in content_type or b"<html" in body[:4096].lower()

    if summary["is_html"] and body:
        text = body.decode("utf-8", errors="replace")
        parser = PageParser()
        parser.feed(text)
        visible = re.sub(r"\s+", " ", " ".join(parser.text_parts)).strip()
        summary["visible_text_excerpt"] = visible[:1600]
        summary["exact_title_present"] = TITLE.casefold() in visible.casefold()
        relevant_links: list[str] = []
        for href in parser.links:
            absolute = urllib.parse.urljoin(str(result["final_url"] or result["requested_url"]), href)
            low = absolute.casefold()
            if any(token in low for token in ("download", ".pdf", "pusdalops", "8604", "information")):
                relevant_links.append(absolute)
        summary["relevant_links"] = sorted(set(relevant_links))[:80]
        summary["forms"] = parser.forms[:20]
        summary["script_sources"] = [
            urllib.parse.urljoin(str(result["final_url"] or result["requested_url"]), src)
            for src in parser.scripts
        ][:80]
    else:
        summary["exact_title_present"] = False
    return summary


def extract_asset_hints(body: bytes) -> list[str]:
    text = body.decode("utf-8", errors="replace")
    hints: list[str] = []
    for match in re.finditer(r".{0,180}(?:home/dip|home/information|home/download|api/download|ajax|datatable).{0,240}", text, flags=re.I | re.S):
        snippet = re.sub(r"\s+", " ", match.group(0)).strip()
        if snippet and snippet not in hints:
            hints.append(snippet)
        if len(hints) >= 40:
            break
    return hints


def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    legacy_urls = [
        f"{BASE}/home/details/{RECORD_ID}-{SLUG}.html",
        f"{BASE}/home/details/{RECORD_ID}-{SLUG}",
        f"{BASE}/home/details/{RECORD_ID}",
    ]
    candidates = [
        f"{BASE}/home/dip",
        *legacy_urls,
        f"{BASE}/home/information/{RECORD_ID}",
        f"{BASE}/home/download/{RECORD_ID}",
        f"{BASE}/api/download/?id={RECORD_ID}",
        f"{BASE}/api/download/?id={RECORD_ID}&title={urllib.parse.quote_plus(TITLE)}",
    ]
    report: dict[str, Any] = {
        "schema": "ranah-observatory/m52-bpbd-2017-ppid-migration-live-probe/v2",
        "purpose": "Read-only deterministic recovery probe for legacy PPID record 8604; no UUID brute force and no scientific value promotion.",
        "record_id": RECORD_ID,
        "exact_title": TITLE,
        "candidate_urls": candidates,
        "responses": [],
        "asset_hints": [],
        "legacy_record_uuid_mapping": None,
        "legacy_mapping_consistent": False,
        "discovered_uuid_download": None,
        "raw_official_pdf_candidate_saved": False,
    }

    script_urls: list[str] = []
    legacy_uuid_by_url: dict[str, str] = {}
    for url in candidates:
        raw = fetch(url)
        summary = summarize_response(raw)
        report["responses"].append(summary)
        if url == f"{BASE}/home/dip":
            script_urls = [u for u in summary.get("script_sources", []) if _same_official_host(u)]
        if url in legacy_urls and raw.get("final_url"):
            match = UUID_INFO_RE.search(str(raw["final_url"]))
            if match:
                legacy_uuid_by_url[url] = match.group(1).lower()

    unique_uuids = sorted(set(legacy_uuid_by_url.values()))
    report["legacy_uuid_by_url"] = legacy_uuid_by_url
    if len(legacy_uuid_by_url) == len(legacy_urls) and len(unique_uuids) == 1:
        recovered_uuid = unique_uuids[0]
        report["legacy_record_uuid_mapping"] = {
            "legacy_record_id": RECORD_ID,
            "current_uuid": recovered_uuid,
            "information_url": f"{BASE}/home/information/{recovered_uuid}",
            "download_url": f"{BASE}/home/download/{recovered_uuid}",
        }
        report["legacy_mapping_consistent"] = True

        download_url = f"{BASE}/home/download/{recovered_uuid}"
        raw = fetch(download_url, max_body=MAX_PDF_BODY)
        summary = summarize_response(raw)
        report["discovered_uuid_download"] = summary
        if summary["is_pdf"] and raw["body"] and not raw["body_truncated"]:
            target = OUTDIR / "bpbd-pusdalops-sumbar-2017-candidate.pdf"
            target.write_bytes(raw["body"])
            summary["saved_path"] = target.as_posix()
            summary["exact_raw_sha256"] = hashlib.sha256(raw["body"]).hexdigest()
            summary["exact_raw_bytes"] = len(raw["body"])
            report["raw_official_pdf_candidate_saved"] = True

    for script_url in script_urls[:MAX_SCRIPT_ASSETS]:
        raw = fetch(script_url)
        if raw["status"] != 200 or not raw["body"]:
            continue
        hints = extract_asset_hints(raw["body"])
        if hints:
            report["asset_hints"].append({
                "url": script_url,
                "status": raw["status"],
                "content_type": raw["content_type"],
                "body_bytes_read": len(raw["body"]),
                "body_sha256_read": hashlib.sha256(raw["body"]).hexdigest(),
                "hints": hints,
            })

    (OUTDIR / "m52-ppid-migration-live-probe.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
