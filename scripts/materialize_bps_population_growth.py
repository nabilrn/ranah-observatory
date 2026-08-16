#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from canonical_collision import existing_canonical_collisions
from validate_bps_population_growth_publication import read_csv, validate_source_contract

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data" / "registries" / "bps_population_growth_2010_2020_publication.csv"
DEFAULT_GEOGRAPHIES = ROOT / "data" / "registries" / "geographies.csv"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "processed" / "bps" / "demography"
SOURCE_ID = "bps_publication_web"
OFFICIAL_PUBLICATION_URL = (
    "https://sumbar.bps.go.id/id/publication/2021/02/26/"
    "438e46e73d9a64df8d8c34f2/provinsi-sumatera-barat-dalam-angka-2021.html"
)
SOURCE_RELEASE = "2021-02-26"
# PR #25 merged at this instant after qualifying the 19-row source contract.
QUALIFIED_AT = "2026-08-16T07:49:28Z"

OBS_FIELDS = [
    "observation_id", "indicator_id", "geography_id", "time_start", "time_end", "frequency",
    "value_numeric", "unit", "claim_type", "provenance_id", "suppressed", "comparable",
    "methodology_version", "price_basis", "notes",
]
PROV_FIELDS = [
    "provenance_id", "source_id", "artifact_locator", "retrieved_at", "source_release",
    "checksum_sha256", "parser_revision", "transform_revision", "extraction_method", "notes",
]


