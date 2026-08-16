from __future__ import annotations

import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.freeze_chirps_rainfall import reuse_existing_baseline_if_identical


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> str:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create_existing_baseline(directory: Path) -> dict[str, str]:
    observations = directory / "chirps-annual-rainfall-observations.csv"
    provenance = directory / "chirps-annual-rainfall-provenance.csv"
    contract = directory / "chirps-source-contract.csv"
    manifest = directory / "chirps-rainfall-materialization.manifest.json"

    obs_sha = write_csv(observations, ["id", "value"], [{"id": "obs1", "value": "10"}])
    prov_sha = write_csv(provenance, ["id", "retrieved_at"], [{"id": "prov1", "retrieved_at": "frozen"}])
    contract_sha = write_csv(contract, ["id", "etag"], [{"id": "src1", "etag": "stable"}])
    payload = {
        "freeze_status": "repository_baseline",
        "observations_sha256": obs_sha,
        "provenance_sha256": prov_sha,
        "source_contract_sha256": contract_sha,
        "retrieved_at": "frozen-original-timestamp",
    }
    manifest.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return payload


class ChirpsRainfallFreezeTests(unittest.TestCase):
    def test_identical_candidate_reuses_existing_baseline_without_rewriting_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            existing = create_existing_baseline(root)
            before = {
                path.name: path.read_bytes()
                for path in root.iterdir()
                if path.is_file()
            }
            result = reuse_existing_baseline_if_identical(
                root,
                candidate_observations_sha=existing["observations_sha256"],
                candidate_source_contract_sha=existing["source_contract_sha256"],
            )
            after = {
                path.name: path.read_bytes()
                for path in root.iterdir()
                if path.is_file()
            }
            self.assertIsNotNone(result)
            self.assertEqual(result["freeze_action"], "reused_identical_repository_baseline")
            self.assertEqual(result["retrieved_at"], "frozen-original-timestamp")
            self.assertEqual(before, after)

    def test_changed_observation_or_source_contract_refuses_automatic_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            existing = create_existing_baseline(root)
            with self.assertRaises(ValueError):
                reuse_existing_baseline_if_identical(
                    root,
                    candidate_observations_sha="0" * 64,
                    candidate_source_contract_sha=existing["source_contract_sha256"],
                )
            with self.assertRaises(ValueError):
                reuse_existing_baseline_if_identical(
                    root,
                    candidate_observations_sha=existing["observations_sha256"],
                    candidate_source_contract_sha="f" * 64,
                )

    def test_partial_existing_baseline_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "chirps-annual-rainfall-observations.csv").write_text("id\nobs1\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                reuse_existing_baseline_if_identical(
                    root,
                    candidate_observations_sha="0" * 64,
                    candidate_source_contract_sha="1" * 64,
                )

    def test_corrupted_existing_file_fails_even_if_manifest_claims_candidate_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            existing = create_existing_baseline(root)
            (root / "chirps-annual-rainfall-provenance.csv").write_text("corrupted\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                reuse_existing_baseline_if_identical(
                    root,
                    candidate_observations_sha=existing["observations_sha256"],
                    candidate_source_contract_sha=existing["source_contract_sha256"],
                )

    def test_absent_existing_baseline_returns_none_for_initial_freeze(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertIsNone(
                reuse_existing_baseline_if_identical(
                    root,
                    candidate_observations_sha="0" * 64,
                    candidate_source_contract_sha="1" * 64,
                )
            )


if __name__ == "__main__":
    unittest.main()
