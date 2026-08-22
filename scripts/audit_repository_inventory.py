#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data"


def tracked_files() -> list[Path]:
    out = subprocess.check_output(["git", "ls-files", "data"], cwd=ROOT, text=True)
    return [ROOT / line for line in out.splitlines() if line.strip()]


def csv_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            next(reader)
        except StopIteration:
            return 0
        return sum(1 for _ in reader)


def main() -> int:
    files = tracked_files()
    by_bucket: Counter[str] = Counter()
    by_ext: Counter[str] = Counter()
    bytes_by_bucket: Counter[str] = Counter()
    csv_rows_by_bucket: Counter[str] = Counter()
    csv_files_by_bucket: Counter[str] = Counter()
    largest: list[tuple[int, str]] = []

    for path in files:
        rel = path.relative_to(ROOT)
        parts = rel.parts
        bucket = parts[1] if len(parts) > 1 else "root"
        by_bucket[bucket] += 1
        size = path.stat().st_size
        bytes_by_bucket[bucket] += size
        ext = path.suffix.lower() or "<no_ext>"
        by_ext[ext] += 1
        largest.append((size, rel.as_posix()))
        if ext == ".csv":
            rows = csv_rows(path)
            csv_rows_by_bucket[bucket] += rows
            csv_files_by_bucket[bucket] += 1

    evidence_like_exts = {".html", ".json", ".csv", ".geojson", ".tif", ".tiff", ".zip", ".txt", ".xml"}
    evidence_like_files = sum(1 for p in files if p.suffix.lower() in evidence_like_exts)

    payload = {
        "tracked_data_files": len(files),
        "tracked_data_bytes": sum(p.stat().st_size for p in files),
        "tracked_data_megabytes_decimal": round(sum(p.stat().st_size for p in files) / 1_000_000, 3),
        "files_by_data_bucket": dict(sorted(by_bucket.items())),
        "bytes_by_data_bucket": dict(sorted(bytes_by_bucket.items())),
        "files_by_extension": dict(sorted(by_ext.items())),
        "manifest_files": by_bucket.get("manifests", 0),
        "processed_evidence_files": by_bucket.get("processed", 0),
        "analysis_files": by_bucket.get("analysis", 0),
        "registry_files": by_bucket.get("registries", 0),
        "snapshot_files": by_bucket.get("snapshots", 0),
        "acquisition_request_files": by_bucket.get("acquisition_requests", 0),
        "evidence_like_files_by_extension_rule": evidence_like_files,
        "csv_files_total": sum(csv_files_by_bucket.values()),
        "csv_physical_rows_total_excluding_headers": sum(csv_rows_by_bucket.values()),
        "csv_files_by_bucket": dict(sorted(csv_files_by_bucket.items())),
        "csv_physical_rows_by_bucket": dict(sorted(csv_rows_by_bucket.items())),
        "largest_tracked_data_files": [
            {"path": path, "bytes": size}
            for size, path in sorted(largest, reverse=True)[:15]
        ],
        "interpretation_note": "CSV physical row totals count rows across all tracked CSV artifacts and can double-count the same scientific evidence when derivative, audit, or rebuilt panels exist. They are a repository-volume measure, not a unique-observation count.",
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
