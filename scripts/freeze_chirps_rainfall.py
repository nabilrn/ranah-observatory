from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from scripts.materialize_chirps_rainfall import PROVENANCE_FIELDS, read_csv

CANDIDATE_PREFIX = "artifact://chirps-annual-rainfall-canonical-candidate/chirps-source-contract.csv#year="
REPOSITORY_PREFIX = "repo://data/processed/climate/rainfall/chirps-source-contract.csv#year="


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rewrite_provenance(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if len(rows) != 45:
        raise ValueError(f"expected 45 candidate provenance rows; got {len(rows)}")
    rewritten: list[dict[str, str]] = []
    for row in rows:
        locator = row["artifact_locator"]
        if not locator.startswith(CANDIDATE_PREFIX):
            raise ValueError(f"candidate provenance locator is not artifact-scoped: {locator!r}")
        year = locator.removeprefix(CANDIDATE_PREFIX)
        if not (len(year) == 4 and year.isdigit() and 1981 <= int(year) <= 2025):
            raise ValueError(f"invalid provenance year fragment: {year!r}")
        updated = dict(row)
        updated["artifact_locator"] = REPOSITORY_PREFIX + year
        updated["notes"] = updated["notes"].replace(
            "checksum_scope=generated_source_contract_artifact_not_full_upstream_raster_bytes",
            "checksum_scope=committed_source_contract_artifact_not_full_upstream_raster_bytes",
        )
        if "committed_source_contract_artifact_not_full_upstream_raster_bytes" not in updated["notes"]:
            raise ValueError(f"provenance checksum scope was not rewritten for year {year}")
        rewritten.append(updated)
    rewritten.sort(key=lambda row: row["provenance_id"])
    if len({row["provenance_id"] for row in rewritten}) != 45:
        raise ValueError("duplicate provenance IDs during freeze")
    return rewritten


def freeze(candidate_dir: Path, output_dir: Path) -> dict[str, Any]:
    candidate_manifest_path = candidate_dir / "chirps-rainfall-materialization.manifest.json"
    observations_path = candidate_dir / "chirps-annual-rainfall-observations.csv"
    provenance_path = candidate_dir / "chirps-annual-rainfall-provenance.csv"
    source_contract_path = candidate_dir / "chirps-source-contract.csv"
    for path in (candidate_manifest_path, observations_path, provenance_path, source_contract_path):
        if not path.is_file():
            raise ValueError(f"missing candidate materialization file: {path}")

    candidate_manifest_bytes = candidate_manifest_path.read_bytes()
    candidate_manifest = json.loads(candidate_manifest_bytes.decode("utf-8"))
    if candidate_manifest.get("observation_count") != 855:
        raise ValueError("candidate manifest does not contain 855 observations")
    if candidate_manifest.get("provenance_count") != 45:
        raise ValueError("candidate manifest does not contain 45 provenance rows")
    if candidate_manifest.get("source_contract_item_count") != 541:
        raise ValueError("candidate manifest does not contain 541 source-contract items")
    if candidate_manifest.get("claim_type") != "model_estimate":
        raise ValueError("candidate claim type is not model_estimate")
    if candidate_manifest.get("spatial_frame") != "fixed_current_boundary_june_2026":
        raise ValueError("candidate spatial frame is not the qualified fixed current boundary")
    if candidate_manifest.get("independent_station_validation") != "pending":
        raise ValueError("station-validation status changed before freeze")
    if candidate_manifest.get("eligible_as_observed_station_data") is not False:
        raise ValueError("candidate incorrectly qualifies as observed station data")
    if candidate_manifest.get("historical_boundary_continuity_claimed") is not False:
        raise ValueError("candidate incorrectly claims historical boundary continuity")

    observations_bytes = observations_path.read_bytes()
    source_contract_bytes = source_contract_path.read_bytes()
    observations_sha = hashlib.sha256(observations_bytes).hexdigest()
    source_contract_sha = hashlib.sha256(source_contract_bytes).hexdigest()
    if candidate_manifest.get("observations_sha256") != observations_sha:
        raise ValueError("candidate observation checksum mismatch")
    if candidate_manifest.get("source_contract_sha256") != source_contract_sha:
        raise ValueError("candidate source-contract checksum mismatch")

    provenance_rows = read_csv(provenance_path)
    frozen_provenance = rewrite_provenance(provenance_rows)

    output_dir.mkdir(parents=True, exist_ok=True)
    frozen_observations_path = output_dir / "chirps-annual-rainfall-observations.csv"
    frozen_provenance_path = output_dir / "chirps-annual-rainfall-provenance.csv"
    frozen_contract_path = output_dir / "chirps-source-contract.csv"
    frozen_manifest_path = output_dir / "chirps-rainfall-materialization.manifest.json"

    frozen_observations_path.write_bytes(observations_bytes)
    frozen_contract_path.write_bytes(source_contract_bytes)
    frozen_provenance_sha = write_csv(frozen_provenance_path, PROVENANCE_FIELDS, frozen_provenance)

    frozen_manifest = dict(candidate_manifest)
    frozen_manifest.update({
        "freeze_status": "repository_baseline",
        "canonical_repository_path": "data/processed/climate/rainfall",
        "provenance_locator_scheme": REPOSITORY_PREFIX + "YYYY",
        "frozen_from_candidate_manifest_sha256": hashlib.sha256(candidate_manifest_bytes).hexdigest(),
        "candidate_provenance_sha256": candidate_manifest.get("provenance_sha256", ""),
        "provenance_sha256": frozen_provenance_sha,
        "observations_sha256": observations_sha,
        "source_contract_sha256": source_contract_sha,
    })
    frozen_manifest_path.write_text(
        json.dumps(frozen_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return frozen_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze CHIRPS canonical candidate into repository-baseline form")
    parser.add_argument("candidate_dir", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    manifest = freeze(args.candidate_dir, args.output_dir)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
