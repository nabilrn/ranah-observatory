from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = ROOT / "data" / "acquisition_requests" / "bps_publications.csv"
DEFAULT_INBOX = ROOT / "data" / "raw" / "inbox"
DEFAULT_MANIFEST = ROOT / "data" / "manifests" / "historical_artifacts.csv"
MANIFEST_FIELDS = [
    "request_id",
    "source_record_id",
    "title",
    "artifact_filename",
    "sha256",
    "bytes",
    "official_page_url",
    "anchor_year",
    "priority",
    "exit_gate_candidate",
    "verification_state",
    "acquired_at_utc",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def validate_pdf(path: Path) -> None:
    if not path.is_file():
        raise ValueError(f"not a file: {path}")
    size = path.stat().st_size
    if size < 16:
        raise ValueError(f"file is too small to be a PDF: {path}")
    with path.open("rb") as handle:
        if not handle.read(8).startswith(b"%PDF-"):
            raise ValueError(f"not a PDF by file signature: {path}")
        handle.seek(max(size - 8192, 0))
        if b"%%EOF" not in handle.read():
            raise ValueError(f"PDF EOF marker not found near end of file: {path}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def existing_manifest(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    return {row["request_id"]: row for row in read_csv(path) if row.get("request_id")}


def inspect_batch(
    queue_path: Path,
    inbox_dir: Path,
    manifest_path: Path,
) -> tuple[list[dict[str, str]], list[str], list[str]]:
    queue = read_csv(queue_path)
    previous = existing_manifest(manifest_path)
    verified: list[dict[str, str]] = []
    missing: list[str] = []
    errors: list[str] = []

    expected_names = {row["output_filename"].strip() for row in queue}
    unknown = sorted(
        path.name for path in inbox_dir.glob("*.pdf") if path.name not in expected_names
    ) if inbox_dir.exists() else []
    for name in unknown:
        errors.append(f"unmatched PDF in inbox: {name}")

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    for row in queue:
        request_id = row["request_id"].strip()
        path = inbox_dir / row["output_filename"].strip()
        if not path.exists():
            missing.append(request_id)
            continue
        try:
            validate_pdf(path)
            digest = sha256_file(path)
        except (OSError, ValueError) as exc:
            errors.append(f"{request_id}: {exc}")
            continue

        old = previous.get(request_id, {})
        acquired_at = old.get("acquired_at_utc", "") if old.get("sha256") == digest else now
        verified.append(
            {
                "request_id": request_id,
                "source_record_id": row.get("source_record_id", "").strip(),
                "title": row["title"].strip(),
                "artifact_filename": path.name,
                "sha256": digest,
                "bytes": str(path.stat().st_size),
                "official_page_url": row["official_page_url"].strip(),
                "anchor_year": row["anchor_year"].strip(),
                "priority": row["priority"].strip(),
                "exit_gate_candidate": row["exit_gate_candidate"].strip().lower(),
                "verification_state": "artifact_verified",
                "acquired_at_utc": acquired_at,
            }
        )
    return verified, missing, errors


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda row: (row["anchor_year"], row["request_id"])))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate historical PDFs in the local inbox and write a small reproducible artifact manifest."
    )
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--inbox-dir", type=Path, default=DEFAULT_INBOX)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument(
        "--require-exit-gate",
        action="store_true",
        help="Fail unless at least one verified exit-gate candidate artifact is present.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        verified, missing, errors = inspect_batch(args.queue, args.inbox_dir, args.manifest)
    except (OSError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    for row in verified:
        print(
            f"VERIFIED {row['request_id']}: {row['artifact_filename']} "
            f"sha256={row['sha256']}"
        )
    for request_id in missing:
        print(f"MISSING  {request_id}")
    for error in errors:
        print(f"ERROR    {error}", file=sys.stderr)

    if not args.check_only and not errors:
        write_manifest(args.manifest, verified)
        print(f"Manifest written: {args.manifest}")

    gate_verified = any(row["exit_gate_candidate"] == "yes" for row in verified)
    print(
        f"Batch summary: verified={len(verified)} missing={len(missing)} "
        f"errors={len(errors)} exit_gate_verified={str(gate_verified).lower()}"
    )
    if errors:
        return 1
    if args.require_exit_gate and not gate_verified:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
