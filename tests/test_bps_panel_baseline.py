from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_bps_source_panel import semantic_fingerprint  # noqa: E402
from compare_bps_panel_baseline import compare  # noqa: E402
from validate_bps_panel_artifact import validate  # noqa: E402


class BPSPanelBaselineTests(unittest.TestCase):
    def test_committed_baseline_validator_passes(self) -> None:
        errors, counts = validate()
        self.assertEqual([], errors, "\n".join(errors))
        self.assertEqual(8, counts["series"])
        self.assertEqual(1240, counts["rows"])
        self.assertEqual(20, counts["geographies"])

    def test_semantic_fingerprint_ignores_retrieval_artifact_volatility(self) -> None:
        base = {
            "panel_row_id": "series:1301:139:0:125:0",
            "panel_series_id": "series",
            "indicator_id": "unemployment_rate",
            "canonical_promotion_status": "pending_reference_period_review",
            "source_id": "bps_webapi",
            "domain": "1300",
            "retrieved_at_utc": "2026-08-15T00:00:00+00:00",
            "bps_last_update": "2025-11-10 08:58:50",
            "bps_var_id": "139",
            "bps_var_label": "TPT",
            "bps_var_unit": "Persen",
            "bps_var_decimal": "2",
            "bps_var_definition": "",
            "bps_var_note": "Sakernas",
            "bps_subject": "Tenaga Kerja",
            "bps_vertical_dimension": "Kabupaten/Kota",
            "bps_vervar_id": "1301",
            "bps_vervar_label": "Kepulauan Mentawai",
            "bps_turvar_id": "0",
            "bps_turvar_label": "Tidak ada",
            "bps_th_id": "125",
            "bps_th_label": "2025",
            "bps_turth_id": "0",
            "bps_turth_label": "Tahun",
            "value": "4.50",
            "source_key": "130113901250",
            "source_snapshot": "var-139-2025.json",
            "source_snapshot_sha256": "a" * 64,
            "canonical_geography_id": "idn.13.1301",
            "geography_mapping_status": "qualified_current_code",
        }
        rerun = copy.deepcopy(base)
        rerun["retrieved_at_utc"] = "2026-08-16T00:00:00+00:00"
        rerun["source_snapshot_sha256"] = "b" * 64
        self.assertEqual(semantic_fingerprint([base]), semantic_fingerprint([rerun]))

        revised = copy.deepcopy(rerun)
        revised["value"] = "4.51"
        self.assertNotEqual(semantic_fingerprint([base]), semantic_fingerprint([revised]))

        metadata_revision = copy.deepcopy(rerun)
        metadata_revision["bps_last_update"] = "2026-08-16 01:02:03"
        self.assertNotEqual(semantic_fingerprint([base]), semantic_fingerprint([metadata_revision]))

    def test_baseline_comparator_reports_semantic_drift(self) -> None:
        baseline = {
            "source_id": "bps_webapi",
            "series_count": 1,
            "row_count": 20,
            "semantic_fingerprint_sha256": "a" * 64,
            "series": [
                {
                    "panel_series_id": "series",
                    "indicator_id": "unemployment_rate",
                    "bps_var_id": 139,
                    "selected_turvar_id": 0,
                    "period_start": 2025,
                    "period_end": 2025,
                    "rows": 20,
                    "source_last_update": "2025-01-01 00:00:00",
                    "canonical_promotion_status": "pending_reference_period_review",
                }
            ],
        }
        generated = {
            "source_id": "bps_webapi",
            "series_count": 1,
            "row_count": 20,
            "semantic_fingerprint_sha256": "b" * 64,
            "series": [
                {
                    "panel_series_id": "series",
                    "indicator_id": "unemployment_rate",
                    "bps_var_id": 139,
                    "selected_turvar_id": 0,
                    "periods": ["2025"],
                    "rows": 20,
                    "source_last_updates": ["2025-01-01 00:00:00"],
                    "canonical_promotion_status": "pending_reference_period_review",
                }
            ],
        }
        errors = compare(baseline, generated)
        self.assertTrue(any("semantic fingerprint changed" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
