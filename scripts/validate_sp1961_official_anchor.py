from __future__ import annotations

import csv
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "validation" / "historical" / "sp1961" / "manifest.json"
SOURCE_NATIVE = ROOT / "data" / "processed" / "bps" / "historical_population_1961_source_native.csv"

EXPECTED_SHA256 = "bd7c171e06807e0de89bd3b2e8b044d83b00f686319f2483db826e50adc06ff0"
EXPECTED_BYTES = 684_905
EXPECTED_PROVINCE = (2_319_057, 1_117_669, 1_201_388)
EXPECTED_LOCAL_NAMES = {
    "Bukittinggi",
    "Padang",
    "Sawah Lunto",
    "Padang Pandjang",
    "Agam",
    "Pasaman",
    "Limapuluh Kota",
    "Solok",
    "Padang Pariaman",
    "Pasisir Selatan",
    "Tanah Datar",
    "Sawah Lunto/Sidjunjung",
}


def read_rows(path: Path = SOURCE_NATIVE) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def is_official_bps_url(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    return parsed.scheme == "https" and (host == "bps.go.id" or host.endswith(".bps.go.id"))


def validate() -> dict[str, int | str]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows = read_rows()

    assert manifest["schema"] == "ranah-observatory/sp1961-official-artifact/v1"
    assert manifest["title"] == "Sensus Penduduk 1961 Republik Indonesia"
    assert manifest["release_date"] == "1962-06-06"
    assert manifest["artifact_sha256"] == EXPECTED_SHA256
    assert manifest["artifact_bytes"] == EXPECTED_BYTES
    assert manifest["pdf_page_count"] == 15
    assert is_official_bps_url(manifest["official_page_url"])
    assert is_official_bps_url(manifest["official_direct_artifact_url"])
    assert urlparse(manifest["official_direct_artifact_url"]).hostname == "web-api.bps.go.id"
    assert manifest["retrieval_surface"] == "web-api.bps.go.id public direct download"
    assert manifest["raw_pdf_committed"] is False
    assert manifest["table_verification_method"] == (
        "manual_visual_transcription_from_exact_official_pdf_render_plus_arithmetic_reconciliation"
    )
    assert manifest["source_status"] == "preliminary_census_figures_published_1962"
    assert manifest["province_table_pdf_page_index"] == 4
    assert manifest["municipality_table_pdf_page_index"] == 8
    assert manifest["regency_table_pdf_page_index"] == 9
    assert (
        manifest["province_value"],
        manifest["province_male"],
        manifest["province_female"],
    ) == EXPECTED_PROVINCE
    assert manifest["source_native_local_unit_count"] == 12
    assert manifest["municipality_count"] == 4
    assert manifest["regency_count"] == 8
    assert manifest["local_totals_reconcile_exactly_to_province"] is True
    assert manifest["sex_totals_reconcile_exactly_to_province"] is True
    assert manifest["each_row_total_reconciles_to_sex_components"] is True
    assert manifest["historical_population_anchor_authorized_at_source_era_province"] is True
    assert manifest["canonical_current_boundary_mapping_authorized"] is False
    assert manifest["historical_local_geography_mapping_pending"] is True

    assert len(rows) == 13
    assert len({row["source_record_id"] for row in rows}) == 13
    assert all(row["source_id"] == "bps_sp1961_official_pdf" for row in rows)
    assert all(row["artifact_sha256"] == EXPECTED_SHA256 for row in rows)
    assert all(row["source_year"] == "1961" for row in rows)
    assert all(row["unit"] == "persons" for row in rows)
    assert all(row["canonical_indicator_id"] == "historical_population" for row in rows)
    assert all(is_official_bps_url(row["official_page_url"]) for row in rows)
    assert all(is_official_bps_url(row["official_direct_artifact_url"]) for row in rows)
    assert all(row["reconstruction_state"] == "observed_source_era_preliminary_census" for row in rows)

    province = rows[0]
    assert province["source_geography_name"] == "Sumatera Barat"
    assert province["source_geography_type"] == "province"
    assert province["pdf_page_index"] == "4"
    assert province["canonical_geography_id"] == "idn.13.h1958"
    assert province["mapping_status"] == "qualified_source_era"
    assert tuple(int(province[key]) for key in ("value_total", "value_male", "value_female")) == EXPECTED_PROVINCE

    locals_ = rows[1:]
    assert {row["source_geography_name"] for row in locals_} == EXPECTED_LOCAL_NAMES
    assert sum(row["source_geography_type"] == "municipality" for row in locals_) == 4
    assert sum(row["source_geography_type"] == "regency" for row in locals_) == 8
    assert all(not row["canonical_geography_id"] for row in locals_)
    assert all(row["mapping_status"] == "historical_geography_pending" for row in locals_)
    assert all(row["pdf_page_index"] in {"8", "9"} for row in locals_)

    for row in rows:
        total = int(row["value_total"])
        male = int(row["value_male"])
        female = int(row["value_female"])
        assert total == male + female

    assert sum(int(row["value_total"]) for row in locals_) == EXPECTED_PROVINCE[0]
    assert sum(int(row["value_male"]) for row in locals_) == EXPECTED_PROVINCE[1]
    assert sum(int(row["value_female"]) for row in locals_) == EXPECTED_PROVINCE[2]

    municipalities = [row for row in locals_ if row["source_geography_type"] == "municipality"]
    regencies = [row for row in locals_ if row["source_geography_type"] == "regency"]
    assert sum(int(row["value_total"]) for row in municipalities) == 232_952
    assert sum(int(row["value_total"]) for row in regencies) == 2_086_105

    return {
        "rows": len(rows),
        "local_units": len(locals_),
        "province_total": EXPECTED_PROVINCE[0],
        "artifact_sha256": EXPECTED_SHA256,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
