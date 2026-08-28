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

BASE = "https://perpustakaan.bps.go.id"
SEARCH_URL = f"{BASE}/opac/search"
TITLE = "Profil Perusahaan Konstruksi di Luar Pulau Jawa 2005"
PUBLICATION_NUMBER = "05230.0610"
ISBN = "979-724-565-9"
OUTDIR = Path("probe-output")
USER_AGENT = "ranah-observatory/0.1 (+https://github.com/nabilrn/ranah-observatory)"
MAX_HTML_BODY = 12_000_000
MAX_PDF_BODY = 100_000_000
DETAIL_ID_RE = re.compile(r"/opac/details/([^/?#]+)$", re.I)
READ_ID_RE = re.compile(r"/opac/read/([^/?#]+)\.pdf$", re.I)


class Parser(HTMLParser):
    """Collect the small public OPAC surface needed by the bounded probe."""

    def __init__(self) -> None:
        super().__init__()
        self.forms: list[dict[str, Any]] = []
        self.links: list[dict[str, str]] = []
        self.text_parts: list[str] = []
        self._form: dict[str, Any] | None = None
        self._link: dict[str, str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: (value or "") for key, value in attrs}
        if tag == "form":
            self._form = {
                "action": values.get("action", ""),
                "method": values.get("method", "get").lower(),
                "fields": [],
            }
            self.forms.append(self._form)
        elif tag in {"input", "select", "textarea", "button"} and self._form is not None:
            self._form["fields"].append(
                {
                    "tag": tag,
                    "name": values.get("name", ""),
                    "type": values.get("type", ""),
                    "value": values.get("value", ""),
                    "placeholder": values.get("placeholder", ""),
                    "checked": "checked" in values,
                }
            )
        elif tag == "a" and values.get("href"):
            self._link = {"href": values["href"], "text": ""}
            self.links.append(self._link)

    def handle_endtag(self, tag: str) -> None:
        if tag == "form":
            self._form = None
        elif tag == "a":
            self._link = None

    def handle_data(self, data: str) -> None:
        text = re.sub(r"\s+", " ", data).strip()
        if text:
            self.text_parts.append(text)
            if self._link is not None:
                self._link["text"] = (self._link["text"] + " " + text).strip()


def official_url(url: str) -> bool:
    """Allow HTTPS BPS hosts only."""
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    return parsed.scheme == "https" and (host == "bps.go.id" or host.endswith(".bps.go.id"))


class OfficialRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject redirects that leave the BPS host family."""

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
        if not official_url(absolute):
            raise urllib.error.HTTPError(
                absolute, code, "refusing redirect outside bps.go.id", headers, fp
            )
        return super().redirect_request(req, fp, code, msg, headers, absolute)


def opener() -> urllib.request.OpenerDirector:
    """Build a cookie-aware opener with BPS-only redirects."""
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(
        OfficialRedirectHandler(), urllib.request.HTTPCookieProcessor(jar)
    )


def fetch(
    op: urllib.request.OpenerDirector,
    request: urllib.request.Request,
    *,
    max_body: int = MAX_HTML_BODY,
) -> dict[str, Any]:
    """Fetch a bounded response from an allowlisted BPS URL."""
    if not official_url(request.full_url):
        raise ValueError(f"non-official request URL: {request.full_url}")
    try:
        with op.open(request, timeout=60) as response:
            final_url = str(response.geturl())
            if not official_url(final_url):
                raise ValueError(f"non-official final URL: {final_url}")
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
        return {
            "requested_url": request.full_url,
            "status": int(exc.code),
            "final_url": str(exc.geturl()),
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


def parse_html(result: dict[str, Any]) -> tuple[Parser, str]:
    """Parse returned HTML without executing scripts."""
    text = (result.get("body") or b"").decode("utf-8", errors="replace")
    parser = Parser()
    parser.feed(text)
    visible = re.sub(r"\s+", " ", " ".join(parser.text_parts)).strip()
    return parser, visible


def redact_text(value: str) -> str:
    """Redact volatile CSRF/token-like values from persisted excerpts."""
    value = re.sub(
        r'(?i)(csrfToken|csrf_token|_token)(?:\\?"|\s|:|=)+[A-Za-z0-9_+\-/=]{16,}',
        r"\1:<redacted>",
        value,
    )
    value = re.sub(
        r'(?i)(csrfToken|csrf_token|_token)\\?"?\s*:\s*\\?"[^"]+\\?"',
        r'\1":"<redacted>"',
        value,
    )
    return value


def form_summary(forms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Copy forms while redacting volatile hidden tokens."""
    copied = json.loads(json.dumps(forms))
    for form in copied:
        for field in form.get("fields", []):
            name = field.get("name", "").casefold()
            if any(token in name for token in ("csrf", "token")) and field.get("value"):
                field["value"] = "<redacted>"
    return copied


