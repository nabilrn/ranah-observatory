#!/usr/bin/env python3
"""Refresh the BPBD workbook portion without re-fetching BIG boundaries.

The full ``acquire_sumbar_public_disaster_sources.py`` remains the explicit
boundary-refresh path. This wrapper is the routine source-refresh path so a
slow BIG administrative query cannot block unrelated BPBD workbook updates.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from acquire_sumbar_public_disaster_sources import (
    BPBD_MANIFEST,
    BPBD_OUTPUT,
    BPBD_PACKAGES,
    MANIFEST_DIR,
    ROOT,
    ckan_action,
    materialize_workbook,
)


def main() -> None:
    retrieved_at = datetime.now(timezone.utc).isoformat()
    BPBD_OUTPUT.mkdir(parents=True, exist_ok=True)
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)

    records = []
    for slug in BPBD_PACKAGES:
        package = ckan_action("package_show", id=slug)
        record = materialize_workbook(slug, package)
        records.append(record)
        print(json.dumps({
            "bpbd_package": slug,
            "worksheets": len(record["worksheets"]),
            "sha256": record["download_sha256"],
        }))

    BPBD_MANIFEST.write_text(
        json.dumps(
            {
                "schema": "ranah-observatory/sumbar-bpbd-open-data-acquisition/v1",
                "retrieved_at": retrieved_at,
                "source": "https://data.sumbarprov.go.id/",
                "producer": "BPBD Provinsi Sumatera Barat",
                "source_data": "Pusdalops BPBD Sumatera Barat",
                "year": 2024,
                "promotion_state": "source_native_review_required",
                "missing_values_inferred": False,
                "packages": records,
                "boundary_refresh_performed": False,
                "boundary_note": "Routine BPBD refresh reuses the separately materialized BIG boundary. Run acquire_sumbar_public_disaster_sources.py explicitly when refreshing geography.",
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    print(json.dumps({
        "bpbd_manifest": BPBD_MANIFEST.relative_to(ROOT).as_posix(),
        "bpbd_package_count": len(records),
        "boundary_refresh_performed": False,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
