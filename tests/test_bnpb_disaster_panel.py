from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_bnpb_disaster_panel import DISASTER_COLUMNS, build  # noqa: E402


GEOGRAPHIES = [
    ("idn.13.1301", "regency", "Kepulauan Mentawai", "1301", "KABUPATEN KEPULAUAN MENTAWAI", "13.01"),
    ("idn.13.1302", "regency", "Pesisir Selatan", "1302", "KABUPATEN PESISIR SELATAN", "13.02"),
    ("idn.13.1303", "regency", "Solok", "1303", "KABUPATEN SOLOK", "13.03"),
    ("idn.13.1304", "regency", "Sijunjung", "1304", "KABUPATEN SIJUNJUNG", "13.04"),
    ("idn.13.1305", "regency", "Tanah Datar", "1305", "KABUPATEN TANAH DATAR", "13.05"),
    ("idn.13.1306", "regency", "Padang Pariaman", "1306", "KABUPATEN PADANG PARIAMAN", "13.06"),
    ("idn.13.1307", "regency", "Agam", "1307", "KABUPATEN AGAM", "13.07"),
    ("idn.13.1308", "regency", "Lima Puluh Kota", "1308", "KABUPATEN LIMA PULUH KOTA", "13.08"),
    ("idn.13.1309", "regency", "Pasaman", "1309", "KABUPATEN PASAMAN", "13.09"),
    ("idn.13.1310", "regency", "Solok Selatan", "1310", "KABUPATEN SOLOK SELATAN", "13.10"),
    ("idn.13.1311", "regency", "Dharmasraya", "1311", "KABUPATEN DHARMASRAYA", "13.11"),
    ("idn.13.1312", "regency", "Pasaman Barat", "1312", "KABUPATEN PASAMAN BARAT", "13.12"),
    ("idn.13.1371", "city", "Padang", "1371", "KOTA PADANG", "13.71"),
    ("idn.13.1372", "city", "Solok", "1372", "KOTA SOLOK", "13.72"),
    ("idn.13.1373", "city", "Sawahlunto", "1373", "KOTA SAWAHLUNTO", "13.73"),
    ("idn.13.1374", "city", "Padang Panjang", "1374", "KOTA PADANG PANJANG", "13.74"),
    ("idn.13.1375", "city", "Bukittinggi", "1375", "KOTA BUKITTINGGI", "13.75"),
    ("idn.13.1376", "city", "Payakumbuh", "1376", "KOTA PAYAKUMBUH", "13.76"),
    ("idn.13.1377", "city", "Pariaman", "1377", "KOTA PARIAMAN", "13.77"),
]


def write_geographies(path: Path) -> None:
    fields = [
        "geography_id", "geography_level", "canonical_name", "bps_code", "parent_geography_id",
        "valid_from", "valid_to", "status", "source_id", "notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for geography_id, level, name, bps_code, _, _ in GEOGRAPHIES:
            writer.writerow(
                {
                    "geography_id": geography_id,
                    "geography_level": level,
                    "canonical_name": name,
                    "bps_code": bps_code,
                    "parent_geography_id": "idn.13",
                    "status": "current",
                }
            )


def source_records(kind: str) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for index, (_, _, _, _, source_name, source_code) in enumerate(GEOGRAPHIES, start=1):
        record: dict[str, object] = {
            "_id": index,
            "Kode Wilayah Kabupaten / Kota": source_code,
            "Nama Kabupaten/Kota": source_name,
            "Latitude": -1.0,
            "Longitude": 100.0,
        }
        if kind == "total":
            for year in range(2010, 2025):
                record[f"{year}.0"] = index + year - 2010
        else:
            for disaster_index, disaster_type in enumerate(DISASTER_COLUMNS, start=1):
                record[disaster_type] = index + disaster_index if kind == "events" else index * disaster_index
        result.append(record)
    return result


def write_snapshot(path: Path, records: list[dict[str, object]]) -> None:
    fields = [{"id": key, "type": "text"} for key in records[0]]
    payload = {
        "snapshot_schema": "ranah-observatory/bnpb-ckan-snapshot/v1",
        "source_id": "bnpb_satu_data",
        "retrieved_at_utc": "2026-08-15T00:00:00+00:00",
        "command": "datastore",
        "filters": {"resource_id": "fixture"},
        "result": {
            "resource_id": "fixture",
            "total": len(records),
            "returned": len(records),
            "fields": fields,
            "records": records,
        },
    }
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


class BNPBDisasterPanelTests(unittest.TestCase):
    def _fixture(self, directory: Path):
        geographies = directory / "geographies.csv"
        total = directory / "total.json"
        detailed = directory / "detailed.json"
        crosscheck = directory / "crosscheck.json"
        affected = directory / "affected.json"
        write_geographies(geographies)
        write_snapshot(total, source_records("total"))
        events = source_records("events")
        write_snapshot(detailed, events)
        write_snapshot(crosscheck, events)
        write_snapshot(affected, source_records("affected"))
        return geographies, total, detailed, crosscheck, affected

    def test_build_keeps_total_and_affected_outside_canonical_layer(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            geographies, total, detailed, crosscheck, affected = self._fixture(directory)
            source_native, canonical, provenance, manifest = build(
                total, detailed, crosscheck, affected, geographies_path=geographies
            )
            self.assertEqual(len(source_native), 627)
            self.assertEqual(len(canonical), 38)
            self.assertEqual(len(provenance), 1)
            self.assertEqual(manifest["official_crosscheck"], "passed")
            self.assertEqual(
                {row["indicator_id"] for row in canonical},
                {"flood_events", "landslide_events"},
            )
            affected_rows = [
                row for row in source_native if row["metric_family"] == "reported_affected_people_by_type"
            ]
            self.assertEqual(len(affected_rows), 171)
            self.assertTrue(all(row["promotion_status"] == "held_source_native" for row in affected_rows))
            total_rows = [
                row for row in source_native if row["metric_family"] == "recorded_disaster_events_total"
            ]
            self.assertEqual(len(total_rows), 285)
            self.assertTrue(all(row["promotion_status"] == "source_native_context" for row in total_rows))

    def test_official_crosscheck_disagreement_is_hard_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            geographies, total, detailed, crosscheck, affected = self._fixture(directory)
            payload = json.loads(crosscheck.read_text(encoding="utf-8"))
            payload["result"]["records"][0]["BANJIR"] += 1
            crosscheck.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "cross-check mismatch"):
                build(total, detailed, crosscheck, affected, geographies_path=geographies)

    def test_duplicate_solok_names_are_resolved_by_admin_type(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            geographies, total, detailed, crosscheck, affected = self._fixture(directory)
            _, canonical, _, _ = build(total, detailed, crosscheck, affected, geographies_path=geographies)
            regency_rows = [row for row in canonical if row["geography_id"] == "idn.13.1303"]
            city_rows = [row for row in canonical if row["geography_id"] == "idn.13.1372"]
            self.assertEqual(len(regency_rows), 2)
            self.assertEqual(len(city_rows), 2)
            self.assertTrue(all("13.03:KABUPATEN SOLOK" in row["notes"] for row in regency_rows))
            self.assertTrue(all("13.72:KOTA SOLOK" in row["notes"] for row in city_rows))


if __name__ == "__main__":
    unittest.main()