def candidate_query_fields(forms: list[dict[str, Any]]) -> list[tuple[dict[str, Any], str]]:
    """Find ordinary text search fields exposed by the OPAC form."""
    candidates: list[tuple[dict[str, Any], str]] = []
    for form in forms:
        for field in form.get("fields", []):
            if field.get("tag") != "input" or not field.get("name"):
                continue
            if field.get("type", "").casefold() not in {"", "text", "search"}:
                continue
            signal = " ".join(
                (field.get("name", ""), field.get("placeholder", ""))
            ).casefold()
            if any(
                token in signal
                for token in ("judul", "keyword", "kata kunci", "search", "cari", "query", "q")
            ):
                candidates.append((form, field["name"]))
    return candidates


def build_payload(form: dict[str, Any], query_field: str) -> dict[str, str]:
    """Preserve the form contract while replacing only the query value."""
    payload: dict[str, str] = {}
    for field in form.get("fields", []):
        name = field.get("name", "")
        if not name:
            continue
        field_type = field.get("type", "").casefold()
        if name == query_field:
            payload[name] = TITLE
        elif field_type == "hidden" and field.get("value"):
            payload[name] = field["value"]
        elif (
            field_type in {"checkbox", "radio"}
            and field.get("checked")
            and field.get("value")
        ):
            payload[name] = field["value"]
    return payload


