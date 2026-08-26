from __future__ import annotations

import csv
import json
import unittest

from scripts import build_milestone37_bnpb_observed_impact as m37


class Milestone37BnpbObservedImpactTests(unittest.TestCase):
    def test_snapshot_identity_and_known_values(self) -> None:
        snapshot = m37.load_snapshot()
        lookup = {(r["year"], r["metric_id"]): r for r in snapshot["records"]}
        self.assertEqual(lookup[(2024, "deaths")]["values"]["BANJIR"], 61)
        self.assertEqual(lookup[(2024, "deaths")]["values"]["TANAH LONGSOR"], 23)
        self.assertEqual(lookup[(2025, "deaths")]["values"]["BANJIR"], 267)
        self.assertEqual(lookup[(2025, "deaths")]["values"]["CUACA EKSTREM"], 3)
        self.assertFalse(snapshot["storage_boundary"]["full_workbooks_committed"])
        self.assertTrue(snapshot["storage_boundary"]["workbook_sha256_recorded"])

    def test_source_blank_is_not_coerced_to_zero(self) -> None:
        snapshot = m37.load_snapshot()
        record = next(r for r in snapshot["records"] if r["year"] == 2024 and r["metric_id"] == "displaced")
        self.assertIsNone(record["values"]["GEMPABUMI"])
        self.assertEqual(record["values"]["CUACA EKSTREM"], 0)

    def test_build_preserves_locked_coverage_and_boundaries(self) -> None:
        csv_sha_1, manifest_sha_1 = m37.build()
        csv_sha_2, manifest_sha_2 = m37.build()
        self.assertEqual((csv_sha_1, manifest_sha_1), (csv_sha_2, manifest_sha_2))

        with m37.OUT_CSV.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 90)
        self.assertEqual(sum(r["source_cell_state"] == "reported_numeric" for r in rows), 89)
        self.assertEqual(sum(r["source_cell_state"] == "source_blank" for r in rows), 1)

        blank = next(r for r in rows if r["source_cell_state"] == "source_blank")
        self.assertEqual((blank["year"], blank["metric_id"], blank["hazard"], blank["value"]), ("2024", "displaced", "GEMPABUMI", ""))

        manifest = json.loads(m37.OUT_MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["qualification"]["classification"], "qualified_source_native_provincial_observed_impact_context")
        self.assertTrue(manifest["qualification"]["observed_impact_context_authorized"])
        for key in (
            "event_level_observed_impact_authorized",
            "district_city_observed_impact_authorized",
            "unique_person_annual_aggregation_authorized",
            "cross_hazard_person_sum_authorized",
            "cross_metric_composite_authorized",
            "risk_synthesis_authorized",
            "causal_claim_authorized",
            "monetary_loss_inference_authorized",
            "policy_ranking_authorized",
        ):
            self.assertFalse(manifest["qualification"][key])


if __name__ == "__main__":
    unittest.main()
