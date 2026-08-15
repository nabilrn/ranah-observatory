from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from fingerprint_bnpb_disaster import fingerprint

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE = ROOT / "data" / "manifests" / "bnpb_disaster_baseline.json"


def compare(root: Path, baseline_path: Path = DEFAULT_BASELINE) -> list[str]:
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    digest, payload = fingerprint(root)
    errors: list[str] = []
    if digest != baseline.get("semantic_fingerprint_sha256"):
        errors.append(
            "BNPB disaster semantic fingerprint drift: "
            f"actual={digest} baseline={baseline.get('semantic_fingerprint_sha256')}"
        )
    expected = {
        "source_native_count": payload["source_native_count"],
        "canonical_observation_count": payload["canonical_observation_count"],
        "mapped_geography_count": payload["mapped_geography_count"],
    }
    for field, actual in expected.items():
        if baseline.get(field) != actual:
            errors.append(f"BNPB baseline {field}={baseline.get(field)!r}, actual={actual!r}")
    if sorted(baseline.get("canonical_indicators", [])) != payload["canonical_indicators"]:
        errors.append("BNPB canonical indicator membership drift")
    if payload["official_crosscheck"] != "passed":
        errors.append("BNPB official cross-check is not passed")
    if payload["geography_mapping"] != baseline.get("geography_mapping"):
        errors.append("BNPB geography mapping contract drift")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare fresh BNPB disaster panel with reviewed semantic baseline.")
    parser.add_argument("root", type=Path)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    args = parser.parse_args()
    try:
        errors = compare(args.root, args.baseline)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"BNPB disaster baseline comparison FAILED: {exc}", file=sys.stderr)
        return 1
    if errors:
        print("BNPB disaster baseline comparison FAILED", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("BNPB disaster semantic baseline reproduced exactly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
