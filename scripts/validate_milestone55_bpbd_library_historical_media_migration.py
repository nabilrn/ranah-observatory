#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
M54 = ROOT / "data" / "manifests" / "milestone54_bpbd_2022_official_source_disagreement.json"
M55 = ROOT / "data" / "manifests" / "milestone55_bpbd_library_historical_media_migration.json"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _official(url: str) -> bool:
    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        and parsed.hostname is not None
        and (
            parsed.hostname == "sumbarprov.go.id"
            or parsed.hostname.endswith(".sumbarprov.go.id")
        )
    )


def validate() -> dict[str, Any]:
    m54 = _read_json(M54)
    m55 = _read_json(M55)

    assert m55["schema"] == "ranah-observatory/milestone55-bpbd-library-historical-media-migration/v1"
    assert m55["milestone"] == 55
    assert m55["depends_on"] == [54]
    assert m55["decision_date"] == "2026-09-02"

    library = m55["current_library"]
    assert library["agency_id"] == 2696
    assert library["lkj_category_slug"] == "laporan-kinerja-instansi-pemerintah"
    assert library["lkj_category_row_count_observed"] == 5
    assert _official(library["public_page_url"])
    assert _official(library["lkj_category_api_url"])

    row = library["lkj_2022_row"]
    assert row == {
        "category": "Laporan Kinerja Instansi Pemerintah",
        "created_at": "16 Februari 2023 16:15:8",
        "created_by": "Admin BPBD",
        "gambar": "/api/files/badan-penanggulangan-bencana-daerah/2023/02/LKJ_BPBD_TAHUN_2022.pdf",
        "slug": "laporan-kinerja-badan-penanggulangan-bencana-daerah-tahun-2022-332",
        "status": "Publish",
        "title": "Laporan Kinerja Badan Penanggulangan Bencana Daerah Tahun 2022",
    }

    transport = m55["transport_audit"]
    assert _official(transport["legacy_lkj_2022_url"])
    assert _official(transport["current_lkj_2022_file_url"])

    legacy = transport["legacy_lkj_2022_response"]
    assert legacy["http_status"] == 200
    assert legacy["content_type"] == "text/html"
    assert legacy["byte_count"] == 1194
    assert legacy["sha256"] == "7e0ebbde81104e10d61008e405636958da368f05d5fd9b859da88007e74d9b7f"
    assert legacy["classification"] == "spa_fallback_not_pdf"

    current = transport["current_lkj_2022_response"]
    assert current["http_status"] == 500
    assert current["content_type"] == "application/json; charset=utf-8"
    assert current["byte_count"] == 60
    assert current["sha256"] == "1fb247e83188a06958c4d3a532ed0cd44be4a3bd3a7d6b93487f25183eadc12a"
    assert current["error"] == "Minio S3Error: The specified key does not exist."
    assert current["classification"] == "published_metadata_missing_storage_object"

    probe = transport["vintage_probe"]
    assert len(probe) == 5
    recovered = [item for item in probe if item["pdf_recovered"]]
    missing = [item for item in probe if not item["pdf_recovered"]]
    assert len(recovered) == 2
    assert len(missing) == 3
    assert {item["metadata_vintage"] for item in recovered} == {"2026/05", "2026/03"}
    assert {item["metadata_vintage"] for item in missing} == {"2024/05", "2023/02", "2016/03"}
    assert all(item["http_status"] == 200 and item["content_type"] == "application/pdf" for item in recovered)
    assert all(item["http_status"] == 500 and item["content_type"].startswith("application/json") for item in missing)
    assert all(item["sha256"] == current["sha256"] for item in missing)
    assert {item["sha256"] for item in recovered} == {
        "c3a45bb8c9e7dfe2ee8daf39b2702b969e1c13911a31c81681bf20e8059f3bd7",
        "7c5ddeee330c38649caae42d8a0f28d89d2af959b0ccdd78778dfcfee314d64b",
    }

    sweep = m55["category_sweep"]
    assert len(sweep["reviewed_slugs"]) == 13
    assert sweep["successful_category_payload_count"] == 12
    assert sweep["renaksi_http_status"] == 404
    assert sweep["dibi_literal_match_count_in_returned_payloads"] == 0
    assert sweep["buku_dibi_2022_current_library_row_recovered"] is False

    interpretation = m55["interpretation"]
    assert interpretation["current_bpbd_library_metadata_for_lkj_2022_is_live"] is True
    assert interpretation["current_bpbd_storage_transport_is_functional_for_newer_objects"] is True
    assert interpretation["lkj_2022_metadata_pointer_resolves_to_missing_minio_key"] is True
    assert interpretation["historical_media_migration_gap_supported"] is True
    assert interpretation["raw_lkj_2022_pdf_recovered_from_current_library"] is False
    assert interpretation["raw_dibi_2022_pdf_recovered_from_current_library"] is False
    assert interpretation["web_indexed_or_cached_pdf_may_satisfy_raw_artifact_gate"] is False

    boundary = m55["research_boundary"]
    assert boundary["lkj_2022_source_native_materialization_authorized"] is False
    assert boundary["dibi_2022_source_native_materialization_authorized"] is False
    assert boundary["canonical_2022_disaster_timeseries_authorized"] is False
    assert boundary["do_not_treat_metadata_presence_as_artifact_availability"] is True
    assert boundary["do_not_treat_spa_fallback_http_200_as_successful_pdf_retrieval"] is True

    result = m55["result"]
    assert result["current_library_transport_audited"] is True
    assert result["newer_storage_objects_retrievable"] == 2
    assert result["historical_metadata_objects_missing"] == 3
    assert result["lkj_2022_raw_artifact_acquired"] is False
    assert result["dibi_2022_current_library_route_found"] is False
    assert result["historical_media_migration_gap_confirmed"] is True
    assert result["promotion_gate_fail_closed"] is True

    # M55 must not weaken the cross-publication disagreement frozen in M54.
    assert m54["sources"]["dibi_2022"]["event_total"] == 1021
    assert m54["sources"]["lkj_2022"]["event_total"] == 1047
    assert m54["sources"]["dibi_2022"]["raw_bytes_frozen"] is False
    assert m54["sources"]["lkj_2022"]["raw_bytes_frozen"] is False
    assert m54["result"]["canonical_unified_2022_series_authorized"] is False

    return {
        "schema": "ranah-observatory/milestone55-bpbd-library-historical-media-migration-audit/v1",
        "milestone": 55,
        "lkj_category_rows": library["lkj_category_row_count_observed"],
        "newer_pdf_objects_recovered": len(recovered),
        "historical_objects_missing": len(missing),
        "dibi_literal_matches": sweep["dibi_literal_match_count_in_returned_payloads"],
        "lkj_2022_raw_artifact_acquired": False,
        "dibi_2022_route_found": False,
        "canonical_2022_series_authorized": False,
        "complete": True,
    }


def main() -> int:
    try:
        report = validate()
    except (AssertionError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"M55 validation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
