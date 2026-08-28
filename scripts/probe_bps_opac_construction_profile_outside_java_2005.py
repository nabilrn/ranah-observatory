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

BASE = "https://perpustakaan.bps.go.id"
TITLE = "Profil Perusahaan Konstruksi di Luar Pulau Jawa 2005"
PUBLICATION_NUMBER = "05230.0610"
ISBN = "979-724-565-9"
SEARCH_URL = f"{BASE}/opac/search?" + urllib.parse.urlencode({"q": TITLE, "media": "no"})
OUTDIR = Path("probe-output")
USER_AGENT = "ranah-observatory/0.1 (+https://github.com/nabilrn/ranah-observatory)"
MAX_BODY = 12_000_000
DETAIL_RE = re.compile(r"/opac/details/([^/?#]+)$", re.I)
READ_RE = re.compile(r"/opac/read/([^/?#]+)\.pdf$", re.I)


class LinkParser(HTMLParser):
    """Collect visible text and links from the public OPAC result page."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, str]] = []
        self.text_parts: list[str] = []
        self._link: dict[str, str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: (value or "") for key, value in attrs}
        if tag == "a" and values.get("href"):
            self._link = {"href": values["href"], "text": ""}
            self.links.append(self._link)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a":
            self._link = None

    def handle_data(self, data: str) -> None:
        text = re.sub(r"\s+", " ", data).strip()
        if not text:
            return
        self.text_parts.append(text)
        if self._link is not None:
            self._link["text"] = (self._link["text"] + " " + text).strip()


def official_url(url: str) -> bool:
    """Allow only HTTPS BPS domains."""
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    return parsed.scheme == "https" and (host == "bps.go.id" or host.endswith(".bps.go.id"))


class OfficialRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject redirects outside the BPS domain family."""

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
    """Fetch only the exact-title search URL already observed on public OPAC."""
    if not official_url(SEARCH_URL):
        raise ValueError("search URL is outside BPS allowlist")
    opener = urllib.request.build_opener(OfficialRedirectHandler())
    request = urllib.request.Request(
        SEARCH_URL,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"},
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
                "requested_url": SEARCH_URL,
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
            "requested_url": SEARCH_URL,
            "final_url": str(exc.geturl()),
            "content_type": str(exc.headers.get("Content-Type", "")) if exc.headers else "",
            "body": body,
            "body_truncated": truncated,
            "error": f"HTTPError:{exc.code}",
        }
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return {
            "status": None,
            "requested_url": SEARCH_URL,
            "final_url": None,
            "content_type": "",
            "body": b"",
            "body_truncated": False,
            "error": f"{type(exc).__name__}:{exc}",
        }


def record_id(url: str) -> str | None:
    """Extract a record ID from an OPAC detail/read URL."""
    path = urllib.parse.urlparse(url).path
    detail = DETAIL_RE.search(path)
    if detail:
        return detail.group(1)
    read = READ_RE.search(path)
    if read:
        return read.group(1)
    return None


def main() -> int:
    """Recover exact-title locator pairs only; never download or save a PDF."""
    OUTDIR.mkdir(parents=True, exist_ok=True)
    result = fetch()
    body = result.get("body") or b""
    parser = LinkParser()
    if body:
        parser.feed(body.decode("utf-8", errors="replace"))
    visible = re.sub(r"\s+", " ", " ".join(parser.text_parts)).strip()
    folded_title = TITLE.casefold()

    groups: dict[str, dict[str, str]] = {}
    for item in parser.links:
        absolute = urllib.parse.urljoin(
            str(result.get("final_url") or result.get("requested_url")), item["href"]
        )
        if not official_url(absolute):
            continue
        rec = record_id(absolute)
        if not rec:
            continue
        group = groups.setdefault(rec, {})
        path = urllib.parse.urlparse(absolute).path
        if "/opac/details/" in path:
            group["detail_url"] = absolute
            if folded_title in item.get("text", "").casefold():
                group["exact_title_text"] = item.get("text", "")
        elif "/opac/read/" in path:
            group["read_url"] = absolute

    exact_records = []
    for rec, group in sorted(groups.items()):
        if folded_title not in group.get("exact_title_text", "").casefold():
            continue
        exact_records.append(
            {
                "record_id": rec,
                "title_text": group.get("exact_title_text", ""),
                "detail_url": group.get("detail_url"),
                "read_url": group.get("read_url"),
                "matching_detail_and_read_record_id": bool(
                    group.get("detail_url") and group.get("read_url")
                ),
            }
        )

    anti_bot_challenge = "please wait while your request is being verified" in visible.casefold()
    report = {
        "schema": "ranah-observatory/bps-opac-outside-java-2005-locator-probe/v1",
        "purpose": "Recover only exact-title public OPAC locator pairs; no record-ID guessing, enumeration, detail traversal, or PDF download.",
        "target_title": TITLE,
        "publication_number": PUBLICATION_NUMBER,
        "isbn": ISBN,
        "search_url": SEARCH_URL,
        "response": {
            "status": result.get("status"),
            "final_url": result.get("final_url"),
            "content_type": result.get("content_type"),
            "body_bytes": len(body),
            "body_sha256": hashlib.sha256(body).hexdigest() if body else None,
            "body_truncated": result.get("body_truncated"),
            "error": result.get("error"),
            "anti_bot_challenge": anti_bot_challenge,
            "exact_title_present": folded_title in visible.casefold(),
        },
        "exact_title_records": exact_records,
        "record_id_guessed_or_bruteforced": False,
        "pdf_download_attempted": False,
    }
    (OUTDIR / "bps-opac-outside-java-2005-locator-probe.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
