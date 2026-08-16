from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from scripts.validate_chirps_rainfall_freeze import validate as validate_frozen_baseline

ROOT = Path(__file__).resolve().parents[1]
BASELINE_DIR = ROOT / "data" / "processed" / "climate" / "rainfall"
SOURCE_CONTRACT = BASELINE_DIR / "chirps-source-contract.csv"
USER_AGENT = "ranah-observatory/0.1 (+https://github.com/nabilrn/ranah-observatory)"
PREFIX_BYTES = 16384
CONTENT_RANGE_RE = re.compile(r"^bytes 0-16383/([1-9][0-9]*)$")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def select_chirps_rows(rows: list[dict[str, str]], mode: str) -> list[dict[str, str]]:
    chirps = [row for row in rows if row["source_id"] == "chirps_v3"]
    if len(chirps) != 540:
        raise ValueError(f"frozen source contract must contain exactly 540 CHIRPS rows; got {len(chirps)}")
    if mode == "full":
        return sorted(chirps, key=lambda row: (int(row["year"]), int(row["month"])))
    if mode != "annual-anchors":
        raise ValueError(f"unsupported drift mode: {mode}")

    anchors = [row for row in chirps if int(row["month"]) == 1]
    endpoint = [row for row in chirps if int(row["year"]) == 2025 and int(row["month"]) == 12]
    selected = anchors + endpoint
    selected.sort(key=lambda row: (int(row["year"]), int(row["month"])))
    if len(selected) != 46:
        raise ValueError(f"annual-anchor mode must select 46 CHIRPS rows; got {len(selected)}")
    return selected


def fetch_prefix(url: str, timeout: float = 45.0) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/octet-stream,*/*",
            "Range": f"bytes=0-{PREFIX_BYTES - 1}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(PREFIX_BYTES)
            return {
                "reachable": True,
                "http_status": int(getattr(response, "status", 200)),
                "bytes_read": len(body),
                "content_range": response.headers.get("Content-Range", ""),
                "content_length": response.headers.get("Content-Length", ""),
                "etag": response.headers.get("ETag", ""),
                "last_modified": response.headers.get("Last-Modified", ""),
                "prefix_sha256": hashlib.sha256(body).hexdigest(),
                "is_tiff": body.startswith(b"II*\x00") or body.startswith(b"MM\x00*"),
            }
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        return {
            "reachable": False,
            "http_status": exc.code if isinstance(exc, urllib.error.HTTPError) else None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def fetch_full(url: str, timeout: float = 90.0) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/geo+json,application/json,*/*"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            return {
                "reachable": True,
                "http_status": int(getattr(response, "status", 200)),
                "bytes": len(body),
                "etag": response.headers.get("ETag", ""),
                "last_modified": response.headers.get("Last-Modified", ""),
                "sha256": hashlib.sha256(body).hexdigest(),
            }
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        return {
            "reachable": False,
            "http_status": exc.code if isinstance(exc, urllib.error.HTTPError) else None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def compare_chirps_identity(row: Mapping[str, str], current: Mapping[str, Any]) -> dict[str, Any]:
    period = f"{int(row['year']):04d}-{int(row['month']):02d}"
    result: dict[str, Any] = {
        "contract_item_id": row["contract_item_id"],
        "period": period,
        "locator": row["locator"],
        "status": "stable",
        "differences": [],
        "current": dict(current),
    }
    differences: list[dict[str, Any]] = result["differences"]

    if not current.get("reachable"):
        result["status"] = "transport_error"
        differences.append({"field": "reachable", "expected": True, "actual": False})
        return result
    if current.get("http_status") != 206:
        differences.append({"field": "http_status", "expected": 206, "actual": current.get("http_status")})
    if current.get("bytes_read") != PREFIX_BYTES:
        differences.append({"field": "bytes_read", "expected": PREFIX_BYTES, "actual": current.get("bytes_read")})
    if current.get("is_tiff") is not True:
        differences.append({"field": "is_tiff", "expected": True, "actual": current.get("is_tiff")})

    content_range = str(current.get("content_range", ""))
    match = CONTENT_RANGE_RE.fullmatch(content_range)
    current_length = match.group(1) if match else ""
    expected_pairs = {
        "content_length_bytes": (row["content_length_bytes"], current_length),
        "etag": (row["transport_identity"], str(current.get("etag", ""))),
        "source_release": (row["source_release"], str(current.get("last_modified", ""))),
        "identity_sha256": (row["identity_sha256"], str(current.get("prefix_sha256", ""))),
    }
    for field, (expected, actual) in expected_pairs.items():
        if expected != actual:
            differences.append({"field": field, "expected": expected, "actual": actual})

    if differences:
        result["status"] = "drift"
    return result


def compare_big_identity(row: Mapping[str, str], current: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "contract_item_id": row["contract_item_id"],
        "locator": row["locator"],
        "status": "stable",
        "differences": [],
        "current": dict(current),
    }
    differences: list[dict[str, Any]] = result["differences"]
    if not current.get("reachable"):
        result["status"] = "transport_error"
        differences.append({"field": "reachable", "expected": True, "actual": False})
        return result
    if current.get("http_status") != 200:
        differences.append({"field": "http_status", "expected": 200, "actual": current.get("http_status")})
    if str(current.get("bytes", "")) != row["content_length_bytes"]:
        differences.append({
            "field": "content_length_bytes",
            "expected": row["content_length_bytes"],
            "actual": str(current.get("bytes", "")),
        })
    if str(current.get("sha256", "")) != row["identity_sha256"]:
        differences.append({
            "field": "identity_sha256",
            "expected": row["identity_sha256"],
            "actual": str(current.get("sha256", "")),
        })
    if differences:
        result["status"] = "drift"
    return result


def run(mode: str) -> dict[str, Any]:
    baseline_validation = validate_frozen_baseline(BASELINE_DIR)
    contract = read_csv(SOURCE_CONTRACT)
    selected = select_chirps_rows(contract, mode)
    big_rows = [row for row in contract if row["source_id"] == "big_admin_boundaries_june_2026"]
    if len(big_rows) != 1:
        raise ValueError(f"expected exactly one frozen BIG identity; got {len(big_rows)}")

    chirps_results = [
        compare_chirps_identity(row, fetch_prefix(row["locator"]))
        for row in selected
    ]
    big_result = compare_big_identity(big_rows[0], fetch_full(big_rows[0]["locator"]))
    all_results = chirps_results + [big_result]
    drift = [row for row in all_results if row["status"] == "drift"]
    transport_errors = [row for row in all_results if row["status"] == "transport_error"]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "drift_probe_version": 1,
        "mode": mode,
        "baseline_validation": baseline_validation,
        "scope": {
            "chirps_contract_total": 540,
            "chirps_items_checked": len(chirps_results),
            "big_items_checked": 1,
            "full_contract_covered": mode == "full",
        },
        "chirps_results": chirps_results,
        "big_result": big_result,
        "summary": {
            "stable_items": sum(row["status"] == "stable" for row in all_results),
            "drift_items": len(drift),
            "transport_error_items": len(transport_errors),
            "baseline_drift_detected": bool(drift),
            "transport_failure_detected": bool(transport_errors),
            "safe_to_silently_replace_baseline": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check frozen CHIRPS/BIG source identities for upstream drift")
    parser.add_argument("--mode", choices=("annual-anchors", "full"), default="annual-anchors")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = run(args.mode)
    rendered = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    summary = payload["summary"]
    return 1 if summary["baseline_drift_detected"] or summary["transport_failure_detected"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
