from __future__ import annotations

import json
import tempfile
import unittest
from email.message import Message
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from bps_publication import (  # noqa: E402
    PublicationAcquisitionError,
    download_publication,
    parse_publication_page,
)


PAGE_URL = (
    "https://sumbar.bps.go.id/id/publication/2026/02/27/example/"
    "provinsi-sumatera-barat-dalam-angka-2026.html"
)
HTML = """
<html>
  <body>
    <h1>Provinsi Sumatera Barat Dalam Angka 2026</h1>
    <a href="https://web-api.bps.go.id/download.php?f=opaque-token">Unduh Publikasi</a>
  </body>
</html>
"""


class FakeResponse:
    def __init__(self, payload: bytes, content_type: str) -> None:
        self._payload = payload
        self.headers = Message()
        self.headers["Content-Type"] = content_type

    def read(self) -> bytes:
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class PublicationTests(unittest.TestCase):
    def test_parse_official_publication_page(self) -> None:
        page = parse_publication_page(HTML, PAGE_URL)
        self.assertEqual("Provinsi Sumatera Barat Dalam Angka 2026", page.title)
        self.assertEqual("web-api.bps.go.id", page.download_url.split("/", 3)[2])

    def test_rejects_non_bps_page(self) -> None:
        with self.assertRaises(PublicationAcquisitionError):
            parse_publication_page(HTML, "https://example.com/publication/book.html")

    def test_rejects_unexpected_download_host(self) -> None:
        html = '<h1>Book</h1><a href="https://evil.example/download.php?f=x">download</a>'
        with self.assertRaises(PublicationAcquisitionError):
            parse_publication_page(html, PAGE_URL)

    def test_download_writes_pdf_checksum_and_manifest(self) -> None:
        calls = []

        def opener(request, timeout):
            calls.append(request.full_url)
            if request.full_url == PAGE_URL:
                return FakeResponse(HTML.encode("utf-8"), "text/html; charset=utf-8")
            return FakeResponse(b"%PDF-1.7\nfixture\n", "application/pdf")

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "book.pdf"
            manifest = download_publication(PAGE_URL, output, opener=opener)
            self.assertTrue(output.exists())
            self.assertTrue((Path(str(output) + ".sha256")).exists())
            manifest_path = Path(str(output) + ".manifest.json")
            self.assertTrue(manifest_path.exists())
            stored = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(False, stored["credential_required"])
            self.assertEqual(PAGE_URL, manifest["official_page_url"])
            self.assertEqual(2, len(calls))

    def test_rejects_non_pdf_download(self) -> None:
        def opener(request, timeout):
            if request.full_url == PAGE_URL:
                return FakeResponse(HTML.encode("utf-8"), "text/html; charset=utf-8")
            return FakeResponse(b"Access denied", "text/html")

        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(PublicationAcquisitionError):
                download_publication(PAGE_URL, Path(directory) / "book.pdf", opener=opener)


if __name__ == "__main__":
    unittest.main()
