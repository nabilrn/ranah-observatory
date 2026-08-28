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

RECORD_ID = "111.0614.1380"
TITLE = "Profil Perusahaan Konstruksi di Luar Pulau Jawa 2005"
DETAIL_URL = f"https://perpustakaan.bps.go.id/opac/details/{RECORD_ID}"
OUTDIR = Path("probe-output")
USER_AGENT = "ranah-observatory/0.1 (+https://github.com/nabilrn/ranah-observatory)"
MAX_BODY = 12_000_000


class DetailParser(HTMLParser):
    """Collect public links, forms, scripts and visible text from one OPAC detail page."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, str]] = []
        self.forms: list[dict[str, Any]] = []
        self.scripts: list[dict[str, str]] = []
        self.text_parts: list[str] = []
        self._link: dict[str, str] | None = None
        self._form: dict[str, Any] | None = None
        self._script: dict[str, str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: (value or "") for key, value in attrs}
        if tag == "a" and values.get("href"):
            self._link = {"href": values["href"], "text": ""}
            self.links.append(self._link)
        elif tag == "form":
            self._form = {
                "action": values.get("action", ""),
                "method": values.get("method", "get").lower(),
                "fields": [],
            }
            self.forms.append(self._form)
        elif tag in {"input", "button", "select", "textarea"} and self._form is not None:
            self._form["fields"].append(
                {
                    "tag": tag,
                    "name": values.get("name", ""),
                    "type": values.get("type", ""),
                    "value": values.get("value", ""),
                }
            )
        elif tag == "script":
            self._script = {"src": values.get("src", ""), "inline": ""}
            self.scripts.append(self._script)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a":
            self._link = None
        elif tag == "form":
            self._form = None
        elif tag == "script":
            self._script = None

    def handle_data(self, data: str) -> None:
        text = re.sub(r"\s+", " ", data).strip()
        if not text:
            return
        self.text_parts.append(text)
        if self._link is not None:
            self._link["text"] = (self._link["text"] + " " + text).strip()
        if self._script is not None and not self._script.get("src"):
            self._script["inline"] = (self._script["inline"] + " " + text).strip()


def official_url(url: str) -> bool:
    """Allow HTTPS BPS hosts only."""
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    return parsed.scheme == "https" and (host == "bps.go.id" or host.endswith(".bps.go.id"))


class OfficialRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject redirects outside the BPS host family."""

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


def fetch() -> dict[str, Any]:
    """Fetch only the exact verified public detail locator."""
    opener = urllib.request.build_opener(OfficialRedirectHandler())
    request = urllib.request.Request(
        DETAIL_URL,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,*/*",
            "Referer": "https://perpustakaan.bps.go.id/opac/search",
        },
    )
    try:
        with opener.open(request, timeout=60) as response:
            final_url = str(response.geturl())
            if not official_url(final_url):
                raise ValueError(f"non-official final URL: {final_url}")
            body = response.read(MAX_BODY + 1)
            truncated = len(body) > MAX_BODY
            if truncated:
                body = body[:MAX_BODY]
            return {
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
            "status": int(exc.code),
            "final_url": str(exc.geturl()),
            "content_type": str(exc.headers.get("Content-Type", "")) if exc.headers else "",
            "body": body,
            "body_truncated": truncated,
            "error": f"HTTPError:{exc.code}",
        }
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return {
            "status": None,
            "final_url": None,
            "content_type": "",
            "body": b"",
            "body_truncated": False,
            "error": f"{type(exc).__name__}:{exc}",
        }


def _redact(fields: list[dict[str, str]]) -> list[dict[str, str]]:
    """Redact token-like values from persisted form metadata."""
    result = json.loads(json.dumps(fields))
    for field in result:
        name = field.get("name", "").casefold()
        if any(token in name for token in ("csrf", "token", "password")) and field.get("value"):
            field["value"] = "<redacted>"
    return result


def main() -> int:
    """Inspect the public detail page for already-exposed official transport locators."""
    OUTDIR.mkdir(parents=True, exist_ok=True)
    result = fetch()
    body = result.get("body") or b""
    parser = DetailParser()
    if body:
        parser.feed(body.decode("utf-8", errors="replace"))

    base = str(result.get("final_url") or DETAIL_URL)
    visible = re.sub(r"\s+", " ", " ".join(parser.text_parts)).strip()
    relevant_links: list[dict[str, str]] = []
    for item in parser.links:
        absolute = urllib.parse.urljoin(base, item["href"])
        if not official_url(absolute):
            continue
        low = absolute.casefold()
        if any(token in low for token in ("read", "download", "file", "pdf", "attachment", "api", RECORD_ID.casefold())):
            relevant_links.append({"url": absolute, "text": item.get("text", "")})

    relevant_scripts: list[dict[str, str]] = []
    for item in parser.scripts:
        src = item.get("src", "")
        if src:
            absolute = urllib.parse.urljoin(base, src)
            if official_url(absolute):
                relevant_scripts.append({"src": absolute, "inline_hint": ""})
            continue
        inline = item.get("inline", "")
        folded = inline.casefold()
        if any(token in folded for token in ("download", "read", "pdf", "attachment", "api", RECORD_ID.casefold())):
            relevant_scripts.append({"src": "", "inline_hint": inline[:2000]})

    forms = []
    for form in parser.forms:
        absolute_action = urllib.parse.urljoin(base, form.get("action", ""))
        if form.get("action") and not official_url(absolute_action):
            continue
        forms.append(
            {
                "action": absolute_action if form.get("action") else "",
                "method": form.get("method", "get"),
                "fields": _redact(form.get("fields", [])),
            }
        )

    report = {
        "schema": "ranah-observatory/bps-opac-outside-java-2005-detail-transport-probe/v1",
        "purpose": "Inspect only the already-verified public OPAC detail page for transport locators exposed by BPS; no identifier enumeration, hidden-route guessing, authentication bypass, or PDF claim.",
        "target": {
            "record_id": RECORD_ID,
            "title": TITLE,
            "detail_url": DETAIL_URL,
        },
        "response": {
            "status": result.get("status"),
            "final_url": result.get("final_url"),
            "content_type": result.get("content_type"),
            "body_bytes": len(body),
            "body_sha256": hashlib.sha256(body).hexdigest() if body else None,
            "body_truncated": result.get("body_truncated"),
            "error": result.get("error"),
            "exact_title_present": TITLE.casefold() in visible.casefold(),
            "record_id_present": RECORD_ID.casefold() in body.decode("utf-8", errors="replace").casefold() if body else False,
        },
        "relevant_official_links": relevant_links,
        "forms": forms,
        "relevant_scripts": relevant_scripts,
        "hidden_route_guessing_performed": False,
        "authentication_bypass_attempted": False,
        "pdf_acquisition_attempted": False,
    }
    path = OUTDIR / "bps-opac-outside-java-2005-detail-transport-probe.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