def request_for_form(form: dict[str, Any], payload: dict[str, str]) -> urllib.request.Request:
    """Build a request using the official form's method and action."""
    action = urllib.parse.urljoin(SEARCH_URL, form.get("action") or SEARCH_URL)
    if not official_url(action):
        raise ValueError(f"non-official form action: {action}")
    method = form.get("method", "get").lower()
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,*/*",
        "Referer": SEARCH_URL,
    }
    if method == "post":
        body = urllib.parse.urlencode(payload, doseq=True).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        return urllib.request.Request(action, data=body, headers=headers, method="POST")
    separator = "&" if urllib.parse.urlparse(action).query else "?"
    url = action + separator + urllib.parse.urlencode(payload, doseq=True)
    return urllib.request.Request(url, headers=headers, method="GET")


def summarize(result: dict[str, Any]) -> dict[str, Any]:
    """Create a compact response summary suitable for probe evidence."""
    body = result.get("body") or b""
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
    summary["body_bytes"] = len(body)
    summary["body_sha256"] = hashlib.sha256(body).hexdigest() if body else None
    summary["complete_pdf"] = (
        result.get("status") == 200
        and result.get("body_truncated") is False
        and body.startswith(b"%PDF-")
        and b"%%EOF" in body[-4096:]
    )
    if "text/html" in str(result.get("content_type", "")).casefold() or b"<html" in body[:4096].lower():
        parser, visible = parse_html(result)
        visible = redact_text(visible)
        folded = visible.casefold()
        summary["visible_excerpt"] = visible[:2500]
        summary["title_present"] = TITLE.casefold() in folded
        summary["publication_number_present"] = PUBLICATION_NUMBER in visible
        summary["isbn_present"] = ISBN in visible
        links: list[dict[str, str]] = []
        for item in parser.links:
            absolute = urllib.parse.urljoin(
                str(result.get("final_url") or result.get("requested_url")), item["href"]
            )
            if not official_url(absolute):
                continue
            if any(
                token in absolute.casefold()
                for token in ("/opac/details/", "/opac/read/", "softcopy", "download", ".pdf")
            ) or any(
                token in item.get("text", "").casefold()
                for token in ("softcopy", "profil perusahaan konstruksi")
            ):
                links.append({"url": absolute, "text": item.get("text", "")})
        summary["relevant_links"] = links[:100]
    return summary


def record_id(url: str) -> str | None:
    """Extract an OPAC record identifier from detail or read routes."""
    path = urllib.parse.urlparse(url).path
    detail_match = DETAIL_ID_RE.search(path)
    if detail_match:
        return detail_match.group(1)
    read_match = READ_ID_RE.search(path)
    if read_match:
        return read_match.group(1)
    return None


def save_if_complete_pdf(report: dict[str, Any], result: dict[str, Any], summary: dict[str, Any]) -> None:
    """Save the first full target softcopy only after strict PDF validation."""
    if report["raw_pdf_candidate_saved"] or not summary.get("complete_pdf"):
        return
    body = result.get("body") or b""
    path = OUTDIR / "profil-perusahaan-konstruksi-luar-jawa-2005-candidate.pdf"
    path.write_bytes(body)
    summary["saved_path"] = path.as_posix()
    summary["exact_sha256"] = hashlib.sha256(body).hexdigest()
    summary["exact_bytes"] = len(body)
    report["raw_pdf_candidate_saved"] = True


def main() -> int:
    """Run an exact-title public OPAC probe without guessing record identifiers."""
    OUTDIR.mkdir(parents=True, exist_ok=True)
    op = opener()
    initial_request = urllib.request.Request(
        SEARCH_URL,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"},
    )
    initial = fetch(op, initial_request)
    initial_parser, initial_visible = parse_html(initial)

    report: dict[str, Any] = {
        "schema": "ranah-observatory/bps-opac-outside-java-2005-live-probe/v2",
        "purpose": "Bounded exact-title probe of the public BPS OPAC; no record-ID brute force.",
        "target_title": TITLE,
        "publication_number": PUBLICATION_NUMBER,
        "isbn": ISBN,
        "initial": summarize(initial),
        "forms": form_summary(initial_parser.forms),
        "query_attempts": [],
        "detail_attempts": [],
        "softcopy_attempts": [],
        "target_record_ids": [],
        "raw_pdf_candidate_saved": False,
    }

    candidates = candidate_query_fields(initial_parser.forms)
    report["candidate_query_field_count"] = len(candidates)
    seen_requests: set[tuple[str, str]] = set()
    exact_query_links: list[dict[str, str]] = []
    for form, query_field in candidates[:6]:
        payload = build_payload(form, query_field)
        try:
            request = request_for_form(form, payload)
        except ValueError as exc:
            report["query_attempts"].append({"query_field": query_field, "error": str(exc)})
            continue
        key = (request.get_method(), request.full_url)
        if key in seen_requests:
            continue
        seen_requests.add(key)
        result = fetch(op, request)
        summary = summarize(result)
        summary["query_field"] = query_field
        report["query_attempts"].append(summary)
        if summary.get("title_present"):
            exact_query_links.extend(summary.get("relevant_links", []))

    grouped: dict[str, dict[str, str]] = {}
    for item in exact_query_links:
        rec = record_id(item["url"])
        if not rec:
            continue
        group = grouped.setdefault(rec, {})
        path = urllib.parse.urlparse(item["url"]).path
        if "/opac/details/" in path:
            group["detail_url"] = item["url"]
            if TITLE.casefold() in item.get("text", "").casefold():
                group["title_text"] = item.get("text", "")
        elif "/opac/read/" in path:
            group["read_url"] = item["url"]

    target_records = [
        rec
        for rec, group in grouped.items()
        if TITLE.casefold() in group.get("title_text", "").casefold()
    ]
    report["target_record_ids"] = sorted(target_records)

    for rec in sorted(target_records):
        group = grouped[rec]
        detail_url = group.get("detail_url")
        if detail_url:
            detail_result = fetch(
                op,
                urllib.request.Request(
                    detail_url,
                    headers={
                        "User-Agent": USER_AGENT,
                        "Accept": "text/html,application/pdf,*/*",
                        "Referer": SEARCH_URL,
                    },
                ),
            )
            detail_summary = summarize(detail_result)
            detail_summary["record_id"] = rec
            detail_summary["source_link_text"] = group.get("title_text", "")
            report["detail_attempts"].append(detail_summary)

        read_url = group.get("read_url")
        if read_url:
            soft_result = fetch(
                op,
                urllib.request.Request(
                    read_url,
                    headers={
                        "User-Agent": USER_AGENT,
                        "Accept": "application/pdf,text/html,*/*",
                        "Referer": SEARCH_URL,
                    },
                ),
                max_body=MAX_PDF_BODY,
            )
            soft_summary = summarize(soft_result)
            soft_summary["record_id"] = rec
            soft_summary["source_search_title"] = group.get("title_text", "")
            report["softcopy_attempts"].append(soft_summary)
            save_if_complete_pdf(report, soft_result, soft_summary)

    report["initial_title_present"] = TITLE.casefold() in initial_visible.casefold()
    (OUTDIR / "bps-opac-outside-java-2005-live-probe.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
