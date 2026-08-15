from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_bnpb_snapshot_geography import expected_pairs, validate_snapshot  # noqa: E402


MAP = ROOT / "data" / "registries" / "bnpb_geography_map.csv"


def _snapshot(path: Path, pairs: dict[str, str]) -> None:
    records = [
        {
            "_id": index,
            "Kode Wilayah Kabupaten / Kota": int(code),
            "Nama Kabupaten/Kota": name,
        }
        for index, (code, name) in enumerate(sorted(pairs.items()), start=1)
    ]
    payload = {
        "snapshot_schema": "ranah-observatory/bnpb-ckan-snapshot/v1",
        "source_id": "bnpb_satu_data",
        "retrieved_at_utc": "2026-08-15T00:00:00+00:00",
        "command": "datastore",
        "filters": {"resource_id": "fixture"},
        "result": {"records": records, "fields": [], "total": len(records)},
    }
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


class BNPBSnapshotGeographyTests(unittest.TestCase):
    def test_exact_reviewed_code_name_pairs_pass(self) -> None:
        pairs = expected_pairs(MAP)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "snapshot.json"
            _snapshot(path, pairs)
            self.assertEqual(validate_snapshot(path, pairs), [])

    def test_code_name_drift_fails_before_mapping(self) -> None:
        pairs = expected_pairs(MAP)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "snapshot.json"
            bad = dict(pairs)
            bad["1301"] = "KEPULAUAN MENTAWAI"
            _snapshot(path, bad)
            errors = validate_snapshot(path, pairs)
            self.assertTrue(any("source code/name drift for 1301" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
