from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from merge_chirps_rainfall_chunks import (  # noqa: E402
    DIAGNOSTICS,
    GEOMETRY,
    MANIFEST,
    OBSERVATIONS,
    PROVENANCE,
    SOURCE_ARTIFACTS,
    merge_chunks,
)


GEOGRAPHIES = [f"g{i:02d}" for i in range(19)]


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def make_chunk(root: Path, name: str, start: int, end: int, geometry: bytes = b"same-geometry") -> Path:
    chunk = root / name
    chunk.mkdir(parents=True)
    (chunk / GEOMETRY).write_bytes(geometry)

    observations: list[dict[str, object]] = []
    diagnostics: list[dict[str, object]] = []
    sources: list[dict[str, object]] = []
    for year in range(start, end + 1):
        source_url = f"https://data.chc.ucsb.edu/products/CHIRPS/v3.0/annual/global/tifs/chirps-v3.0.{year}.tif"
        source_sha = f"{year:064d}"[-64:]
        sources.append(
            {
                "year": year,
                "source_url": source_url,
                "retrieved_at": "2026-08-16T00:00:00+00:00",
                "bytes": 22000000,
                "sha256": source_sha,
            }
        )
        for index, geography in enumerate(GEOGRAPHIES):
            value = 2000.0 + index + (year - 1981)
            observations.append(
                {
                    "observation_id": f"obs-{geography}-{year}",
                    "indicator_id": "annual_rainfall",
                    "geography_id": geography,
                    "time_start": f"{year}-01-01",
                    "time_end": f"{year}-12-31",
                    "frequency": "annual",
                    "value_numeric": value,
                    "unit": "millimetres",
                    "claim_type": "model_estimate",
                    "provenance_id": f"prov-{name}",
                    "suppressed": "false",
                    "comparable": "true",
                    "methodology_version": "chirps-v3-final-annual_fractional-area-v1",
                    "price_basis": "",
                    "notes": "fixture",
                }
            )
            diagnostics.append(
                {
                    "geography_id": geography,
                    "canonical_name": geography,
                    "source_permendagri_code": f"13{index:02d}",
                    "year": year,
                    "annual_rainfall_mm": value,
                    "valid_area_fraction": 0.999,
                    "valid_weight_area_m2": 99.9,
                    "polygon_weight_area_m2": 100.0,
                    "valid_pixel_intersections": 10,
                    "total_pixel_intersections": 10,
                    "source_url": source_url,
                    "source_sha256": source_sha,
                    "source_bytes": 22000000,
                }
            )

    write_csv(chunk / OBSERVATIONS, observations)
    write_csv(chunk / DIAGNOSTICS, diagnostics)
    write_csv(chunk / SOURCE_ARTIFACTS, sources)
    write_csv(
        chunk / PROVENANCE,
        [
            {
                "provenance_id": f"prov-{name}",
                "source_id": "chirps_v3",
                "artifact_locator": "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/annual/global/tifs/chirps-v3.0.YYYY.tif",
                "retrieved_at": "2026-08-16T00:00:00+00:00",
                "source_release": "CHIRPS v3 Final annual",
                "checksum_sha256": "fixture",
                "parser_revision": "build_chirps_rainfall_panel.py",
                "transform_revision": "chirps-v3-final-annual_fractional-area-v1",
                "extraction_method": "derived",
                "notes": "fixture",
            }
        ],
    )
    geometry_sha = __import__("hashlib").sha256(geometry).hexdigest()
    manifest = {
        "panel_version": 2,
        "indicator_id": "annual_rainfall",
        "claim_type": "model_estimate",
        "unit": "millimetres",
        "years": {"start": start, "end": end, "count": end - start + 1},
        "geography": {
            "count": 19,
            "spatial_frame": "current_boundary_reconstruction",
            "source": "Badan Informasi Geospasial",
            "source_edition": "Juni 2026",
            "mapping": "fixture",
            "raw_geojson_sha256": geometry_sha,
        },
        "chirps": {
            "source": "CHIRPS v3 Final annual",
            "annual_tif_base": "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/annual/global/tifs",
            "annual_raster_count": end - start + 1,
            "grid": {"crs": "EPSG:4326", "width": 7200, "height": 2400, "transform": [1, 0, 0, 0, -1, 0], "resolution": [0.05, 0.05]},
            "nodata_rule": "fixture",
            "transport": {"mode": "sequential_full_download", "download_attempts": 5, "polite_inter_request_delay_seconds": 2.0, "source_level_sha256": True},
        },
        "method": {
            "revision": "chirps-v3-final-annual_fractional-area-v1",
            "weight_crs": "EPSG:6933",
            "pixel_weighting": "fractional polygon-pixel intersection area",
            "annual_statistic": "area-weighted spatial mean of official CHIRPS annual precipitation raster",
            "minimum_required_valid_area_fraction": 0.98,
        },
        "cross_granularity_validation": {
            "reference": "data/validation/chirps/chirps-v3-2025-annual-monthly-equivalence.csv",
            "year": 2025,
            "annual_tif_sha256": "e24f177b53c05eae36bf636b7ed42223948dce37350115ac157211f118b1e70c",
            "max_absolute_difference_mm": 0.000460631,
            "max_relative_difference_percent": 0.000013209810,
            "interpretation": "fixture",
        },
        "negative_guards": {
            "is_direct_station_observation": False,
            "uses_historical_boundary_geometry": False,
            "safe_to_interpret_big_june_2026_as_historical_boundary": False,
            "safe_to_equate_big_kdpkab_with_bps_code": False,
        },
    }
    (chunk / MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")
    return chunk


class CHIRPSChunkMergeTests(unittest.TestCase):
    def test_merge_rewrites_provenance_and_covers_all_years_once(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            chunks = root / "chunks"
            make_chunk(chunks, "a", 1981, 1981)
            make_chunk(chunks, "b", 1982, 1982)
            output = root / "full"
            manifest = merge_chunks(chunks, output, 1981, 1982)

            self.assertEqual(manifest["years"]["count"], 2)
            self.assertEqual(manifest["quality"]["observation_count"], 38)
            self.assertEqual(manifest["quality"]["source_artifact_count"], 2)
            self.assertEqual(manifest["chunk_merge"]["chunk_count"], 2)

            observations = list(csv.DictReader((output / OBSERVATIONS).open(encoding="utf-8")))
            provenance = list(csv.DictReader((output / PROVENANCE).open(encoding="utf-8")))
            self.assertEqual(len(observations), 38)
            self.assertEqual(len(provenance), 1)
            self.assertEqual({row["provenance_id"] for row in observations}, {provenance[0]["provenance_id"]})

    def test_merge_rejects_overlapping_ranges(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            chunks = root / "chunks"
            make_chunk(chunks, "a", 1981, 1982)
            make_chunk(chunks, "b", 1982, 1983)
            with self.assertRaisesRegex(ValueError, "overlap"):
                merge_chunks(chunks, root / "full", 1981, 1983)

    def test_merge_rejects_geometry_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            chunks = root / "chunks"
            make_chunk(chunks, "a", 1981, 1981, geometry=b"geometry-a")
            make_chunk(chunks, "b", 1982, 1982, geometry=b"geometry-b")
            with self.assertRaisesRegex(ValueError, "BIG raw GeoJSON SHA-256"):
                merge_chunks(chunks, root / "full", 1981, 1982)


if __name__ == "__main__":
    unittest.main()
