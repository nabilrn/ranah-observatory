from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_bps_canonical_panel import build_canonical  # noqa: E402


class BPSCanonicalPanelTests(unittest.TestCase):
    def _write_fixture(self, root: Path) -> tuple[Path, Path, Path]:
        source = root / "source.csv"
        source_fields = [
            "panel_row_id", "panel_series_id", "indicator_id", "canonical_promotion_status",
            "source_id", "domain", "retrieved_at_utc", "bps_last_update", "bps_var_id",
            "bps_var_label", "bps_var_unit", "bps_var_decimal", "bps_var_definition", "bps_var_note",
            "bps_subject", "bps_vertical_dimension", "bps_vervar_id", "bps_vervar_label",
            "bps_turvar_id", "bps_turvar_label", "bps_th_id", "bps_th_label", "bps_turth_id",
            "bps_turth_label", "value", "source_key", "source_snapshot", "source_snapshot_sha256",
            "canonical_geography_id", "geography_mapping_status",
        ]
        rows = [
            {
                "panel_row_id": "tpt:1301:139:0:125:0", "panel_series_id": "tpt", "indicator_id": "unemployment_rate",
                "canonical_promotion_status": "canonical_ready", "source_id": "bps_webapi", "domain": "1300",
                "retrieved_at_utc": "2026-08-15T00:00:00+00:00", "bps_last_update": "2025-11-10 08:58:50",
                "bps_var_id": "139", "bps_var_label": "TPT", "bps_var_unit": "Persen", "bps_var_decimal": "2",
                "bps_var_definition": "2018-2021 menggunakan estimasi dari hasil proyeksi SUPAS 2015", "bps_var_note": "Sakernas",
                "bps_subject": "Tenaga Kerja", "bps_vertical_dimension": "Kabupaten/Kota", "bps_vervar_id": "1301",
                "bps_vervar_label": "Kepulauan Mentawai", "bps_turvar_id": "0", "bps_turvar_label": "Tidak ada",
                "bps_th_id": "125", "bps_th_label": "2025", "bps_turth_id": "0", "bps_turth_label": "Tahun",
                "value": "4.50", "source_key": "key1", "source_snapshot": "var-139-2025.json",
                "source_snapshot_sha256": "a" * 64, "canonical_geography_id": "idn.13.1301",
                "geography_mapping_status": "qualified_current_code",
            },
            {
                "panel_row_id": "internet:1301:320:595:125:0", "panel_series_id": "internet", "indicator_id": "internet_access",
                "canonical_promotion_status": "pending_indicator_universe_review", "source_id": "bps_webapi", "domain": "1300",
                "retrieved_at_utc": "2026-08-15T00:00:00+00:00", "bps_last_update": "2026-02-28 02:00:54",
                "bps_var_id": "320", "bps_var_label": "Internet", "bps_var_unit": "Persen", "bps_var_decimal": "2",
                "bps_var_definition": "", "bps_var_note": "Susenas", "bps_subject": "Komunikasi",
                "bps_vertical_dimension": "Kabupaten/Kota", "bps_vervar_id": "1301", "bps_vervar_label": "Kepulauan Mentawai",
                "bps_turvar_id": "595", "bps_turvar_label": "Pernah Mengakses Internet", "bps_th_id": "125",
                "bps_th_label": "2025", "bps_turth_id": "0", "bps_turth_label": "Tahun", "value": "70.00",
                "source_key": "key2", "source_snapshot": "var-320-2025.json", "source_snapshot_sha256": "b" * 64,
                "canonical_geography_id": "idn.13.1301", "geography_mapping_status": "qualified_current_code",
            },
        ]
        with source.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=source_fields)
            writer.writeheader()
            writer.writerows(rows)

        series = root / "series.csv"
        series.write_text(
            "panel_series_id,qualification_id,canonical_promotion_status\n"
            "tpt,q_tpt,canonical_ready\n"
            "internet,q_internet,pending_indicator_universe_review\n",
            encoding="utf-8",
        )
        qualifications = root / "qualifications.csv"
        qualifications.write_text(
            "qualification_id,decision,canonical_unit,reference_period_rule,source_universe,method_version,quality_flags_rule\n"
            "q_tpt,canonical_ready,percent,calendar_month_august,Population age 15+,Sakernas August,retain weighting notes\n"
            "q_internet,hold_source_native,percent,calendar_year_source_label,Persons age 5+,Susenas,retain universe\n",
            encoding="utf-8",
        )
        return source, series, qualifications

    def test_only_qualified_series_are_promoted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source, series, qualifications = self._write_fixture(Path(tmp))
            observations, provenance, manifest = build_canonical(source, series, qualifications)
            self.assertEqual(1, len(observations))
            self.assertEqual(1, len(provenance))
            self.assertEqual(1, manifest["canonical_series_count"])
            self.assertEqual(["internet"], manifest["held_series"])
            observation = observations[0]
            self.assertEqual("unemployment_rate", observation["indicator_id"])
            self.assertEqual("2025-08-01", observation["time_start"])
            self.assertEqual("2025-08-31", observation["time_end"])
            self.assertEqual("percent", observation["unit"])
            self.assertEqual("observed", observation["claim_type"])

    def test_grdp_release_status_and_price_basis_are_retained(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, series, qualifications = self._write_fixture(root)
            with source.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            row = rows[0]
            row.update(
                {
                    "panel_row_id": "real_grdp_growth_regency:1301:138:0:125:0",
                    "panel_series_id": "real_grdp_growth_regency",
                    "indicator_id": "real_grdp_growth",
                    "bps_var_id": "138",
                    "bps_var_label": "PDRB growth",
                    "bps_th_label": "2025",
                    "bps_th_id": "125",
                }
            )
            with source.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerow(row)
            series.write_text(
                "panel_series_id,qualification_id,canonical_promotion_status\n"
                "real_grdp_growth_regency,q_grdp,canonical_ready\n",
                encoding="utf-8",
            )
            qualifications.write_text(
                "qualification_id,decision,canonical_unit,reference_period_rule,source_universe,method_version,quality_flags_rule\n"
                "q_grdp,canonical_ready,percent,calendar_year,Regional economy,ADHK 2010,retain provisional status\n",
                encoding="utf-8",
            )
            observations, _, _ = build_canonical(source, series, qualifications)
            self.assertEqual("constant_2010", observations[0]["price_basis"])
            self.assertIn("release_status=very_very_provisional", observations[0]["notes"])


if __name__ == "__main__":
    unittest.main()
