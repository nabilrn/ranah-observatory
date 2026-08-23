from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

try:
    from scripts import build_milestone36_station_overlap as overlap
except ModuleNotFoundError:
    import build_milestone36_station_overlap as overlap

FIRST_STAGE0_SUCCESS_RUN = 32645859174
FIRST_STAGE0_ARTIFACT_DIGEST = "sha256:b2cd66500cd8d4826270435708a5f2fcd7a413a16e323b840c8881a2dd7ad002"
FIRST_STAGE1_SUCCESS_RUN = 32646150222
FIRST_STAGE1_ARTIFACT_DIGEST = "sha256:742086c441be9ce3d4f36cf79b945aa57a8995d5e0d4472a0e0b98d99cffb38d"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_stage0() -> dict[str, object]:
    return {
        "schema": "ranah-observatory/milestone36-stage0-qualification/v1",
        "target": {
            "traditional_station_identifier": "96163",
            "historical_identity": "BMKG PADANG/TABING",
            "historical_bmkg_coordinate": [100.35, -(53.0 / 60.0)],
            "target_years": [1997, 1998],
        },
        "locked_candidate_order": [
            "ncei_daily_summaries_ghcn_IDM00096163",
            "ncei_gsod_96163099999",
        ],
        "candidate_results": [
            {
                "candidate": "ncei_daily_summaries_ghcn_IDM00096163",
                "identity_qualified": False,
                "target_period_coverage_qualified": False,
                "accepted": False,
                "reason": "locked Daily Summaries/GHCN probe did not expose qualifying 1997-1998 coverage",
            },
            {
                "candidate": "ncei_gsod_96163099999",
                "identity_qualified": True,
                "target_period_coverage_qualified": True,
                "accepted": True,
                "ncei_name": "TABING, ID",
                "ncei_coordinate": [100.351881, -0.874989],
                "reason": "exact locked GSOD identifier plus tight coordinate guard qualifies historical Tabing for both target years",
            },
        ],
        "accepted_stage1_representation": "ncei_gsod_96163099999",
        "station_history_guard": {
            "historical_bmkg_identity": "PADANG/TABING",
            "current_identity_from_prior_repository_probe": "PADANG PARIAMAN/MINANGKABAU",
            "prior_repository_pr": 20,
            "live_current_bmkg_recheck_from_hosted_runner": "http_403_transport_blocked",
            "safe_to_merge_96163_across_station_history": False,
        },
        "precipitation_values_inspected_during_stage0": False,
        "stage1_numeric_inspection_authorized": True,
        "first_successful_stage0_workflow_run_id": FIRST_STAGE0_SUCCESS_RUN,
        "first_successful_stage0_artifact_digest": FIRST_STAGE0_ARTIFACT_DIGEST,
        "first_successful_stage1_workflow_run_id": FIRST_STAGE1_SUCCESS_RUN,
        "first_successful_stage1_artifact_digest": FIRST_STAGE1_ARTIFACT_DIGEST,
        "boundaries": {
            "safe_to_relabel_chirps_as_observed": False,
            "safe_to_mark_global_chirps_station_validation_complete": False,
            "causal_claim_authorized": False,
        },
    }


def finalize(candidate_dir: Path, output_dir: Path) -> dict[str, object]:
    candidate_source = candidate_dir / "source"
    if not candidate_source.is_dir():
        raise ValueError(f"missing candidate source directory: {candidate_source}")

    output_source = output_dir / "source"
    output_source.mkdir(parents=True, exist_ok=True)
    for year in overlap.TARGET_YEARS:
        filename = f"ncei_gsod_{overlap.STATION_ID}_{year}.csv"
        source = candidate_source / filename
        if not source.is_file():
            raise ValueError(f"missing source snapshot: {source}")
        shutil.copyfile(source, output_source / filename)

    result = overlap.build(output_dir, source_dir=output_source)
    stage0 = canonical_stage0()
    (output_dir / "stage0-qualification.json").write_text(
        json.dumps(stage0, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    expected_classification = "station_overlap_directionally_supportive"
    if result["comparison"]["classification"] != expected_classification:
        raise ValueError(
            "candidate result changed after the first preregistered Stage 1 run: "
            f"{result['comparison']['classification']}"
        )

    required = [
        "annual-summary.csv",
        "station-overlap.json",
        "stage0-qualification.json",
        f"source/ncei_gsod_{overlap.STATION_ID}_1997.csv",
        f"source/ncei_gsod_{overlap.STATION_ID}_1998.csv",
    ]
    files = {
        rel: {
            "sha256": sha256_file(output_dir / rel),
            "bytes": (output_dir / rel).stat().st_size,
        }
        for rel in required
    }
    manifest = {
        "schema": "ranah-observatory/milestone36-station-evidence-manifest/v1",
        "milestone": 36,
        "evidence_scope": "independent_historical_station_directional_overlap",
        "canonical_station_representation": "ncei_gsod_96163099999",
        "target_years": [1997, 1998],
        "classification": result["comparison"]["classification"],
        "offline_rebuild_supported": True,
        "raw_source_files_frozen": True,
        "source_is_third_party_observation_summary": True,
        "chirps_baseline_modified": False,
        "publication_package_modified": False,
        "causal_claim_authorized": False,
        "files": files,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Finalize deterministic M36 station evidence")
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest = finalize(args.candidate_dir, args.output_dir)
    print(json.dumps({
        "classification": manifest["classification"],
        "files": len(manifest["files"]),
        "offline_rebuild_supported": manifest["offline_rebuild_supported"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
