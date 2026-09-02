#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE_MANIFEST = ROOT / "data/manifests/milestone60_bpbd_profile_2014_2024_acquisition.json"
BOOK_MANIFEST = ROOT / "data/manifests/milestone60_bpbd_book_2024_acquisition.json"
FINAL = ROOT / "data/manifests/milestone60_bpbd_profile_2014_2024_final.json"
PROFILE = ROOT / "data/raw/bpbd/m60_profile_2014_2024/profil-bencana-sumbar-2014-sd-2024.jpeg"
BOOK = ROOT / "data/raw/bpbd/m60_book_2024/data-dan-informasi-bencana-sumatera-barat-2024.pdf"
BOOK_SEARCH = ROOT / "data/processed/bpbd/disaster_profile_2014_2024/diagnostic-book-historical-search.txt"
CATALOG = ROOT / "catalog/public-datasets.csv"
FORBIDDEN_IDS = ("bpbd-disaster-profile-2014-2024", "bpbd-disaster-timeseries-2014-2024")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate() -> dict:
    profile = json.loads(PROFILE_MANIFEST.read_text(encoding="utf-8"))
    book = json.loads(BOOK_MANIFEST.read_text(encoding="utf-8"))
    final = json.loads(FINAL.read_text(encoding="utf-8"))

    assert profile["schema"] == "ranah-observatory/milestone60-bpbd-profile-2014-2024-acquisition/v1"
    assert profile["source"]["package_id"] == "8acd9009-56df-43ba-b079-a477ab844edb"
    assert profile["source"]["resource_id"] == "b15be1ad-80b9-4ffa-9e6b-a8e0118599cb"
    assert profile["source"]["source_data"] == "Pusdalop BPBD Sumatera Barat"
    assert profile["raw_artifact"]["width_px"] == 1280
    assert profile["raw_artifact"]["height_px"] == 720
    assert sha256(PROFILE) == profile["raw_artifact"]["sha256"]

    assert book["schema"] == "ranah-observatory/milestone60-bpbd-book-2024-acquisition/v1"
    assert book["source"]["package_id"] == "f0e9b9f4-d382-4bbc-a84a-5a5a5ffeee2a"
    assert book["source"]["resource_id"] == "3d7b1f51-226e-43c3-9ff8-2cbcc85fe978"
    assert sha256(BOOK) == book["raw_artifact"]["sha256"]
    assert BOOK_SEARCH.read_text(encoding="utf-8").strip() == ""

    assert final["schema"] == "ranah-observatory/milestone60-bpbd-profile-2014-2024-final/v1"
    assert final["status"] == "qualification_hold"
    q = final["qualification"]
    assert q["official_profile_artifact_frozen"] is True
    assert q["official_companion_book_frozen"] is True
    assert q["machine_readable_2014_2024_timeseries_found"] is False
    assert q["diagnostic_ocr_considered_source_truth"] is False
    assert q["manual_image_transcription_authorized"] is False
    assert q["historical_timeseries_extraction_authorized"] is False
    assert q["dashboard_promotion_authorized"] is False
    assert q["public_catalog_registration_authorized"] is False
    assert final["result"]["unsafe_numeric_promotion_blocked"] is True
    assert final["result"]["milestone_complete"] is True

    catalog = CATALOG.read_text(encoding="utf-8")
    assert all(dataset_id not in catalog for dataset_id in FORBIDDEN_IDS)

    return {
        "milestone": 60,
        "status": "qualification_hold",
        "raw_profile_frozen": True,
        "raw_book_frozen": True,
        "historical_series_materialized": False,
        "unsafe_numeric_promotion_blocked": True,
        "complete": True,
    }


def main() -> int:
    try:
        report = validate()
    except (AssertionError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"M60 validation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
