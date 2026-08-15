from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "data" / "manifests" / "bnpb_disaster_baseline.json"

EXPECTED = {
    "source_native_count": 627,
    "canonical_observation_count": 38,
    "canonical_provenance_count": 1,
    "mapped_geography_count": 19,
}


def _hex(value: object, length: int) -> bool:
    if not isinstance(value, str) or len(value) != length:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def validate(path: Path = BASELINE) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    if payload.get("schema") != "ranah-observatory/bnpb-disaster-baseline/v1":
        errors.append("unexpected BNPB disaster baseline schema")
    if payload.get("source_id") != "bnpb_satu_data":
        errors.append("BNPB disaster baseline source_id must be bnpb_satu_data")
    for field, expected in EXPECTED.items():
        if payload.get(field) != expected:
            errors.append(f"baseline {field}={payload.get(field)!r}, expected {expected}")
    if payload.get("canonical_indicators") != ["flood_events", "landslide_events"]:
        errors.append("baseline canonical indicators changed unexpectedly")
    if payload.get("official_crosscheck") != "passed":
        errors.append("baseline official cross-check must be passed")
    if payload.get("geography_mapping") != "explicit_permendagri_current_crosswalk":
        errors.append("baseline geography mapping contract changed unexpectedly")
    for field in (
        "semantic_fingerprint_sha256",
        "reviewed_source_native_sha256",
        "reviewed_canonical_observations_sha256",
        "reviewed_canonical_provenance_sha256",
        "reviewed_manifest_sha256",
    ):
        if not _hex(payload.get(field), 64):
            errors.append(f"baseline {field} is not a valid SHA-256")
    acquisition = payload.get("acquisition")
    if not isinstance(acquisition, dict):
        errors.append("baseline acquisition provenance is required")
    else:
        if acquisition.get("workflow") != "Climate Disaster Foundation":
            errors.append("unexpected BNPB baseline acquisition workflow")
        for field in ("workflow_run_id", "artifact_id"):
            if not isinstance(acquisition.get(field), int) or acquisition.get(field, 0) <= 0:
                errors.append(f"baseline acquisition {field} must be a positive integer")
        if not _hex(acquisition.get("artifact_digest_sha256"), 64):
            errors.append("baseline acquisition artifact digest must be a valid SHA-256")
        if not _hex(acquisition.get("source_commit"), 40):
            errors.append("baseline acquisition source_commit must be a 40-character commit SHA")
        note = str(acquisition.get("review_note", ""))
        if "semantically wrong code-to-canonical mapping" not in note:
            errors.append("baseline review note must preserve the rejected pre-review mapping history")
    exclusions = set(payload.get("semantic_exclusions", []))
    required_exclusions = {
        "source_snapshot_sha256",
        "provenance_id",
        "provenance retrieval/checksum fields",
    }
    if not required_exclusions.issubset(exclusions):
        errors.append("baseline semantic exclusions do not document retrieval-only volatility")
    return errors


def main() -> int:
    try:
        errors = validate()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"BNPB disaster baseline validation FAILED: {exc}", file=sys.stderr)
        return 1
    if errors:
        print("BNPB disaster baseline validation FAILED", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("BNPB disaster baseline validation passed: 627 source-native, 38 canonical, 19 geographies.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
