#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

RECORD_ID = "111.0614.1380"
TITLE = "Profil Perusahaan Konstruksi di Luar Pulau Jawa 2005"
PUBLICATION_NUMBER = "05230.0610"
ISBN = "979-724-565-9"
DETAIL_URL = f"https://perpustakaan.bps.go.id/opac/details/{RECORD_ID}"
READ_URL = f"https://perpustakaan.bps.go.id/opac/read/{RECORD_ID}.pdf"
DISCOVERY_RUN_ID = 33156939897
DISCOVERY_JOB_ID = 98801856553
DISCOVERY_ARTIFACT_ID = 9679984516
DISCOVERY_ARTIFACT_ZIP_SHA256 = "45fb60bc75a61857d9e97f85b70d9b28e4c0f859edb28c2891d9c9ae686a04af"
OUTDIR = Path("probe-output")
USER_AGENT = "ranah-observatory/0.1 (+https://github.com/nabilrn/ranah-observatory)"
MAX_BODY = 100_000_000


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


def fetch(url: str) -> dict[str, Any]:
    """Fetch one verified official locator without record-ID discovery."""
    if not official_url(url):
        raise ValueError(f"non-official URL: {url}")
    opener = urllib.request.build_opener(OfficialRedirectHandler())
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/pdf,text/html,*/*",
            "Referer": "https://perpustakaan.bps.go.id/opac/search",
        },
    )
    try:
        with opener.open(request, timeout=90) as response:
            final_url = str(response.geturl())
            if not official_url(final_url):
                raise ValueError(f"non-official final URL: {final_url}")
            body = response.read(MAX_BODY + 1)
            truncated = len(body) > MAX_BODY
            if truncated:
                body = body[:MAX_BODY]
            return {
                "status": int(response.status),
                "requested_url": url,
                "final_url": final_url,
                "content_type": str(response.headers.get("Content-Type", "")),
                "content_length_header": str(response.headers.get("Content-Length", "")),
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
            "requested_url": url,
            "final_url": str(exc.geturl()),
            "content_type": str(exc.headers.get("Content-Type", "")) if exc.headers else "",
            "content_length_header": str(exc.headers.get("Content-Length", "")) if exc.headers else "",
            "body": body,
            "body_truncated": truncated,
            "error": f"HTTPError:{exc.code}",
        }
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return {
            "status": None,
            "requested_url": url,
            "final_url": None,
            "content_type": "",
            "content_length_header": "",
            "body": b"",
            "body_truncated": False,
            "error": f"{type(exc).__name__}:{exc}",
        }


def summarize(result: dict[str, Any]) -> dict[str, Any]:
    """Summarize transport identity without persisting volatile login tokens."""
    body = result.get("body") or b""
    summary = {
        key: result.get(key)
        for key in (
            "status",
            "requested_url",
            "final_url",
            "content_type",
            "content_length_header",
            "body_truncated",
            "error",
        )
    }
    summary["body_bytes"] = len(body)
    summary["body_sha256"] = hashlib.sha256(body).hexdigest() if body else None
    summary["pdf_signature"] = body.startswith(b"%PDF-")
    summary["pdf_eof"] = b"%%EOF" in body[-4096:]
    summary["complete_pdf"] = (
        result.get("status") == 200
        and result.get("body_truncated") is False
        and summary["pdf_signature"]
        and summary["pdf_eof"]
    )
    if not summary["complete_pdf"] and body:
        text = body.decode("utf-8", errors="replace")
        text = re.sub(r'(?i)(csrfToken|csrf_token|_token)\\?"?\s*:\s*\\?"[^"]+\\?"', r'\1":"<redacted>"', text)
        visible = re.sub(r"<[^>]+>", " ", text)
        visible = re.sub(r"\s+", " ", visible).strip()
        summary["response_excerpt"] = visible[:1200]
    return summary


def main() -> int:
    """Attempt acquisition only from the exact locator discovered by the official search."""
    OUTDIR.mkdir(parents=True, exist_ok=True)
    result = fetch(READ_URL)
    summary = summarize(result)
    report: dict[str, Any] = {
        "schema": "ranah-observatory/bps-opac-outside-java-2005-verified-softcopy-probe/v1",
        "purpose": "Acquire only the verified OPAC read locator discovered by an earlier exact-title official search; no identifier guessing or enumeration.",
        "target": {
            "record_id": RECORD_ID,
            "title": TITLE,
            "publication_number": PUBLICATION_NUMBER,
            "isbn": ISBN,
            "detail_url": DETAIL_URL,
            "read_url": READ_URL,
        },
        "locator_provenance": {
            "discovery_method": "official OPAC exact-title GET search",
            "discovery_run_id": DISCOVERY_RUN_ID,
            "discovery_job_id": DISCOVERY_JOB_ID,
            "discovery_artifact_id": DISCOVERY_ARTIFACT_ID,
            "discovery_artifact_zip_sha256": DISCOVERY_ARTIFACT_ZIP_SHA256,
            "exact_title_link_observed": True,
            "matching_detail_and_read_record_id_observed": True,
        },
        "softcopy_response": summary,
        "raw_pdf_candidate_saved": False,
    }
    if summary["complete_pdf"]:
        body = result["body"]
        path = OUTDIR / "profil-perusahaan-konstruksi-luar-jawa-2005-candidate.pdf"
        path.write_bytes(body)
        summary["saved_path"] = path.as_posix()
        summary["exact_sha256"] = hashlib.sha256(body).hexdigest()
        summary["exact_bytes"] = len(body)
        report["raw_pdf_candidate_saved"] = True

    (OUTDIR / "bps-opac-outside-java-2005-verified-softcopy-probe.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
