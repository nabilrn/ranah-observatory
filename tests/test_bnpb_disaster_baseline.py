from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from fingerprint_bnpb_disaster import fingerprint  # noqa: E402


SOURCE_FIELDS = [
    "source_row_id", "source_record_id", "metric_family", "canonical_geography_id",
    "source_geography_code", "source_geography_name", "year", "disaster_type",
    "value_numeric", "unit", "promotion_status", "source_snapshot_sha256", "notes",
]
CANONICAL_FIELDS = [
    "observation_id", "indicator_id", "geography_id", "time_start", "time_end", "frequency",
    "value_numeric", "unit", "claim_type", "provenance_id", "suppressed", "comparable",
    "methodology_version", "price_basis", "notes",
]


def _write(root: Path, *, value: str = "3", volatile: str = "a" * 64) -> None:
    source = {
        "source_row_id": "source-" + volatile[:4],
        "source_record_id": "bnpb_events_by_type_kab_2024_primary",
        "metric_family": "recorded_disaster_events_by_type",
        "canonical_geography_id": "idn.13.1302",
        "source_geography_code": "1301",
        "source_geography_name": "PESISIR SELATAN",
        "year": "2024",
        "disaster_type": "BANJIR",
        "value_numeric": value,
        "unit": "count",
        "promotion_status": "canonical_ready",
        "source_snapshot_sha256": volatile,
        "notes": "reviewed source pair",
    }
    canonical = {
        "observation_id": "obs-" + volatile[:4],
        "indicator_id": "flood_events",
        "geography_id": "idn.13.1302",
        "time_start": "2024-01-01",
        "time_end": "2024-12-31",
        "frequency": "annual",
        "value_numeric": value,
        "unit": "count",
        "claim_type": "observed",
        "provenance_id": "prov-" + volatile[:4],
        "suppressed": "false",
        "comparable": "",
        "methodology_version": "BNPB/DIBI 2024 event classification",
        "price_basis": "",
        "notes": "source_geography=1301:PESISIR SELATAN",
    }
    with (root / "bnpb-disaster-source-native.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SOURCE_FIELDS)
        writer.writeheader(); writer.writerow(source)
    with (root / "bnpb-disaster-canonical-observations.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CANONICAL_FIELDS)
        writer.writeheader(); writer.writerow(canonical)
    (root / "bnpb-disaster-panel.manifest.json").write_text(
        json.dumps({
            "source_id": "bnpb_satu_data",
            "official_crosscheck": "passed",
            "geography_mapping": "explicit_permendagri_current_crosswalk",
            "mapped_geography_count": 1,
            "canonical_indicators": ["flood_events"],
        }) + "\n",
        encoding="utf-8",
    )


class BNPBDisasterFingerprintTests(unittest.TestCase):
    def test_retrieval_only_identifiers_do_not_change_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write(root, volatile="a" * 64)
            first, _ = fingerprint(root)
            _write(root, volatile="b" * 64)
            second, _ = fingerprint(root)
            self.assertEqual(first, second)

    def test_observation_value_change_changes_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write(root, value="3")
            first, _ = fingerprint(root)
            _write(root, value="4")
            second, _ = fingerprint(root)
            self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
