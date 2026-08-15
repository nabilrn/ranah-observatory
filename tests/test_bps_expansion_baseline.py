from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from fingerprint_bps_expansion import semantic_fingerprint  # noqa: E402


class BPSExpansionBaselineTests(unittest.TestCase):
    def test_fingerprint_ignores_retrieval_only_volatility(self) -> None:
        row = {
            "expansion_row_id": "row-1",
            "expansion_series_id": "underemployment_regency",
            "raw_value": "4.50",
            "denominator_raw_value": "",
            "bps_last_update": "2024-11-21 14:32:39",
            "canonical_geography_id": "idn.13.1301",
            "transform": "identity",
            "retrieved_at_utc": "2026-08-15T00:00:00+00:00",
            "source_snapshot": "a.json",
            "source_snapshot_sha256": "a" * 64,
        }
        rerun = copy.deepcopy(row)
        rerun["retrieved_at_utc"] = "2026-08-16T00:00:00+00:00"
        rerun["source_snapshot"] = "b.json"
        rerun["source_snapshot_sha256"] = "b" * 64
        self.assertEqual(semantic_fingerprint([row]), semantic_fingerprint([rerun]))

    def test_fingerprint_detects_value_and_source_revision(self) -> None:
        row = {
            "expansion_row_id": "row-1",
            "raw_value": "4.50",
            "bps_last_update": "2024-11-21 14:32:39",
            "retrieved_at_utc": "2026-08-15T00:00:00+00:00",
            "source_snapshot": "a.json",
            "source_snapshot_sha256": "a" * 64,
        }
        revised_value = copy.deepcopy(row)
        revised_value["raw_value"] = "4.51"
        self.assertNotEqual(semantic_fingerprint([row]), semantic_fingerprint([revised_value]))
        revised_metadata = copy.deepcopy(row)
        revised_metadata["bps_last_update"] = "2026-08-16 00:00:00"
        self.assertNotEqual(semantic_fingerprint([row]), semantic_fingerprint([revised_metadata]))


if __name__ == "__main__":
    unittest.main()
