#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import http.cookiejar
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
MAX_SEARCH_RESULTS_TO_INSPECT = 20
UUID_INFO_RE = re.compile(
    r"/home/information/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/?$",
    re.I,
)


class PageParser(HTMLParser):
    """Collect the small HTML surface needed by the bounded PPID probe."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.forms: list[dict[str, Any]] = []
        self.text_parts: list[str] = []
        self._form: dict[str, Any] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Record links and form fields without executing page scripts."""
        values = {key: (value or "") for key, value in attrs}
        if tag == "a" and values.get("href"):
            self.links.append(values["href"])
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
        """Close the current form scope."""
        if tag == "form":
            self._form = None

    def handle_data(self, data: str) -> None:
        """Retain normalized visible text for semantic identity checks."""
        text = re.sub(r"\s+", " ", data).strip()
        if text:
            self.text_parts.append(text)


def _same_official_host(url: str) -> bool:
    """Accept only HTTPS URLs on sumbarprov.go.id or its subdomains."""
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    return parsed.scheme == "https" and (
        host == "sumbarprov.go.id" or host.endswith(".sumbarprov.go.id")
    )


class OfficialRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject redirects that leave the allowlisted Sumatera Barat host family."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request | None:
        """Validate every redirect target before urllib follows it."""
        absolute = urllib.parse.urljoin(req.full_url, newurl)
        if not _same_official_host(absolute):
            raise urllib.error.HTTPError(
                absolute,
                code,
                "refusing redirect outside official sumbarprov.go.id host family",
                headers,
                fp,
            )
        return super().redirect_request(req, fp, code, msg, headers, absolute)


def _build_opener(cookie_jar: http.cookiejar.CookieJar | None = None) -> urllib.request.OpenerDirector:
    """Build an opener that enforces the official-host redirect policy."""
    handlers: list[Any] = [OfficialRedirectHandler()]
    if cookie_jar is not None:
        handlers.append(urllib.request.HTTPCookieProcessor(cookie_jar))
    return urllib.request.build_opener(*handlers)


def _request_result(
    opener: urllib.request.OpenerDirector,
    request: urllib.request.Request,
    max_body: int,
) -> dict[str, Any]:
    """Fetch one bounded response and preserve transport diagnostics."""
    if not _same_official_host(request.full_url):
        raise ValueError(f"refusing non-official URL: {request.full_url}")
    try:
        with opener.open(request, timeout=45) as response:
            final_url = str(response.geturl())
            if not _same_official_host(final_url):
                raise ValueError(f"refusing non-official final URL: {final_url}")
            body = response.read(max_body + 1)
            truncated = len(body) > max_body
            if truncated:
                body = body[:max_body]
            return {
                "requested_url": request.full_url,
                "status": int(response.status),
                "final_url": final_url,
                "content_type": str(response.headers.get("Content-Type", "")),
                "content_length_header": str(response.headers.get("Content-Length", "")),
                "body": body,
                "body_truncated": truncated,
                "error": None,
            }
    except urllib.error.HTTPError as exc:
        body = exc.read(max_body + 1) if exc.fp is not None else b""
        truncated = len(body) > max_body
        if truncated:
            body = body[:max_body]
        final_url = str(exc.geturl())
        return {
            "requested_url": request.full_url,
            "status": int(exc.code),
            "final_url": final_url,
            "content_type": str(exc.headers.get("Content-Type", "")) if exc.headers else "",
            "content_length_header": str(exc.headers.get("Content-Length", "")) if exc.headers else "",
            "body": body,
            "body_truncated": truncated,
            "error": f"HTTPError:{exc.code}",
        }
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return {
            "requested_url": request.full_url,
            "status": None,
            "final_url": None,
            "content_type": "",
            "content_length_header": "",
            "body": b"",
            "body_truncated": False,
            "error": f"{type(exc).__name__}:{exc}",
        }


