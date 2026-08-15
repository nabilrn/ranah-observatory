from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
import sys
import time
import webbrowser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = ROOT / "data" / "acquisition_requests" / "bps_publications.csv"
DEFAULT_INBOX = ROOT / "data" / "raw" / "inbox"
ALLOWED_PRIORITY = {"P0", "P1", "P2"}


def read_queue(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {
        "request_id",
        "title",
        "official_page_url",
        "output_filename",
        "priority",
        "anchor_year",
        "exit_gate_candidate",
        "purpose",
    }
    missing = required - set(rows[0].keys() if rows else [])
    if missing:
        raise ValueError("queue is missing columns: " + ", ".join(sorted(missing)))
    return rows


def official_bps_url(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and (host == "bps.go.id" or host.endswith(".bps.go.id"))


def validate_pdf(path: Path) -> None:
    if not path.is_file():
        raise ValueError(f"not a file: {path}")
    with path.open("rb") as handle:
        head = handle.read(8)
        if not head.startswith(b"%PDF-"):
            raise ValueError(f"not a PDF by file signature: {path}")
        try:
            handle.seek(max(path.stat().st_size - 8192, 0))
        except OSError:
            handle.seek(0)
        tail = handle.read()
    if b"%%EOF" not in tail:
        raise ValueError(f"PDF EOF marker not found near end of file: {path}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_pdfs(directory: Path) -> dict[Path, tuple[int, int]]:
    if not directory.exists():
        return {}
    result: dict[Path, tuple[int, int]] = {}
    for path in directory.glob("*.pdf"):
        try:
            stat = path.stat()
        except OSError:
            continue
        result[path.resolve()] = (stat.st_mtime_ns, stat.st_size)
    return result


def newest_changed_pdf(
    directory: Path,
    before: dict[Path, tuple[int, int]],
    *,
    started_at: float,
) -> list[Path]:
    candidates: list[Path] = []
    for path in directory.glob("*.pdf"):
        try:
            resolved = path.resolve()
            stat = path.stat()
        except OSError:
            continue
        previous = before.get(resolved)
        changed = previous != (stat.st_mtime_ns, stat.st_size)
        recent = stat.st_mtime >= started_at - 5
        if changed and recent:
            candidates.append(path)
    candidates.sort(key=lambda item: item.stat().st_mtime_ns, reverse=True)
    return candidates


def filtered_queue(rows: list[dict[str, str]], priorities: set[str]) -> list[dict[str, str]]:
    return [row for row in rows if row["priority"].strip() in priorities]


def print_queue(rows: list[dict[str, str]]) -> None:
    for index, row in enumerate(rows, start=1):
        gate = " gate" if row["exit_gate_candidate"].strip().lower() == "yes" else ""
        print(
            f"{index:02d}. [{row['priority']}] {row['anchor_year']} "
            f"{row['request_id']}{gate}\n    {row['title']}"
        )


def collect(
    rows: list[dict[str, str]],
    *,
    downloads_dir: Path,
    inbox_dir: Path,
    replace: bool = False,
) -> tuple[int, int, int]:
    inbox_dir.mkdir(parents=True, exist_ok=True)
    acquired = 0
    skipped = 0
    failed = 0

    for index, row in enumerate(rows, start=1):
        request_id = row["request_id"].strip()
        title = row["title"].strip()
        page_url = row["official_page_url"].strip()
        output = inbox_dir / row["output_filename"].strip()

        if not official_bps_url(page_url):
            print(f"ERROR {request_id}: refusing non-BPS URL {page_url}", file=sys.stderr)
            failed += 1
            continue

        if output.exists() and not replace:
            try:
                validate_pdf(output)
                print(f"SKIP [{index}/{len(rows)}] {request_id}: already in inbox")
                skipped += 1
                continue
            except ValueError as exc:
                print(f"WARN {request_id}: existing inbox file is invalid: {exc}")

        print("\n" + "=" * 72)
        print(f"[{index}/{len(rows)}] {title}")
        print(f"Target: {output.name}")
        print(page_url)
        before = snapshot_pdfs(downloads_dir)
        started_at = time.time()
        opened = webbrowser.open(page_url, new=2)
        if not opened:
            print("Browser could not be opened automatically; open the URL above manually.")

        answer = input(
            "Download the original PDF in the browser, then press Enter. "
            "Type s to skip or q to stop: "
        ).strip().lower()
        if answer == "q":
            break
        if answer == "s":
            skipped += 1
            continue

        candidates = newest_changed_pdf(downloads_dir, before, started_at=started_at)
        if not candidates:
            manual = input(
                "No new PDF detected in Downloads. Paste the PDF path, or press Enter to skip: "
            ).strip().strip('"')
            if not manual:
                failed += 1
                continue
            candidates = [Path(manual).expanduser()]

        candidate = candidates[0]
        if len(candidates) > 1:
            print("Multiple new PDFs detected; using the newest:")
            for item in candidates[:5]:
                print(f"  - {item}")
            print(f"Selected: {candidate}")

        try:
            validate_pdf(candidate)
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(candidate, output)
            validate_pdf(output)
            digest = sha256_file(output)
        except (OSError, ValueError) as exc:
            print(f"ERROR {request_id}: {exc}", file=sys.stderr)
            failed += 1
            continue

        print(f"OK   {request_id}: {output.name}")
        print(f"     sha256={digest}")
        acquired += 1

    return acquired, skipped, failed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Open official BPS source pages and collect browser-downloaded PDFs into a local inbox."
    )
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--downloads-dir", type=Path, default=Path.home() / "Downloads")
    parser.add_argument("--inbox-dir", type=Path, default=DEFAULT_INBOX)
    parser.add_argument(
        "--priority",
        action="append",
        choices=sorted(ALLOWED_PRIORITY),
        help="Priority to collect; repeat for multiple priorities. Defaults to P0 only.",
    )
    parser.add_argument("--open", action="store_true", help="Run the interactive browser collection loop.")
    parser.add_argument("--replace", action="store_true", help="Replace an existing inbox artifact.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    priorities = set(args.priority or ["P0"])
    try:
        rows = read_queue(args.queue)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    rows = filtered_queue(rows, priorities)
    print_queue(rows)
    if not args.open:
        print(f"\n{len(rows)} item(s). Add --open to start interactive browser collection.")
        return 0
    acquired, skipped, failed = collect(
        rows,
        downloads_dir=args.downloads_dir.expanduser(),
        inbox_dir=args.inbox_dir,
        replace=args.replace,
    )
    print(f"\nBatch result: acquired={acquired} skipped={skipped} failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
