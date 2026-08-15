from __future__ import annotations

import csv
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_bps_source_panel import build_panel  # noqa: E402


class BPSPanelBuilderTests(unittest.TestCase):
    def _fixture(self, root: Path, *, selected_turvar: str = "0", geography_id: str = "1301") -> Path:
        registry = root / "registry.csv"
        registry.write_text(
            "panel_series_id,indicator_id,bps_var_id,subject_id,source_title,target_start_year,target_end_year,selected_turvar_id,selected_turvar_label,subperiod_policy,qualification_status,canonical_promotion_status,comparability_notes\n"
            f"series_a,unemployment_rate,139,6,Source title,2024,2025,{selected_turvar},Tidak ada,preserve_all,source_metadata_qualified,pending_reference_period_review,test\n",
            encoding="utf-8",
        )
        directory = root / "series-var139"
        directory.mkdir()
        fields = [
            "source_id", "domain", "retrieved_at_utc", "bps_var_id", "bps_var_label", "bps_var_unit",
            "bps_var_decimal", "bps_var_definition", "bps_var_note", "bps_subject", "bps_vertical_dimension",
            "bps_vervar_id", "bps_vervar_label", "bps_turvar_id", "bps_turvar_label", "bps_th_id",
            "bps_th_label", "bps_turth_id", "bps_turth_label", "value", "source_key",
        ]
        label = "Kab. Kepulauan Mentawai" if geography_id == "1301" else "Provinsi Sumatera Barat"
        with (directory / "var-139-long.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for year, th in (("2024", "124"), ("2025", "125")):
                writer.writerow(
                    {
                        "source_id": "bps_webapi", "domain": "1300", "retrieved_at_utc": "2026-01-01T00:00:00+00:00",
                        "bps_var_id": "139", "bps_var_label": "Source title", "bps_var_unit": "Persen",
                        "bps_var_decimal": "2", "bps_var_definition": "", "bps_var_note": "note", "bps_subject": "Tenaga Kerja",
                        "bps_vertical_dimension": "Kabupaten/Kota", "bps_vervar_id": geography_id, "bps_vervar_label": label,
                        "bps_turvar_id": "0", "bps_turvar_label": "Tidak ada", "bps_th_id": th, "bps_th_label": year,
                        "bps_turth_id": "0", "bps_turth_label": "Tahun", "value": "4.5", "source_key": f"{geography_id}13901{th}0",
                    }
                )
        snapshots = []
        for year in ("2024", "2025"):
            snapshot = directory / f"var-139-{year}.json"
            snapshot.write_text(json.dumps({"period": year}) + "\n", encoding="utf-8")
            digest = hashlib.sha256(snapshot.read_bytes()).hexdigest()
            checksum = directory / f"var-139-{year}.json.sha256"
            checksum.write_text(f"{digest}  {snapshot.name}\n", encoding="utf-8")
            snapshots.append(
                {
                    "period_label": year,
                    "period_id": "124" if year == "2024" else "125",
                    "snapshot": snapshot.name,
                    "checksum": checksum.name,
                    "observed_values": 1,
                    "missing_combinations": 0,
                }
            )
        (directory / "var-139-manifest.json").write_text(
            json.dumps({"var_id": 139, "snapshots": snapshots}) + "\n", encoding="utf-8"
        )
        return registry

    def test_builder_links_each_row_to_snapshot_checksum_and_current_geography(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = self._fixture(root)
            rows, manifest = build_panel(root, registry)
            self.assertEqual(2, len(rows))
            self.assertEqual(2, manifest["row_count"])
            self.assertTrue(all(len(row["source_snapshot_sha256"]) == 64 for row in rows))
            self.assertTrue(all(row["canonical_geography_id"] == "idn.13.1301" for row in rows))
            self.assertTrue(all(row["geography_mapping_status"] == "qualified_current_code" for row in rows))

    def test_builder_maps_1378_only_as_explicit_province_alias(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = self._fixture(root, geography_id="1378")
            rows, _ = build_panel(root, registry)
            self.assertTrue(all(row["canonical_geography_id"] == "idn.13" for row in rows))
            self.assertTrue(
                all(row["geography_mapping_status"] == "qualified_source_aggregate_alias" for row in rows)
            )

    def test_builder_rejects_selector_that_produces_no_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = self._fixture(root, selected_turvar="999")
            with self.assertRaisesRegex(ValueError, "produced no rows"):
                build_panel(root, registry)

    def test_builder_rejects_missing_target_year(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = self._fixture(root)
            path = root / "series-var139" / "var-139-long.csv"
            with path.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerow(rows[0])
            with self.assertRaisesRegex(ValueError, "missing target period"):
                build_panel(root, registry)


if __name__ == "__main__":
    unittest.main()