def fetch(url: str, *, max_body: int = MAX_HTML_BODY) -> dict[str, Any]:
    """GET one allowlisted URL with redirect enforcement."""
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/pdf,*/*",
        },
    )
    return _request_result(_build_opener(), request, max_body)


def _redacted_forms(forms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove volatile CSRF token values from persisted probe output."""
    copied = json.loads(json.dumps(forms))
    for form in copied:
        for field in form.get("fields", []):
            if field.get("name") == "csrf_ppid" and field.get("value"):
                field["value"] = "<redacted-volatile-csrf>"
    return copied


def _is_complete_pdf(result: dict[str, Any]) -> bool:
    """Require a complete HTTP-200 PDF body with magic bytes and EOF marker."""
    body = result.get("body") or b""
    return (
        result.get("status") == 200
        and result.get("body_truncated") is False
        and body.startswith(b"%PDF-")
        and b"%%EOF" in body[-4096:]
    )


def summarize_response(result: dict[str, Any]) -> dict[str, Any]:
    """Produce a stable, non-secret summary for one live response."""
    body: bytes = result.get("body") or b""
    content_type = str(result.get("content_type", "")).casefold()
    summary = {
        key: result.get(key)
        for key in (
            "requested_url",
            "status",
            "final_url",
            "content_type",
            "content_length_header",
            "body_truncated",
            "error",
        )
    }
    summary["body_bytes_read"] = len(body)
    summary["body_sha256_read"] = hashlib.sha256(body).hexdigest() if body else None
    summary["is_pdf"] = _is_complete_pdf(result)
    summary["is_html"] = "text/html" in content_type or b"<html" in body[:4096].lower()

    if summary["is_html"] and body:
        parser = PageParser()
        parser.feed(body.decode("utf-8", errors="replace"))
        visible = re.sub(r"\s+", " ", " ".join(parser.text_parts)).strip()
        folded = visible.casefold()
        summary["visible_text_excerpt"] = visible[:1800]
        summary["exact_title_present"] = TITLE.casefold() in folded
        summary["identity_tokens_present"] = all(
            token in folded for token in ("pusdalops", "kebencanaan", "2017")
        )
        relevant_links: list[str] = []
        for href in parser.links:
            absolute = urllib.parse.urljoin(
                str(result.get("final_url") or result.get("requested_url")), href
            )
            if not _same_official_host(absolute):
                continue
            low = absolute.casefold()
            if any(token in low for token in ("download", ".pdf", "pusdalops", "8604", "information")):
                relevant_links.append(absolute)
        summary["relevant_links"] = sorted(set(relevant_links))[:100]
        summary["forms"] = _redacted_forms(parser.forms[:20])
    else:
        summary["exact_title_present"] = False
        summary["identity_tokens_present"] = False
    return summary


def exact_title_inventory_search() -> tuple[dict[str, Any], list[str]]:
    """Submit the exact target title through the official PPID search form."""
    jar = http.cookiejar.CookieJar()
    opener = _build_opener(jar)
    dip_url = f"{BASE}/home/dip"
    initial_request = urllib.request.Request(
        dip_url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"},
    )
    initial = _request_result(opener, initial_request, MAX_HTML_BODY)
    if initial["status"] != 200 or not initial["body"]:
        return summarize_response(initial), []

    parser = PageParser()
    parser.feed(initial["body"].decode("utf-8", errors="replace"))
    csrf: str | None = None
    for form in parser.forms:
        for field in form["fields"]:
            if field["name"] == "csrf_ppid" and field["value"]:
                csrf = field["value"]
                break
        if csrf:
            break
    if not csrf:
        summary = summarize_response(initial)
        summary["search_error"] = "csrf_token_not_found"
        return summary, []

    payload = urllib.parse.urlencode({"csrf_ppid": csrf, "judul": TITLE}).encode("utf-8")
    request = urllib.request.Request(
        dip_url,
        data=payload,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,*/*",
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": dip_url,
        },
        method="POST",
    )
    result = _request_result(opener, request, MAX_HTML_BODY)
    summary = summarize_response(result)
    summary["search_method"] = "official_ppid_dip_post_exact_title"
    summary["csrf_cookie_session_used"] = True
    info_urls = [
        url
        for url in summary.get("relevant_links", [])
        if _same_official_host(url) and UUID_INFO_RE.search(urllib.parse.urlparse(url).path)
    ]
    return summary, sorted(set(info_urls))


