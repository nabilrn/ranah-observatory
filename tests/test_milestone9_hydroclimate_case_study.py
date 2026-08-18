from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/manifests/milestone9_hydroclimate_case_study.json"
GATE = ROOT / "data/manifests/milestone9_design_gate.json"
FRAME = ROOT / "data/analysis/climate_disaster/m9-hydroclimate-2024-geography-frame.csv"
CORR = ROOT / "data/analysis/climate_disaster/m9-hydroclimate-2024-correlations.csv"
LOO = ROOT / "data/analysis/climate_disaster/m9-hydroclimate-2024-leave-one-out.csv"


def read_csv(path: Path):
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class Milestone9HydroclimateCaseStudyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.gate = json.loads(GATE.read_text(encoding="utf-8"))
        cls.frame = read_csv(FRAME)
        cls.corr = read_csv(CORR)
        cls.loo = read_csv(LOO)

    def test_completion_gate(self):
        self.assertTrue(self.manifest["milestone9_complete"])
        self.assertEqual(self.manifest["criterion"], "one climate/disaster case study relevant to West Sumatra")
        self.assertEqual(self.manifest["claim_classification"], "descriptive_climate_disaster_spatial_case_study")

    def test_preanalysis_gate_stays_preanalysis(self):
        self.assertFalse(self.gate["association_computed"])
        self.assertFalse(self.gate["milestone9_complete"])
        self.assertEqual(self.gate["study_year"], 2024)
        self.assertEqual(self.gate["baseline_year_count"], 43)

    def test_exact_geography_and_output_footprints(self):
        self.assertEqual(len(self.frame), 19)
        self.assertEqual(len({row["geography_id"] for row in self.frame}), 19)
        self.assertEqual(len(self.corr), 6)
        self.assertEqual(len(self.loo), 57)

    def test_evidence_classes_and_claim_boundary(self):
        self.assertEqual(self.manifest["climate_claim_type"], "model_estimate")
        self.assertEqual(self.manifest["independent_station_validation"], "pending")
        self.assertFalse(self.manifest["station_observation_equivalence"])
        self.assertFalse(self.manifest["causal_attribution_performed"])
        self.assertFalse(self.manifest["climate_change_attribution_performed"])
        self.assertFalse(self.manifest["daily_rainfall_claim_performed"])

    def test_zero_event_geographies_are_not_dropped(self):
        self.assertTrue(self.manifest["zero_event_geographies_retained"])
        self.assertTrue(any(float(row["landslide_events"]) == 0 for row in self.frame))
        self.assertEqual(len(self.frame), 19)

    def test_all_preregistered_associations_reported(self):
        pairs = {(row["climate_metric"], row["disaster_metric"]) for row in self.corr}
        expected = {
            (climate, disaster)
            for climate in {"rainfall_z_2024", "rainfall_2024_mm"}
            for disaster in {"flood_events", "landslide_events", "hydroclimate_event_count"}
        }
        self.assertEqual(pairs, expected)
        self.assertTrue(all(row["claim_scope"] == "descriptive_spatial_association_not_causal" for row in self.corr))


if __name__ == "__main__":
    unittest.main()
