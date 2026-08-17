#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Mapping

from bps_client import BPSApiError, BPSClient

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "manifests" / "milestone7_bps_subject_catalog.json"
DOMAIN = "0000"

SUBJECT_TERMS = (
    "pendidikan",
    "pembangunan manusia",
    "kesehatan",
    "kependudukan",
    "penduduk",
    "demografi",
    "telekomunikasi",
    "teknologi informasi",
    "komunikasi",
    "transportasi",
    "jalan",
    "energi",
    "listrik",
    "produk domestik regional bruto",
    "pdrb",
    "lapangan usaha",
    "neraca regional",
    "kesejahteraan rakyat",
)


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()


def first_text(row: Mapping[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def first_int(row: Mapping[str, Any], keys: tuple[str, ...]) -> int | None:
    for key in keys:
        value = row.get(key)
        if value in (None, ""):
            continue
        try:
            return int(str(value).strip())
        except ValueError:
            continue
    return None


def subject_id(row: Mapping[str, Any]) -> int | None:
    return first_int(row, ("sub_id", "subject_id", "subj", "id", "val"))


def subject_label(row: Mapping[str, Any]) -> str:
    preferred = first_text(row, ("title", "label", "sub", "subject", "name"))
    if preferred:
        return preferred
    return " ".join(
        str(v) for v in row.values()
        if isinstance(v, (str, int, float)) and str(v).strip()
    )


def relevant(label: str) -> bool:
    text = normalize(label)
    return any(normalize(term) in text for term in SUBJECT_TERMS)


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze national BPS subject metadata for Milestone 7.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    api_key = os.environ.get("BPS_API_KEY", "").strip()
    if not api_key:
        print("error: BPS_API_KEY is required", file=sys.stderr)
        return 2
    client = BPSClient(api_key, retries=3, retry_backoff_seconds=1.0)
    try:
        rows = client.list_subjects(domain=DOMAIN)
    except BPSApiError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    subjects = [
        {
            "subject_id": subject_id(row),
            "subject_label": subject_label(row),
            "relevant_to_m7": relevant(subject_label(row)),
            "metadata": dict(row),
        }
        for row in rows
    ]
    report = {
        "schema": "ranah-observatory/milestone7-bps-subject-catalog/v1",
        "domain": DOMAIN,
        "source_authority": "Badan Pusat Statistik (BPS-Statistics Indonesia)",
        "subject_count": len(subjects),
        "relevant_subject_count": sum(bool(row["relevant_to_m7"]) for row in subjects),
        "subjects": subjects,
        "interpretation": "National-domain subject IDs are discovery evidence only; no subject ID is inherited from provincial domains.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"subject_count": report["subject_count"], "relevant_subject_count": report["relevant_subject_count"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
