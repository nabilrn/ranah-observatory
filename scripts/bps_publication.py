from __future__ import annotations

import hashlib
import json
import os
import tempfile
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable

USER_AGENT = "ranah-observatory/0.1 (+https://github.com/nabilrn/ranah-observatory)"
ALLOWED_PAGE_SUFFIX = ".bps.go.id"
ALLOWED_DOWNLOAD_HOSTS = {"web-api.bps.go.id", "cdn.bps.go.id"}


class PublicationAcquisitionError(RuntimeError):
    pass


@dataclass(frozen=True)
class PublicationPage:
    title: str
    page_url: str
    download_url: str


class _PublicationHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._in_h1 = False
        self._h1_parts: list[str] = []
        self.download_href: str | None = None

    @property
    def title(self) -> str:
        return " ".join("".join(self._h1_parts).split())

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = {key.lower(): value for key, value in attrs}
        if tag.lower() == "h1":
            self._in_h1 = True
        if tag.lower() != "a":
            return
        href = attrs_map.get("href") or ""
        parsed = urllib.parse.urlparse(href)
        if "download.php" in parsed.path and "f=" in parsed.query:
            self.download_href = href

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "h1":
            self._in_h1 = False

    def handle_data(self, data: str) -> None:
        if self._in_h1:
            self._h1_parts.append(data)


def _validate_publication_page_url(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not host.endswith(ALLOWED_PAGE_SUFFIX):
        raise PublicationAcquisitionError(
            "publication page must use HTTPS on an official *.bps.go.id host"
        )
    if "/publication/" not in parsed.path:
        raise PublicationAcquisitionError("URL does not look like a BPS publication page")


def _validate_download_url(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or host not in ALLOWED_DOWNLOAD_HOSTS:
        raise PublicationAcquisitionError(
            f"refusing unexpected publication download host: {host or '<missing>'}"
        )


def parse_publication_page(html: str, page_url: str) -> PublicationPage:
    _validate_publication_page_url(page_url)
    parser = _PublicationHTMLParser()
    parser.feed(html)
    if not parser.download_href:
        raise PublicationAcquisitionError("publication download link was not found")
    download_url = urllib.parse.urljoin(page_url, parser.download_href)
    _validate_download_url(download_url)
    return PublicationPage(
        title=parser.title,
        page_url=page_url,
        download_url=download_url,
    )


def _default_open(request: urllib.request.Request, timeout: float):
    return urllib.request.urlopen(request, timeout=timeout)


def fetch_publication_page(
    page_url: str,
    *,
    timeout: float = 30.0,
    opener: Callable = _default_open,
) -> PublicationPage:
    _validate_publication_page_url(page_url)
    request = urllib.request.Request(
        page_url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
    )
    try:
        with opener(request, timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            html = response.read().decode(charset, errors="replace")
    except Exception as exc:  # urllib exposes several transport-specific exceptions
        raise PublicationAcquisitionError(f"failed to fetch publication page: {exc}") from exc
    return parse_publication_page(html, page_url)


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def download_publication(
    page_url: str,
    output_path: str | Path,
    *,
    timeout: float = 90.0,
    opener: Callable = _default_open,
) -> dict[str, object]:
    page = fetch_publication_page(page_url, timeout=timeout, opener=opener)
    request = urllib.request.Request(
        page.download_url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/pdf,*/*;q=0.8"},
    )
    try:
        with opener(request, timeout) as response:
            payload = response.read()
    except Exception as exc:
        raise PublicationAcquisitionError(f"failed to download publication: {exc}") from exc

    if not payload.startswith(b"%PDF-"):
        raise PublicationAcquisitionError(
            "download did not return a PDF; the BPS download token may have expired or been blocked"
        )

    output = Path(output_path)
    _atomic_write(output, payload)
    digest = hashlib.sha256(payload).hexdigest()
    checksum_path = output.with_suffix(output.suffix + ".sha256")
    _atomic_write(checksum_path, f"{digest}  {output.name}\n".encode("utf-8"))

    manifest = {
        "schema_version": 1,
        "source_id": "bps_publication_web",
        "title": page.title,
        "official_page_url": page.page_url,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "sha256": digest,
        "bytes": len(payload),
        "artifact": output.name,
        "acquisition": "official_publication_page_download_link",
        "credential_required": False,
    }
    manifest_path = output.with_suffix(output.suffix + ".manifest.json")
    _atomic_write(
        manifest_path,
        (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    )
    return manifest
