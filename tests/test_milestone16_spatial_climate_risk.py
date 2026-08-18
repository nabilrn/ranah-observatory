from __future__ import annotations

import csv
import unittest
from pathlib import Path

from scripts.audit_milestone16_spatial_climate_risk import audit

ROOT = Path(__file__).resolve().parents[1]
FRAME = ROOT / "data/analysis/engine/spatial_climate_risk_v1/m16-spatial-component-frame.csv"
REGISTRY = ROOT / "data/analysis/engine/spatial_climate_risk_v1/m16-evidence-component-registry.csv"


class Milestone16Tests(unittest.TestCase):
    def test_completion_audit_is_clean(self) -> None:
        report = audit()
        self.assertEqual(report["errors"], [])
        self.assertTrue(report["milestone16_complete"])
        self.assertEqual(report["geography_count"], 19)
        self.assertEqual(report["component_registry_count"], 12)
        self.assertFalse(report["risk_synthesis_authorized"])

    def test_frame_never_authorizes_risk_synthesis(self) -> None:
        with FRAME.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 19)
        self.assertTrue(all(row["risk_synthesis_authorized"] == "False" for row in rows))
        self.assertTrue(all(row["cross_event_temporal_aggregation_authorized"] == "False" for row in rows))
        self.assertTrue(all(row["qualified_exposure_component_present"] == "False" for row in rows))
        self.assertTrue(all(row["qualified_vulnerability_component_present"] == "False" for row in rows))
        self.assertFalse(any("risk_score" in column or "risk_rank" in column for column in rows[0]))

    def test_inarisk_endpoints_remain_blocked(self) -> None:
        with REGISTRY.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        inarisk = [row for row in rows if "inarisk" in row["evidence_id"]]
        self.assertEqual(len(inarisk), 4)
        self.assertTrue(all(row["evidence_state"] == "endpoint_verified_version_binding_unresolved" for row in inarisk))
        self.assertTrue(all(row["substantive_frame_authorized"] == "False" for row in inarisk))

    def test_event_occurrence_is_not_observed_impact(self) -> None:
        with REGISTRY.open("r", encoding="utf-8", newline="") as handle:
            rows = {row["evidence_id"]: row for row in csv.DictReader(handle)}
        self.assertEqual(rows["m16_o1_bnpb_flood_events_2024"]["component_class"], "recorded_event_occurrence")
        self.assertEqual(rows["m16_o2_bnpb_landslide_events_2024"]["component_class"], "recorded_event_occurrence")
        self.assertEqual(rows["m16_i1_observed_impact_gap"]["evidence_state"], "qualified_component_missing")


if __name__ == "__main__":
    unittest.main()
