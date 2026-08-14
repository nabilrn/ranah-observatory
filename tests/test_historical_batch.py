from __future__ import annotations

import csv
import hashlib
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from historical_batch_collect import newest_changed_pdf, official_bps_url  # noqa: E402
from historical_batch_ingest import inspect_batch, write_manifest  # noqa: E402
from validate_historical_batch import REQUIRED_P0, validate  # noqa: E402


PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"


class HistoricalBatchTests(unittest.TestCase):
    def test_batch_validator_passes(self) -> None:
        errors, counts = validate()
        self.assertEqual([], errors, "\n".join(errors))
        self.assertGreaterEqual(counts["queue"], 13)
        self.assertEqual(8, counts["p0"])

    def test_anchor_strategy_is_present(self) -> None:
        queue_path = ROOT / "data" / "acquisition_requests" / "bps_publications.csv"
        with queue_path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        by_id = {row["request_id"]: row for row in rows}
        self.assertTrue(REQUIRED_P0.issubset(by_id))
        self.assertEqual({"yes"}, {by_id[item]["exit_gate_candidate"] for item in {"sp1961_indonesia", "sp1971_sumbar_e3"}})

    def test_official_url_validation_rejects_suffix_trick(self) -> None:
        self.assertTrue(official_bps_url("https://sumbar.bps.go.id/id/publication/example"))
        self.assertTrue(official_bps_url("https://perpustakaan.bps.go.id/opac/search"))
        self.assertFalse(official_bps_url("https://bps.go.id.evil.example/publication"))
        self.assertFalse(official_bps_url("http://sumbar.bps.go.id/publication"))

    def test_newest_changed_pdf_detects_browser_download(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            downloads = Path(directory)
            old = downloads / "old.pdf"
            old.write_bytes(PDF_BYTES)
            before = {old.resolve(): (old.stat().st_mtime_ns, old.stat().st_size)}
            started = time.time()
            fresh = downloads / "fresh.pdf"
            fresh.write_bytes(PDF_BYTES + b"\n")
            candidates = newest_changed_pdf(downloads, before, started_at=started)
            self.assertEqual(fresh, candidates[0])

    def test_ingest_hashes_exact_bytes_and_writes_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            queue = root / "queue.csv"
            inbox = root / "inbox"
            manifest = root / "manifest.csv"
            inbox.mkdir()
            queue.write_text(
                "request_id,source_record_id,title,official_page_url,output_filename,priority,anchor_year,exit_gate_candidate,purpose\n"
                "fixture,bps_publication_web,Fixture,https://sumbar.bps.go.id/id/publication/example,fixture.pdf,P0,1971,yes,Test\n",
                encoding="utf-8",
            )
            artifact = inbox / "fixture.pdf"
            artifact.write_bytes(PDF_BYTES)
            verified, missing, errors = inspect_batch(queue, inbox, manifest)
            self.assertEqual([], missing)
            self.assertEqual([], errors)
            self.assertEqual(1, len(verified))
            self.assertEqual(hashlib.sha256(PDF_BYTES).hexdigest(), verified[0]["sha256"])
            self.assertEqual("artifact_verified", verified[0]["verification_state"])
            write_manifest(manifest, verified)
            with manifest.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual("fixture", rows[0]["request_id"])


if __name__ == "__main__":
    unittest.main()