def _stable_id(prefix: str, *parts: str) -> str:
    token = "|".join(parts)
    return prefix + hashlib.sha256(token.encode("utf-8")).hexdigest()[:24]


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(source_path: Path, geography_path: Path, output_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    source_rows = read_csv(source_path)
    validation = validate_source_contract(source_rows, read_csv(geography_path))
    if validation["formula_match_count"] != 19:
        raise ValueError("source contract no longer reproduces all 19 published growth rates")

    source_checksum = hashlib.sha256(source_path.read_bytes()).hexdigest()
    provenance_id = _stable_id(
        "bpspopgrowthprov_", SOURCE_ID, validation["publication_id"], validation["table"], source_checksum
    )
    provenance = [{
        "provenance_id": provenance_id,
        "source_id": SOURCE_ID,
        "artifact_locator": OFFICIAL_PUBLICATION_URL,
        "retrieved_at": QUALIFIED_AT,
        "source_release": SOURCE_RELEASE,
        "checksum_sha256": source_checksum,
        "parser_revision": "bps_population_growth_publication_contract:v1",
        "transform_revision": "materialize_bps_population_growth:v1",
        "extraction_method": "manual_transcription",
        "notes": (
            "Authority is BPS Provinsi Sumatera Barat, Table 3.1.1. checksum_sha256 covers the committed "
            "19-row source-contract CSV, not the upstream PDF; every row is crosschecked against official "
            "SP2010/SP2020 counts and the BPS geometric formula before promotion."
        ),
    }]

    existing_ids, existing_keys = existing_canonical_collisions(
        ROOT / "data" / "processed", output_dir
    )
    observations: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_keys: set[tuple[str, str, str, str]] = set()
    for row in source_rows:
        geography_id = row["geography_id"]
        observation_id = _stable_id(
            "bpspopgrowthobs_", "population_growth", geography_id, "2010-05", "2020-09", validation["publication_id"]
        )
        semantic_key = ("population_growth", geography_id, "2010-05-01", "2020-09-30")
        if observation_id in seen_ids or semantic_key in seen_keys:
            raise ValueError(f"duplicate materialized population-growth row for {geography_id}")
        if observation_id in existing_ids or semantic_key in existing_keys:
            raise ValueError(f"population-growth collision with existing canonical data for {geography_id}")
        seen_ids.add(observation_id)
        seen_keys.add(semantic_key)
        observations.append({
            "observation_id": observation_id,
            "indicator_id": "population_growth",
            "geography_id": geography_id,
            "time_start": "2010-05-01",
            "time_end": "2020-09-30",
            "frequency": "annualized_interval",
            "value_numeric": float(row["growth_2010_2020_pct_per_year"]),
            "unit": "percent",
            "claim_type": "derived",
            "provenance_id": provenance_id,
            "suppressed": "false",
            "comparable": "true",
            "methodology_version": "bps_geometric_lpp_sp2010_may_to_sp2020_september_124_months",
            "price_basis": "",
            "notes": (
                f"Official BPS-published annual growth for May 2010 to September 2020; table=3.1.1; "
                f"source_population_2010={row['population_2010_may']}; "
                f"source_population_2020={row['population_2020_september']}; "
                "time bounds encode source months; interval length used by validation is exactly 124 months."
            ),
        })

    observations.sort(key=lambda row: row["geography_id"])
    manifest = {
        "schema": "ranah-observatory/bps-population-growth-canonical/v1",
        "source_id": SOURCE_ID,
        "indicator_id": "population_growth",
        "claim_type": "derived",
        "frequency": "annualized_interval",
        "time_start": "2010-05-01",
        "time_end": "2020-09-30",
        "interval_months": 124,
        "canonical_observation_count": len(observations),
        "canonical_provenance_count": len(provenance),
        "source_contract_sha256": source_checksum,
        "formula_match_count": validation["formula_match_count"],
        "canonical_promotion_performed": True,
    }
    return observations, provenance, manifest


def write_outputs(observations: list[dict[str, Any]], provenance: list[dict[str, Any]], manifest: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    obs_path = output_dir / "population-growth-2010-2020-observations.csv"
    prov_path = output_dir / "population-growth-2010-2020-provenance.csv"
    manifest_path = output_dir / "population-growth-2010-2020.manifest.json"
    obs_sha = _write_csv(obs_path, OBS_FIELDS, observations)
    prov_sha = _write_csv(prov_path, PROV_FIELDS, provenance)
    result = dict(manifest)
    result.update({
        "observations_file": obs_path.name,
        "observations_sha256": obs_sha,
        "provenance_file": prov_path.name,
        "provenance_sha256": prov_sha,
    })
    manifest_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def validate_output(output_dir: Path) -> dict[str, Any]:
    manifest_path = output_dir / "population-growth-2010-2020.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    obs_path = output_dir / manifest["observations_file"]
    prov_path = output_dir / manifest["provenance_file"]
    observations = read_csv(obs_path)
    provenance = read_csv(prov_path)
    if len(observations) != 19 or len(provenance) != 1:
        raise ValueError("population-growth canonical cardinality drifted")
    if hashlib.sha256(obs_path.read_bytes()).hexdigest() != manifest["observations_sha256"]:
        raise ValueError("population-growth observation checksum mismatch")
    if hashlib.sha256(prov_path.read_bytes()).hexdigest() != manifest["provenance_sha256"]:
        raise ValueError("population-growth provenance checksum mismatch")
    if {row["indicator_id"] for row in observations} != {"population_growth"}:
        raise ValueError("unexpected indicator in population-growth output")
    if {row["claim_type"] for row in observations} != {"derived"}:
        raise ValueError("population-growth claim type drifted")
    if {row["frequency"] for row in observations} != {"annualized_interval"}:
        raise ValueError("population-growth interval frequency drifted")
    if {row["time_start"] for row in observations} != {"2010-05-01"} or {row["time_end"] for row in observations} != {"2020-09-30"}:
        raise ValueError("population-growth time bounds drifted")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize qualified BPS 2010-2020 population-growth observations.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--geographies", type=Path, default=DEFAULT_GEOGRAPHIES)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    try:
        if args.validate_only:
            manifest = validate_output(args.output_dir)
        else:
            observations, provenance, manifest = build(args.source, args.geographies, args.output_dir)
            manifest = write_outputs(observations, provenance, manifest, args.output_dir)
            validate_output(args.output_dir)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
