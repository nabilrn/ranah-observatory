import csv
import gzip
import hashlib
import io
import json
import re
import unittest
from collections import Counter
from pathlib import Path


MANIFEST_PATH = Path("data/manifests/milestone42_bnpb_historical_source_native_staging.json")
STAGING_PATH = Path("data/processed/bnpb_historical_source_native_rows_2000_2017.csv.gz")

METRICS = [
    "jumlah_kejadian",
    "meninggal",
    "hilang",
    "terluka",
    "menderita",
    "mengungsi",
    "rumah_rusak_berat",
    "rumah_rusak_sedang",
    "rumah_rusak_ringan",
    "rumah_terendam",
    "fasilitas_pendidikan",
    "fasilitas_kesehatan",
    "fasilitas_peribadatan",
    "fasilitas_umum",
]


def parse_raw_count(value: str) -> int:
    normalized = value.strip().replace(",", "")
    if not re.fullmatch(r"\d+", normalized):
        raise ValueError(f"not a source-native non-negative integer: {value!r}")
    return int(normalized)


class Milestone42HistoricalStagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        cls.compressed = STAGING_PATH.read_bytes()
        cls.uncompressed = gzip.decompress(cls.compressed)
        cls.rows = list(
            csv.DictReader(io.StringIO(cls.uncompressed.decode("utf-8")))
        )

    def test_artifact_digests_and_shape_match_manifest(self):
        artifact = self.manifest["staging_artifact"]
        self.assertEqual(artifact["compressed_bytes"], len(self.compressed))
        self.assertEqual(artifact["uncompressed_bytes"], len(self.uncompressed))
        self.assertEqual(
            artifact["compressed_sha256"], hashlib.sha256(self.compressed).hexdigest()
        )
        self.assertEqual(
            artifact["uncompressed_sha256"], hashlib.sha256(self.uncompressed).hexdigest()
        )
        self.assertEqual(202, len(self.rows))
        self.assertEqual(artifact["rows"], len(self.rows))

    def test_2001_remains_empty_and_no_absent_rows_are_synthesized(self):
        years = Counter(int(row["source_year"]) for row in self.rows)
        self.assertNotIn(2001, years)

        workbook = {item["year"]: item for item in self.manifest["workbooks"]}
        self.assertEqual("empty_body", workbook[2001]["state"])
        self.assertEqual(0, workbook[2001]["rows"])
        self.assertFalse(workbook[2001]["total"])
        self.assertIsNone(workbook[2001]["reconcile14"])

        for year in range(2000, 2018):
            if year == 2001:
                continue
            self.assertEqual(workbook[year]["rows"], years[year])

        self.assertFalse(
            self.manifest["geography_execution"]["absent_geography_rows_synthesized"]
        )

    def test_every_metric_cell_preserves_raw_parsed_and_state_semantics(self):
        zero_count = 0
        positive_count = 0
        for row in self.rows:
            for metric in METRICS:
                raw = row[f"{metric}_raw"]
                value = row[f"{metric}_value"]
                state = row[f"{metric}_state"]

                self.assertNotEqual("", raw)
                parsed = parse_raw_count(raw)
                self.assertEqual(parsed, int(value))

                expected_state = "observed_zero" if parsed == 0 else "observed_positive"
                self.assertEqual(expected_state, state)
                if parsed == 0:
                    zero_count += 1
                else:
                    positive_count += 1

        self.assertEqual(2828, zero_count + positive_count)
        self.assertEqual(
            sum(item["zero_cells"] for item in self.manifest["workbooks"]),
            zero_count,
        )
        self.assertEqual(
            sum(item["positive_cells"] for item in self.manifest["workbooks"]),
            positive_count,
        )

    def test_all_non_empty_workbooks_reconcile_and_have_no_bad_metric_cells(self):
        for item in self.manifest["workbooks"]:
            self.assertEqual(0, item["blank_cells"])
            self.assertEqual(0, item["nonnumeric_cells"])
            if item["year"] == 2001:
                continue
            self.assertTrue(item["total"])
            self.assertTrue(item["reconcile14"])
            self.assertEqual(item["rows"] * 14, item["cells"])

    def test_historical_codes_are_source_identity_not_current_bnpb_join_keys(self):
        profile = self.manifest["historical_source_code_profile"]
        self.assertEqual(19, len(profile))
        self.assertEqual(19, len({item["code"] for item in profile}))
        self.assertEqual(19, len({item["name"] for item in profile}))

        expected_by_name = {
            item["name"]: item["canonical_entity_id"] for item in profile
        }
        for row in self.rows:
            self.assertEqual(
                expected_by_name[row["source_name_raw"]],
                row["canonical_entity_id_by_name_lineage"],
            )

        geo = self.manifest["geography_execution"]
        self.assertFalse(geo["raw_code_only_join_used"])
        self.assertTrue(geo["name_plus_legal_lineage_mapping_used"])
        self.assertFalse(geo["current_boundary_comparability_promoted"])

    def test_source_identity_is_unique_per_year_and_row(self):
        keys = [
            (int(row["source_year"]), int(row["source_row_number"]))
            for row in self.rows
        ]
        self.assertEqual(len(keys), len(set(keys)))

        labels = [
            (int(row["source_year"]), row["source_label_raw"])
            for row in self.rows
        ]
        self.assertEqual(len(labels), len(set(labels)))
        self.assertNotIn("Jumlah", {row["source_label_raw"] for row in self.rows})

    def test_known_boundary_transition_rows_are_flagged(self):
        lookup = {
            (int(row["source_year"]), row["source_name_raw"]): row
            for row in self.rows
        }
        self.assertEqual(
            "transition_year_parent_solok_selatan_split",
            lookup[(2003, "SOLOK")]["geography_lineage_status"],
        )
        self.assertEqual(
            "transition_year_parent_dharmasraya_split",
            lookup[(2003, "SIJUNJUNG")]["geography_lineage_status"],
        )
        self.assertEqual(
            "pre_solok_selatan_split_parent",
            lookup[(2002, "SOLOK")]["geography_lineage_status"],
        )
        self.assertEqual(
            "pre_dharmasraya_split_parent",
            lookup[(2000, "SIJUNJUNG")]["geography_lineage_status"],
        )

        for row in self.rows:
            self.assertEqual("not_proven", row["current_boundary_comparability"])

    def test_pre_2008_sijunjung_source_labels_keep_retrospective_warning(self):
        rows = [
            row
            for row in self.rows
            if row["source_name_raw"] == "SIJUNJUNG" and int(row["source_year"]) < 2008
        ]
        self.assertGreater(len(rows), 0)
        for row in rows:
            self.assertEqual(
                "retrospective_or_source_normalized_name_before_legal_rename",
                row["source_label_timing_status"],
            )

    def test_m42_stops_at_source_native_staging(self):
        q = self.manifest["qualification"]
        self.assertTrue(q["all_workbooks_audited"])
        self.assertTrue(q["single_structural_schema_observed"])
        self.assertTrue(q["source_native_staging_materialized"])
        self.assertFalse(q["canonical_historical_panel_authorized"])
        self.assertFalse(q["event_level_panel_authorized"])

        boundaries = " ".join(self.manifest["boundaries"]).lower()
        self.assertIn("no zero filling", boundaries)
        self.assertIn("no current-boundary comparability claim", boundaries)
        self.assertIn("no event reconstruction", boundaries)
        self.assertIn("no canonical historical metric promotion", boundaries)


if __name__ == "__main__":
    unittest.main()
