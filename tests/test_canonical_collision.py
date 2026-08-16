from __future__ import annotations

import csv
import os
import tempfile
import unittest
from pathlib import Path

from scripts.canonical_collision import existing_canonical_collisions


FIELDS = ["observation_id", "indicator_id", "geography_id", "time_start", "time_end"]


def write_observation(path: Path, observation_id: str, indicator_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerow(
            {
                "observation_id": observation_id,
                "indicator_id": indicator_id,
                "geography_id": "idn.13.1301",
                "time_start": "2025-01-01",
                "time_end": "2025-12-31",
            }
        )


class CanonicalCollisionTests(unittest.TestCase):
    def test_relative_output_dir_is_excluded_from_collision_scan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            processed = root / "data" / "processed"
            output = processed / "bps" / "target"
            external = processed / "bps" / "other"
            write_observation(output / "target.csv", "self-id", "self_indicator")
            write_observation(external / "other.csv", "external-id", "external_indicator")

            previous = Path.cwd()
            try:
                os.chdir(root)
                ids, keys = existing_canonical_collisions(
                    Path("data/processed"), Path("data/processed/bps/target")
                )
            finally:
                os.chdir(previous)

            self.assertNotIn("self-id", ids)
            self.assertIn("external-id", ids)
            self.assertNotIn(
                ("self_indicator", "idn.13.1301", "2025-01-01", "2025-12-31"),
                keys,
            )
            self.assertIn(
                ("external_indicator", "idn.13.1301", "2025-01-01", "2025-12-31"),
                keys,
            )


if __name__ == "__main__":
    unittest.main()
