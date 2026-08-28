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
MAX_BODY = 12_000_000


class Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.forms: list[dict[str, Any]] = []
        self.links: list[dict[str, str]] = []
        self.text_parts: list[str] = []
        self._form: dict[str, Any] | None = None
        self._link: dict[str, str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {k: (v or "") for k, v in attrs}
        if tag == "form":
            self._form = {
                "action": values.get("action", ""),
                "method": values.get("method", "get").lower(),
                "fields": [],
            }
            self.forms.append(self._form)
        elif tag in {"input", "select", "textarea", "button"} and self._form is not None:
            self._form["fields"].append({
                "tag": tag,
                "name": values.get("name", ""),
                "type": values.get("type", ""),
                "value": values.get("value", ""),
                "placeholder": values.get("placeholder", ""),
                "checked": "checked" in values,
            })
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
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    return parsed.scheme == "https" and (host == "bps.go.id" or host.endswith(".bps.go.id"))


class OfficialRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: urllib.request.Request, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> urllib.request.Request | None:
        absolute = urllib.parse.urljoin(req.full_url, newurl)
        if not official_url(absolute):
            raise urllib.error.HTTPError(absolute, code, "refusing redirect outside bps.go.id", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, absolute)


def opener() -> urllib.request.OpenerDirector:
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(OfficialRedirectHandler(), urllib.request.HTTPCookieProcessor(jar))


def fetch(op: urllib.request.OpenerDirector, request: urllib.request.Request) -> dict[str, Any]:
    if not official_url(request.full_url):
        raise ValueError(f"non-official request URL: {request.full_url}")
    try:
        with op.open(request, timeout=45) as response:
            final_url = str(response.geturl())
            if not official_url(final_url):
                raise ValueError(f"non-official final URL: {final_url}")
            body = response.read(MAX_BODY + 1)
            truncated = len(body) > MAX_BODY
            if truncated:
                body = body[:MAX_BODY]
            return {
                "requested_url": request.full_url,
                "status": int(response.status),
                "final_url": final_url,
                "content_type": str(response.headers.get("Content-Type", "")),
                "body": body,
                "body_truncated": truncated,
                "error": None,
            }
    except urllib.error.HTTPError as exc:
        body = exc.read(MAX_BODY + 1) if exc.fp is not None else b""
        truncated = len(body) > MAX_BODY
        if truncated:
            body = body[:MAX_BODY]
        return {
            "requested_url": request.full_url,
            "status": int(exc.code),
            "final_url": str(exc.geturl()),
            "content_type": str(exc.headers.get("Content-Type", "")) if exc.headers else "",
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
            "body": b"",
            "body_truncated": False,
            "error": f"{type(exc).__name__}:{exc}",
        }


def parse_html(result: dict[str, Any]) -> tuple[Parser, str]:
    text = (result.get("body") or b"").decode("utf-8", errors="replace")
    parser = Parser()
    parser.feed(text)
    visible = re.sub(r"\s+", " ", " ".join(parser.text_parts)).strip()
    return parser, visible


def form_summary(forms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    copied = json.loads(json.dumps(forms))
    for form in copied:
        for field in form.get("fields", []):
            name = field.get("name", "").casefold()
            if any(token in name for token in ("csrf", "token")) and field.get("value"):
                field["value"] = "<redacted>"
    return copied


def candidate_query_fields(forms: list[dict[str, Any]]) -> list[tuple[dict[str, Any], str]]:
    candidates: list[tuple[dict[str, Any], str]] = []
    for form in forms:
        for field in form.get("fields", []):
            if field.get("tag") != "input" or not field.get("name"):
                continue
            if field.get("type", "").casefold() not in {"", "text", "search"}:
                continue
            signal = " ".join((field.get("name", ""), field.get("placeholder", ""))).casefold()
            if any(token in signal for token in ("judul", "keyword", "kata kunci", "search", "cari", "query", "q")):
                candidates.append((form, field["name"]))
    return candidates


def build_payload(form: dict[str, Any], query_field: str) -> dict[str, str]:
    payload: dict[str, str] = {}
    for field in form.get("fields", []):
        name = field.get("name", "")
        if not name:
            continue
        ftype = field.get("type", "").casefold()
        if name == query_field:
            payload[name] = TITLE
        elif ftype == "hidden" and field.get("value"):
            payload[name] = field["value"]
        elif ftype in {"checkbox", "radio"} and field.get("checked") and field.get("value"):
            payload[name] = field["value"]
    return payload


def request_for_form(form: dict[str, Any], payload: dict[str, str]) -> urllib.request.Request:
    action = urllib.parse.urljoin(SEARCH_URL, form.get("action") or SEARCH_URL)
    if not official_url(action):
        raise ValueError(f"non-official form action: {action}")
    method = form.get("method", "get").lower()
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,*/*", "Referer": SEARCH_URL}
    if method == "post":
        body = urllib.parse.urlencode(payload, doseq=True).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        return urllib.request.Request(action, data=body, headers=headers, method="POST")
    separator = "&" if urllib.parse.urlparse(action).query else "?"
    url = action + separator + urllib.parse.urlencode(payload, doseq=True)
    return urllib.request.Request(url, headers=headers, method="GET")


def summarize(result: dict[str, Any]) -> dict[str, Any]:
    body = result.get("body") or b""
    summary = {k: result.get(k) for k in ("requested_url", "status", "final_url", "content_type", "body_truncated", "error")}
    summary["body_bytes"] = len(body)
    summary["body_sha256"] = hashlib.sha256(body).hexdigest() if body else None
    if "text/html" in str(result.get("content_type", "")).casefold() or b"<html" in body[:4096].lower():
        parser, visible = parse_html(result)
        folded = visible.casefold()
        summary["visible_excerpt"] = visible[:2500]
        summary["title_present"] = TITLE.casefold() in folded
        summary["publication_number_present"] = PUBLICATION_NUMBER in visible
        summary["isbn_present"] = ISBN in visible
        links = []
        for item in parser.links:
            absolute = urllib.parse.urljoin(str(result.get("final_url") or result.get("requested_url")), item["href"])
            if not official_url(absolute):
                continue
            if any(token in absolute.casefold() for token in ("/opac/details/", "softcopy", "download", ".pdf")) or any(
                token in item.get("text", "").casefold() for token in ("softcopy", "profil perusahaan konstruksi")
            ):
                links.append({"url": absolute, "text": item.get("text", "")})
        summary["relevant_links"] = links[:100]
    return summary


def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    op = opener()
    initial_request = urllib.request.Request(SEARCH_URL, headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"})
    initial = fetch(op, initial_request)
    initial_parser, initial_visible = parse_html(initial)

    report: dict[str, Any] = {
        "schema": "ranah-observatory/bps-opac-outside-java-2005-live-probe/v1",
        "purpose": "Bounded exact-title probe of the public BPS OPAC; no record-ID brute force.",
        "target_title": TITLE,
        "publication_number": PUBLICATION_NUMBER,
        "isbn": ISBN,
        "initial": summarize(initial),
        "forms": form_summary(initial_parser.forms),
        "query_attempts": [],
        "detail_attempts": [],
        "softcopy_attempts": [],
        "raw_pdf_candidate_saved": False,
    }

    candidates = candidate_query_fields(initial_parser.forms)
    report["candidate_query_field_count"] = len(candidates)
    seen_requests: set[tuple[str, str]] = set()
    discovered_links: list[dict[str, str]] = []
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
        discovered_links.extend(summary.get("relevant_links", []))

    dedup: dict[str, dict[str, str]] = {}
    for item in discovered_links:
        dedup[item["url"]] = item
    for item in list(dedup.values())[:30]:
        url = item["url"]
        if "/opac/details/" not in urllib.parse.urlparse(url).path:
            continue
        result = fetch(op, urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/pdf,*/*", "Referer": SEARCH_URL}))
        summary = summarize(result)
        summary["source_link_text"] = item.get("text", "")
        report["detail_attempts"].append(summary)
        for soft in summary.get("relevant_links", []):
            soft_url = soft["url"]
            if soft_url == url or "/opac/details/" in urllib.parse.urlparse(soft_url).path:
                continue
            soft_result = fetch(op, urllib.request.Request(soft_url, headers={"User-Agent": USER_AGENT, "Accept": "application/pdf,text/html,*/*", "Referer": url}))
            soft_summary = summarize(soft_result)
            soft_summary["source_detail_url"] = url
            report["softcopy_attempts"].append(soft_summary)
            body = soft_result.get("body") or b""
            is_complete_pdf = (
                soft_result.get("status") == 200
                and soft_result.get("body_truncated") is False
                and body.startswith(b"%PDF-")
                and b"%%EOF" in body[-4096:]
            )
            if is_complete_pdf and not report["raw_pdf_candidate_saved"]:
                path = OUTDIR / "profil-perusahaan-konstruksi-luar-jawa-2005-candidate.pdf"
                path.write_bytes(body)
                soft_summary["saved_path"] = path.as_posix()
                soft_summary["exact_sha256"] = hashlib.sha256(body).hexdigest()
                soft_summary["exact_bytes"] = len(body)
                report["raw_pdf_candidate_saved"] = True

    report["initial_title_present"] = TITLE.casefold() in initial_visible.casefold()
    (OUTDIR / "bps-opac-outside-java-2005-live-probe.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
