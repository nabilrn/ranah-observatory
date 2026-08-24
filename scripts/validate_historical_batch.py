from __future__ import annotations

import csv
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "data" / "acquisition_requests" / "bps_publications.csv"
MANIFEST = ROOT / "data" / "manifests" / "historical_artifacts.csv"
SOURCES = ROOT / "data" / "registries" / "historical_source_inventory.csv"
CATALOG = ROOT / "catalog" / "data-catalog.csv"

ALLOWED_PRIORITY = {"P0", "P1", "P2"}
ALLOWED_GATE = {"yes", "no"}
ALLOWED_COMMITTED_PDFS = frozenset(
    {
        "publication/v0.1/distribution/Ranah_Observatory_v0.1_Preprint_Nabil_Rizki_Navisa.pdf",
    }
)
SAFE_FILENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.pdf$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_P0 = {
    "sp1961_indonesia",
    "sp1971_sumbar_e3",
    "sumbar_1970",
    "sumbar_1980",
    "sumbar_1990",
    "sumbar_2000",
    "sumbar_2010",
    "sumbar_2020",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def official_bps_url(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and (host == "bps.go.id" or host.endswith(".bps.go.id"))


def find_disallowed_committed_pdfs(root: Path = ROOT) -> list[str]:
    disallowed: list[str] = []
    for path in root.rglob("*.pdf"):
        if ".git" in path.parts:
            continue
        relative_path = path.relative_to(root).as_posix()
        if relative_path.startswith("data/raw/"):
            continue
        if relative_path in ALLOWED_COMMITTED_PDFS:
            continue
        disallowed.append(relative_path)
    return sorted(disallowed)


def validate() -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    queue = read_csv(QUEUE)
    manifest = read_csv(MANIFEST)
    sources = read_csv(SOURCES)
    catalog = read_csv(CATALOG)

    source_refs = {row["source_record_id"].strip() for row in sources}
    source_refs |= {row["source_id"].strip() for row in catalog}

    request_ids = [row["request_id"].strip() for row in queue]
    filenames = [row["output_filename"].strip() for row in queue]
    if len(request_ids) != len(set(request_ids)):
        errors.append("historical acquisition queue contains duplicate request_id values")
    if len(filenames) != len(set(filenames)):
        errors.append("historical acquisition queue contains duplicate output filenames")

    queue_by_id = {row["request_id"].strip(): row for row in queue}
    missing_p0 = sorted(REQUIRED_P0 - queue_by_id.keys())
    if missing_p0:
        errors.append("historical acquisition queue is missing anchor requests: " + ", ".join(missing_p0))

    for row_number, row in enumerate(queue, start=2):
        request_id = row["request_id"].strip()
        if not request_id:
            errors.append(f"queue row {row_number}: request_id is required")
        if not row["title"].strip():
            errors.append(f"queue row {row_number}: title is required")
        source_ref = row["source_record_id"].strip()
        if source_ref not in source_refs:
            errors.append(f"queue row {row_number}: unknown source_record_id/source_id={source_ref!r}")
        if not official_bps_url(row["official_page_url"].strip()):
            errors.append(f"queue row {row_number}: official_page_url must be on an official BPS host")
        if not SAFE_FILENAME.match(row["output_filename"].strip()):
            errors.append(f"queue row {row_number}: unsafe output_filename")
        priority = row["priority"].strip()
        if priority not in ALLOWED_PRIORITY:
            errors.append(f"queue row {row_number}: invalid priority={priority!r}")
        gate = row["exit_gate_candidate"].strip().lower()
        if gate not in ALLOWED_GATE:
            errors.append(f"queue row {row_number}: invalid exit_gate_candidate={gate!r}")
        try:
            year = int(row["anchor_year"].strip())
            if year < 1945 or year > 2100:
                errors.append(f"queue row {row_number}: anchor_year outside supported range")
        except ValueError:
            errors.append(f"queue row {row_number}: anchor_year must be an integer")
        if not row["purpose"].strip():
            errors.append(f"queue row {row_number}: purpose is required")

    for request_id in REQUIRED_P0:
        row = queue_by_id.get(request_id)
        if row and row["priority"].strip() != "P0":
            errors.append(f"anchor request {request_id} must remain P0")

    if not any(row["exit_gate_candidate"].strip().lower() == "yes" for row in queue):
        errors.append("queue must contain at least one exit-gate candidate")

    manifest_ids = [row["request_id"].strip() for row in manifest]
    if len(manifest_ids) != len(set(manifest_ids)):
        errors.append("historical artifact manifest contains duplicate request_id values")

    for row_number, row in enumerate(manifest, start=2):
        request_id = row["request_id"].strip()
        queue_row = queue_by_id.get(request_id)
        if queue_row is None:
            errors.append(f"manifest row {row_number}: unknown request_id={request_id!r}")
            continue
        if row["source_record_id"].strip() != queue_row["source_record_id"].strip():
            errors.append(f"manifest row {row_number}: source_record_id differs from queue")
        if row["artifact_filename"].strip() != queue_row["output_filename"].strip():
            errors.append(f"manifest row {row_number}: artifact filename differs from queue")
        if not SHA256.match(row["sha256"].strip()):
            errors.append(f"manifest row {row_number}: invalid SHA-256")
        try:
            if int(row["bytes"].strip()) <= 0:
                errors.append(f"manifest row {row_number}: bytes must be positive")
        except ValueError:
            errors.append(f"manifest row {row_number}: bytes must be an integer")
        for field in ("official_page_url", "anchor_year", "priority", "exit_gate_candidate"):
            if row[field].strip() != queue_row[field].strip():
                errors.append(f"manifest row {row_number}: {field} differs from queue")
        if row["verification_state"].strip() != "artifact_verified":
            errors.append(f"manifest row {row_number}: verification_state must be artifact_verified")
        try:
            datetime.fromisoformat(row["acquired_at_utc"].strip())
        except ValueError:
            errors.append(f"manifest row {row_number}: acquired_at_utc must be ISO-8601")

    disallowed_pdfs = find_disallowed_committed_pdfs()
    if disallowed_pdfs:
        errors.append(
            "PDF artifacts outside the explicit committed allowlist must not be committed to Git: "
            + ", ".join(disallowed_pdfs)
        )

    counts = {
        "queue": len(queue),
        "p0": sum(row["priority"].strip() == "P0" for row in queue),
        "manifest": len(manifest),
        "exit_gate_verified": sum(
            row["exit_gate_candidate"].strip().lower() == "yes" for row in manifest
        ),
    }
    return errors, counts


def main() -> int:
    errors, counts = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(
        "Historical acquisition batch valid: "
        f"{counts['queue']} queued; {counts['p0']} P0 anchors; "
        f"{counts['manifest']} verified artifacts; "
        f"{counts['exit_gate_verified']} verified exit-gate artifacts"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