def maybe_save_verified_download(report: dict[str, Any], information_url: str) -> None:
    """Save only a complete official PDF linked from one exact-title inventory hit."""
    if not _same_official_host(information_url):
        return
    uuid_match = UUID_INFO_RE.search(urllib.parse.urlparse(information_url).path)
    if not uuid_match:
        return
    uuid = uuid_match.group(1).lower()
    download_url = f"{BASE}/home/download/{uuid}"
    raw = fetch(download_url, max_body=MAX_PDF_BODY)
    summary = summarize_response(raw)
    summary["source_information_url"] = information_url
    report["active_inventory_exact_match_download"] = summary
    if not _is_complete_pdf(raw):
        return
    target = OUTDIR / "bpbd-pusdalops-sumbar-2017-candidate.pdf"
    target.write_bytes(raw["body"])
    summary["saved_path"] = target.as_posix()
    summary["exact_raw_sha256"] = hashlib.sha256(raw["body"]).hexdigest()
    summary["exact_raw_bytes"] = len(raw["body"])
    report["raw_official_pdf_candidate_saved"] = True


def main() -> int:
    """Run the bounded legacy-route and exact-title PPID migration probe."""
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
        "schema": "ranah-observatory/m52-bpbd-2017-ppid-migration-live-probe/v5",
        "purpose": "Read-only deterministic recovery probe for legacy PPID record 8604 plus exact-title search on the official PPID inventory; no UUID brute force and no scientific value promotion.",
        "record_id": RECORD_ID,
        "exact_title": TITLE,
        "candidate_urls": candidates,
        "responses": [],
        "legacy_record_uuid_redirect": None,
        "legacy_redirect_consistent": False,
        "legacy_redirect_semantic_match": False,
        "raw_official_pdf_candidate_saved": False,
        "active_inventory_exact_match_download": None,
    }

    legacy_uuid_by_url: dict[str, str] = {}
    legacy_summaries: list[dict[str, Any]] = []
    for url in candidates:
        raw = fetch(url)
        summary = summarize_response(raw)
        report["responses"].append(summary)
        if url in legacy_urls:
            legacy_summaries.append(summary)
            final_url = raw.get("final_url")
            if final_url and _same_official_host(str(final_url)):
                match = UUID_INFO_RE.search(urllib.parse.urlparse(str(final_url)).path)
                if match:
                    legacy_uuid_by_url[url] = match.group(1).lower()

    unique_uuids = sorted(set(legacy_uuid_by_url.values()))
    report["legacy_uuid_by_url"] = legacy_uuid_by_url
    if len(legacy_uuid_by_url) == len(legacy_urls) and len(unique_uuids) == 1:
        uuid = unique_uuids[0]
        report["legacy_record_uuid_redirect"] = {
            "legacy_record_id": RECORD_ID,
            "current_uuid": uuid,
            "information_url": f"{BASE}/home/information/{uuid}",
            "download_url": f"{BASE}/home/download/{uuid}",
        }
        report["legacy_redirect_consistent"] = True
        report["legacy_redirect_semantic_match"] = all(
            item.get("exact_title_present") or item.get("identity_tokens_present")
            for item in legacy_summaries
        )
        report["legacy_redirect_download"] = summarize_response(
            fetch(f"{BASE}/home/download/{uuid}", max_body=MAX_PDF_BODY)
        )

    search_summary, info_urls = exact_title_inventory_search()
    report["active_inventory_exact_title_search"] = search_summary
    report["active_inventory_information_urls"] = info_urls
    inspected: list[dict[str, Any]] = []
    exact_matches: list[str] = []
    token_matches: list[str] = []
    for info_url in info_urls[:MAX_SEARCH_RESULTS_TO_INSPECT]:
        detail = summarize_response(fetch(info_url))
        detail["information_url"] = info_url
        inspected.append(detail)
        if detail.get("exact_title_present"):
            exact_matches.append(info_url)
        elif detail.get("identity_tokens_present"):
            token_matches.append(info_url)
    report["active_inventory_inspected_records"] = inspected
    report["active_inventory_exact_title_matches"] = exact_matches
    report["active_inventory_token_only_matches"] = token_matches
    if len(exact_matches) == 1:
        maybe_save_verified_download(report, exact_matches[0])

    (OUTDIR / "m52-ppid-migration-live-probe.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
