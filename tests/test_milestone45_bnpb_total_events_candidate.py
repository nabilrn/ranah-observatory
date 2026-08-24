from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_milestone45_bnpb_total_events_candidate import (
    DEFAULT_GEOGRAPHIES,
    DEFAULT_M44,
    DEFAULT_PACKAGE_METADATA,
    DEFAULT_SOURCE,
    build,
    sha256_file,
    write_csv,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/manifests/milestone45_bnpb_total_events_candidate.json"


class Milestone45TotalEventsCandidateTest(unittest.TestCase):
    def test_frozen_candidate_rebuilds_exactly(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        rows, provenance, summary = build(
            DEFAULT_SOURCE,
            DEFAULT_GEOGRAPHIES,
            DEFAULT_PACKAGE_METADATA,
            DEFAULT_M44,
        )

        self.assertEqual(len(rows), 285)
        self.assertEqual(summary["observation_count"], 285)
        self.assertEqual(summary["geography_count"], 19)
        self.assertEqual(summary["years_count"], 15)
        self.assertTrue(summary["complete_geography_year_matrix"])
        self.assertEqual(summary["minimum_value"], 0)
        self.assertEqual(summary["maximum_value"], 68)
        self.assertEqual(summary["year_sums"], manifest["year_sums"])
        self.assertEqual(sum(summary["year_sums"].values()), manifest["all_year_sum"])
        self.assertEqual(
            provenance["source_snapshot_sha256"],
            manifest["source"]["source_snapshot_sha256"],
        )
        self.assertEqual(
            provenance["frozen_processed_source_sha256"],
            manifest["source"]["frozen_processed_source_sha256"],
        )
        self.assertEqual(
            provenance["provenance_id"],
            manifest["candidate_artifact"]["provenance_id"],
        )

        with tempfile.TemporaryDirectory() as tmp:
            candidate = Path(tmp) / "candidate.csv"
            write_csv(candidate, rows)
            self.assertEqual(
                sha256_file(candidate),
                manifest["candidate_artifact"]["sha256"],
            )
            parsed = list(csv.DictReader(candidate.open(encoding="utf-8", newline="")))

        self.assertEqual(len(parsed), 285)
        self.assertEqual({row["indicator_id"] for row in parsed}, {"total_disaster_events"})
        self.assertEqual({row["unit"] for row in parsed}, {"count"})
        self.assertEqual({row["claim_type"] for row in parsed}, {"observed"})
        self.assertEqual({row["comparable"] for row in parsed}, {""})
        self.assertTrue(all("exact_polygon_harmonization=not_proven" in row["notes"] for row in parsed))

    def test_promotion_boundary_remains_narrow(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        q = manifest["qualification"]
        self.assertTrue(q["candidate_artifact_reproducible"])
        self.assertTrue(q["within_source_longitudinal_use_authorized_with_caveat"])
        self.assertFalse(q["exact_polygon_harmonization_proven"])
        self.assertTrue(q["type_specific_interpretation_forbidden"])
        self.assertTrue(q["true_incidence_claim_forbidden"])
        self.assertFalse(q["global_indicator_registry_update_authorized"])
        self.assertFalse(q["global_panel_integration_authorized"])


if __name__ == "__main__":
    unittest.main()
