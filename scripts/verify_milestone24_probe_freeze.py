#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROBE = ROOT / "data/manifests/milestone24_bps_stable32_probe.json"
DEFAULT_RAW = ROOT / "data/processed/bps/comparative_stable32/source"


class M24FreezeVerificationError(RuntimeError):
    pass


def semantic_digest(payload: Mapping[str, Any]) -> str:
    selected = {
        "var": payload.get("var"),
        "turvar": payload.get("turvar"),
        "labelvervar": payload.get("labelvervar"),
        "vervar": payload.get("vervar"),
        "tahun": payload.get("tahun"),
        "turtahun": payload.get("turtahun"),
        "metadata": payload.get("metadata"),
        "datacontent": payload.get("datacontent"),
        "last_update": payload.get("last_update"),
    }
    encoded = json.dumps(selected, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def verify(probe_path: Path, raw_root: Path) -> dict[str, Any]:
    probe = json.loads(probe_path.read_text(encoding="utf-8"))
    if probe.get("schema") != "ranah-observatory/milestone24-bps-stable32-probe/v1":
        raise M24FreezeVerificationError("unexpected M24 probe schema")
    candidates = probe.get("candidates")
    if not isinstance(candidates, list):
        raise M24FreezeVerificationError("M24 probe candidates must be a list")
    qualified = [
        item for item in candidates
        if isinstance(item, dict) and item.get("qualification_status") == "stable32_2018_2025_probe_qualified"
    ]
    if len(qualified) != probe.get("qualified_candidate_count"):
        raise M24FreezeVerificationError("qualified candidate count drift")

    checked: list[dict[str, Any]] = []
    for candidate in qualified:
        var_id = str(candidate["bps_var_id"])
        expected_by_year = candidate.get("semantic_sha256_by_year")
        if not isinstance(expected_by_year, dict):
            raise M24FreezeVerificationError(f"missing semantic digests for var={var_id}")
        for year in range(2018, 2026):
            snapshot_path = raw_root / f"var-{var_id}" / f"var-{var_id}-{year}.json"
            if not snapshot_path.exists():
                raise M24FreezeVerificationError(f"missing frozen snapshot {snapshot_path}")
            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
            result = snapshot.get("result")
            if not isinstance(result, Mapping):
                raise M24FreezeVerificationError(f"invalid frozen snapshot result {snapshot_path}")
            actual = semantic_digest(result)
            expected = str(expected_by_year.get(str(year), ""))
            if not expected:
                raise M24FreezeVerificationError(f"probe lacks semantic digest for var={var_id} year={year}")
            if actual != expected:
                raise M24FreezeVerificationError(
                    f"BPS semantic payload changed between probe and freeze for var={var_id} year={year}: {actual} != {expected}"
                )
            checked.append({"series_id": candidate["series_id"], "bps_var_id": int(var_id), "year": year, "semantic_sha256": actual})

    return {
        "schema": "ranah-observatory/milestone24-probe-freeze-verification/v1",
        "qualified_candidate_count": len(qualified),
        "verified_snapshot_count": len(checked),
        "semantic_probe_freeze_match": True,
        "verified": checked,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify frozen M24 BPS snapshots match the credentialed probe semantic digests.")
    parser.add_argument("--probe", type=Path, default=DEFAULT_PROBE)
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = verify(args.probe, args.raw_root)
    except (OSError, json.JSONDecodeError, M24FreezeVerificationError, KeyError, TypeError, ValueError) as exc:
        print(f"error: {exc}")
        return 2
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(json.dumps({
        "verified_snapshot_count": result["verified_snapshot_count"],
        "semantic_probe_freeze_match": result["semantic_probe_freeze_match"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
