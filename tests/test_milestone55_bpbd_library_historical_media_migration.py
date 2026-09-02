from __future__ import annotations

import unittest

from scripts.validate_milestone55_bpbd_library_historical_media_migration import validate


class Milestone55BPBDLibraryHistoricalMediaMigrationTests(unittest.TestCase):
    def test_migration_gap_is_frozen_without_promoting_2022_artifacts(self) -> None:
        report = validate()
        self.assertTrue(report["complete"])
        self.assertEqual(report["lkj_category_rows"], 5)
        self.assertEqual(report["newer_pdf_objects_recovered"], 2)
        self.assertEqual(report["historical_objects_missing"], 3)
        self.assertEqual(report["dibi_literal_matches"], 0)
        self.assertFalse(report["lkj_2022_raw_artifact_acquired"])
        self.assertFalse(report["dibi_2022_route_found"])
        self.assertFalse(report["canonical_2022_series_authorized"])


if __name__ == "__main__":
    unittest.main()
