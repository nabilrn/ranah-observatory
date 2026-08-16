#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from scripts.validate_bps_population_growth_publication import (
    DEFAULT_GEOGRAPHIES,
    DEFAULT_SOURCE,
    EXPECTED_PUBLICATION_ID,
    EXPECTED_PUBLICATION_NUMBER,
    EXPECTED_TABLE,
    read_csv,
    validate_source_contract,
)

ROOT = Path(__file__).resolve().parents[1]
INDICATOR_ID = "population_growth"
SOURCE_ID = "bps_publication"
METHODOLOGY_VERSION = "bps_geometric_lpp_sp2010_may_sp2020_september_v1"
TIME_START = "2010-05-15"
TIME_END = "2020-09-30"
SOURCE_RELEASE = "2021-02-26"

OBSERVATION_FIELDS = [
    "observation_id", "indicator_id", "geography_id", "time_start", "time_end", "frequency",
    "value_numeric", "unit", "claim_type", "provenance_id", "suppressed", "comparable",
    "methodology_version", "price_basis", "notes",
]
PROVENANCE_FIELDS = [
    "provenance_id", "source_id", "artifact_locator", "retrieved_at", "source_release",
    "checksum_sha256", "parser_revision", "transform_revision", "extraction_method", "notes",
]


def stable_id(prefix: str, parts: Iterable[str]) -> str:
    token = "|".join(parts)
    return prefix + hashlib.sha256(token.encode("utf-8")).hexdigest()[:24]


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_canonical_candidate(
    source_rows: list[dict[str, str]],
    geography_rows: list[dict[str, str]],
    source_contract_sha256: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    validation = validate_source_contract(source_rows, geography_rows)
    if validation["canonical_promotion_performed"] is not False:
        raise ValueError("source-contract phase must not claim prior canonical promotion")
    if validation["formula_match_count"] != 19:
        raise ValueError("all 19 official BPS rates must pass formula cross-check before materialization")

    provenance_id = stable_id(
        "bpsgrowthprov_",
        [
            SOURCE_ID,
            EXPECTED_PUBLICATION_ID,
            EXPECTED_TABLE,
            source_contract_sha256,
            METHODOLOGY_VERSION,
        ],
    )
    provenance = [
        {
            "provenance_id": provenance_id,
            "source_id": SOURCE_ID,
            "artifact_locator": (
                "repo://data/registries/bps_population_growth_2010_2020_publication.csv"
                f"#publication_id={EXPECTED_PUBLICATION_ID};table={EXPECTED_TABLE}"
            ),
            "retrieved_at": "2026-08-16T00:00:00+00:00",
            "source_release": SOURCE_RELEASE,
            "checksum_sha256": source_contract_sha256,
            "parser_revision": "publication_table_transcription:v1",
            "transform_revision": "materialize_bps_population_growth:v1",
            "extraction_method": "manual_transcription",
            "notes": (
                f"official_agency=BPS Provinsi Sumatera Barat; publication_number={EXPECTED_PUBLICATION_NUMBER}; "
                f"publication_id={EXPECTED_PUBLICATION_ID}; table={EXPECTED_TABLE}; "
                "checksum_scope=qualified_repository_source_contract_not_official_pdf_bytes; "
                "transcription_carrier_not_source_authority=true; "
                "crosscheck=official_SP2010_counts+official_SP2020_counts+BPS_geometric_formula; "
                "interval=May_2010_to_September_2020_124_months"
            ),
        }
    ]

    observations: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for row in source_rows:
        gid = row["geography_id"]
        observation_id = stable_id(
            "bpsgrowthobs_",
            [INDICATOR_ID, gid, TIME_START, TIME_END, provenance_id, METHODOLOGY_VERSION],
        )
        if observation_id in seen_ids:
            raise ValueError(f"duplicate observation id for {gid}")
        seen_ids.add(observation_id)
        value = float(row["growth_2010_2020_pct_per_year"])
        observations.append(
            {
                "observation_id": observation_id,
                "indicator_id": INDICATOR_ID,
                "geography_id": gid,
                "time_start": TIME_START,
                "time_end": TIME_END,
                "frequency": "annual",
                "value_numeric": f"{value:.2f}",
                "unit": "percent",
                "claim_type": "derived",
                "provenance_id": provenance_id,
                "suppressed": "false",
                "comparable": "true",
                "methodology_version": METHODOLOGY_VERSION,
                "price_basis": "",
                "notes": (
                    "statistic=official_BPS_derived_population_growth_rate; "
                    "annualized_rate_over_intercensal_interval=true; "
                    "reference_start=SP2010_May_Hari_Sensus_2010-05-15; "
                    "reference_end=SP2020_September_result_window_end_2020-09-30; "
                    "interval_months=124; method=geometric; "
                    f"source_population_2010={row['population_2010_may']}; "
                    f"source_population_2020={row['population_2020_september']}; "
                    f"published_2000_2010_context_rate={row['growth_2000_2010_pct_per_year']}; "
                    "not_Ranah_model_estimate=true"
                ),
            }
        )

    observations.sort(key=lambda item: item["observation_id"])
    if len(observations) != 19:
        raise ValueError(f"expected 19 canonical candidate rows; got {len(observations)}")
    if {row["geography_id"] for row in observations} != {row["geography_id"] for row in source_rows}:
        raise ValueError("candidate geography footprint differs from qualified source contract")

    manifest = {
        "schema": "ranah-observatory/bps-population-growth-canonical-candidate/v1",
        "source_id": SOURCE_ID,
        "indicator_id": INDICATOR_ID,
        "claim_type": "derived",
        "methodology_version": METHODOLOGY_VERSION,
        "time_start": TIME_START,
        "time_end": TIME_END,
        "frequency": "annual",
        "unit": "percent",
        "observation_count": len(observations),
        "provenance_count": len(provenance),
        "geography_count": len({row["geography_id"] for row in observations}),
        "source_contract_sha256": source_contract_sha256,
        "source_publication_id": EXPECTED_PUBLICATION_ID,
        "source_publication_number": EXPECTED_PUBLICATION_NUMBER,
        "source_table": EXPECTED_TABLE,
        "canonical_freeze_performed": False,
        "source_contract_validation": validation,
    }
    return observations, provenance, manifest


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return file_sha256(path)


def write_outputs(
    observations: list[dict[str, Any]],
    provenance: list[dict[str, Any]],
    manifest: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    obs_path = output_dir / "bps-population-growth-observations.csv"
    prov_path = output_dir / "bps-population-growth-provenance.csv"
    manifest_path = output_dir / "bps-population-growth.manifest.json"
    obs_sha = write_csv(obs_path, OBSERVATION_FIELDS, observations)
    prov_sha = write_csv(prov_path, PROVENANCE_FIELDS, provenance)
    final_manifest = dict(manifest)
    final_manifest.update(
        {
            "observations_file": obs_path.name,
            "observations_sha256": obs_sha,
            "provenance_file": prov_path.name,
            "provenance_sha256": prov_sha,
        }
    )
    manifest_path.write_text(json.dumps(final_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return final_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize official BPS 2010-2020 population growth into canonical-format candidate rows")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--geographies", type=Path, default=DEFAULT_GEOGRAPHIES)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        source_rows = read_csv(args.source)
        geography_rows = read_csv(args.geographies)
        source_sha = file_sha256(args.source)
        observations, provenance, manifest = build_canonical_candidate(source_rows, geography_rows, source_sha)
        final_manifest = write_outputs(observations, provenance, manifest, args.output_dir)
    except (OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}")
        return 2
    print(json.dumps(final_manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
