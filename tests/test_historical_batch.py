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

from historical_batch_collect import (  # noqa: E402
    newest_changed_pdf,
    official_bps_url,
    official_source_url,
    queue_allowed_host,
    read_queue,
)
from historical_batch_ingest import inspect_batch, write_manifest  # noqa: E402
from validate_historical_batch import (  # noqa: E402
    ALLOWED_COMMITTED_PDFS,
    REQUIRED_P0,
    find_disallowed_committed_pdfs,
    validate,
)


PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"


class HistoricalBatchTests(unittest.TestCase):
    def test_batch_validator_passes(self) -> None:
        errors, counts = validate()
        self.assertEqual([], errors, "\n".join(errors))
        self.assertGreaterEqual(counts["queue"], 13)
        self.assertEqual(8, counts["p0"])

    def test_committed_pdf_guard_allows_only_explicit_distribution_pdf(self) -> None:
        canonical_path = (
            "publication/v0.1/distribution/"
            "Ranah_Observatory_v0.1_Preprint_Nabil_Rizki_Navisa.pdf"
        )
        self.assertIn(canonical_path, ALLOWED_COMMITTED_PDFS)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            canonical = root / canonical_path
            canonical.parent.mkdir(parents=True)
            canonical.write_bytes(PDF_BYTES)
            self.assertEqual([], find_disallowed_committed_pdfs(root))

            rogue = root / "publication" / "scratch.pdf"
            rogue.write_bytes(PDF_BYTES)
            self.assertEqual(
                ["publication/scratch.pdf"],
                find_disallowed_committed_pdfs(root),
            )

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

    def test_generic_official_host_validation_supports_bpbd_queue_safely(self) -> None:
        self.assertTrue(
            official_source_url("https://bpbd.sumbarprov.go.id/ppid", "sumbarprov.go.id")
        )
        self.assertTrue(
            official_source_url("https://www.sumbarprov.go.id/images/report.pdf", "sumbarprov.go.id")
        )
        self.assertFalse(
            official_source_url("https://sumbarprov.go.id.evil.example/report.pdf", "sumbarprov.go.id")
        )
        self.assertFalse(
            official_source_url("http://bpbd.sumbarprov.go.id/ppid", "sumbarprov.go.id")
        )
        self.assertFalse(
            official_source_url("https://bpbd.sumbarprov.go.id/ppid", "https://sumbarprov.go.id")
        )

    def test_bpbd_acquisition_queue_is_allowlisted_and_has_2017_exit_gate(self) -> None:
        queue_path = ROOT / "data" / "acquisition_requests" / "bpbd_publications.csv"
        rows = read_queue(queue_path)
        core_ids = {
            "bpbd_pusdalops_2015",
            "bpbd_pusdalops_2017",
            "bpbd_data_kebencanaan_2015_2016",
            "bpbd_lakip_2017",
            "bpbd_pusdalops_2018",
        }
        self.assertGreaterEqual(len(rows), len(core_ids))
        by_id = {row["request_id"]: row for row in rows}
        self.assertEqual(len(rows), len(by_id))
        self.assertTrue(core_ids.issubset(by_id))

        target = by_id["bpbd_pusdalops_2017"]
        self.assertEqual("P0", target["priority"])
        self.assertEqual("2017", target["anchor_year"])
        self.assertEqual("yes", target["exit_gate_candidate"])
        self.assertEqual("sumbarprov.go.id", queue_allowed_host(target))
        self.assertEqual(
            ["bpbd_pusdalops_2017"],
            [row["request_id"] for row in rows if row["exit_gate_candidate"] == "yes"],
        )
        for request_id, row in by_id.items():
            self.assertTrue(
                official_source_url(row["official_page_url"], queue_allowed_host(row)),
                request_id,
            )
            if request_id != "bpbd_pusdalops_2017":
                self.assertEqual("no", row["exit_gate_candidate"])

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
