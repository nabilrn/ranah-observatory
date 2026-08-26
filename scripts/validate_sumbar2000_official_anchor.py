from __future__ import annotations

import csv
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "validation" / "historical" / "sumbar2000"
ARTIFACT = BASE / "artifact_manifest.json"
INDEX = BASE / "structural_index.json"
POPULATION = BASE / "population_anchor_manifest.json"
SOURCE_NATIVE = ROOT / "data" / "processed" / "bps" / "historical_population_2000_source_native.csv"

EXPECTED_SHA256 = "689318d0760f99ff82a54866295b580a0159ed0e39051b4342b8b7e9d13648cf"
EXPECTED_BYTES = 31_081_427
EXPECTED_PAGES = 646
EXPECTED_POPULATION = (4_220_318, 2_070_602, 2_149_716)


def official_bps_url(value: str) -> bool:
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower().rstrip(".")
    return parsed.scheme == "https" and (host == "bps.go.id" or host.endswith(".bps.go.id"))


def validate() -> dict[str, int | bool | str]:
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    population = json.loads(POPULATION.read_text(encoding="utf-8"))
    with SOURCE_NATIVE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert artifact["schema"] == "ranah-observatory/sumbar2000-official-artifact/v1"
    assert artifact["title"] == "Sumatera Barat Dalam Angka Tahun 2000"
    assert artifact["artifact_sha256"] == EXPECTED_SHA256
    assert artifact["artifact_bytes"] == EXPECTED_BYTES
    assert artifact["pdf_page_count"] == EXPECTED_PAGES
    assert artifact["builtin_text_char_count"] == 737_222
    assert artifact["full_publication_artifact_acquired"] is True
    assert artifact["historical_anchor_satisfied"] is True
    assert artifact["raw_pdf_committed"] is False
    assert artifact["numeric_extraction_started"] is True
    assert artifact["numeric_promotion_authorized"] is False
    assert artifact["blanket_numeric_promotion_authorized"] is False
    assert artifact["qualified_extraction_manifests"] == [
        "data/validation/historical/sumbar2000/population_anchor_manifest.json"
    ]
    assert artifact["current_catalog_number"] == "1102001.13"
    assert artifact["source_native_cover_catalog_number"] == "1403.13"
    assert official_bps_url(artifact["official_page_url"])
    assert official_bps_url(artifact["official_direct_artifact_url"])
    assert urlparse(artifact["official_direct_artifact_url"]).hostname == "web-api.bps.go.id"
    review = artifact["visual_completeness_review"]
    assert review["sampled_pdf_pages"] == [1, 323, 646]
    assert review["main_statistical_table_body_present"] is True
    assert review["back_cover_present_on_final_pdf_page"] is True
    assert review["sampled_body_pdf_page"] == 323
    assert review["sampled_body_printed_page"] == 268

    assert index["schema"] == "ranah-observatory/sumbar2000-structural-discovery-index/v1"
    assert index["artifact_sha256"] == EXPECTED_SHA256
    assert index["source_pdf_page_count"] == EXPECTED_PAGES
    assert index["text_layer_char_count"] == 736_122
    assert index["numeric_promotion_authorized"] is False
    assert index["extraction_method"] == "pdftotext-layout-built-in-text-layer-only-no-ocr"
    assert index["evidentiary_role"].startswith("page/table discovery only")
    domains = index["domains"]
    assert {"population", "education", "health", "agriculture", "industry", "public_finance", "transport", "trade"} == set(domains)
    assert all(domains[name] for name in domains)
    population_pages = {row["pdf_page"] for row in domains["population"]}
    assert {92, 94, 95, 96}.issubset(population_pages)
    assert 226 in {row["pdf_page"] for row in domains["agriculture"]}
    assert 150 in {row["pdf_page"] for row in domains["health"]}
    assert 312 in {row["pdf_page"] for row in domains["industry"]}

    assert population["schema"] == "ranah-observatory/sumbar2000-population-anchor/v1"
    assert population["artifact_sha256"] == EXPECTED_SHA256
    assert population["source_year"] == 2000
    assert population["canonical_indicator_id"] == "historical_population"
    assert population["canonical_geography_id"] == "idn.13.h1958"
    assert population["historical_population_anchor_authorized_at_source_era_province"] is True
    assert population["canonical_current_local_boundary_mapping_authorized"] is False
    assert population["local_geography_mapping_pending"] is True
    assert population["reconstruction_state"] == "derived_source_era"
    assert population["table_verification_method"] == (
        "manual_visual_review_plus_builtin_text_layer_plus_arithmetic_reconciliation"
    )
    assert "Survei Sosial Ekonomi Nasional 2000" in population["population_source_family"]

    primary = population["primary_table"]
    assert primary["table_number"] == "3.1.3"
    assert primary["pdf_page"] == 96
    assert primary["printed_page"] == 41
    assert primary["unit_label"] == "x 1000"
    assert primary["source_line"] == "BPS, Hasil Survei Sosial Ekonomi Nasional 2000"
    raw = primary["raw_values_x1000_persons"]
    raw_total = Decimal(str(raw["total"]))
    raw_male = Decimal(str(raw["male"]))
    raw_female = Decimal(str(raw["female"]))
    assert raw_male + raw_female == raw_total == Decimal("4220.318")

    normalized = population["normalized_values_persons"]
    assert (
        normalized["total"],
        normalized["male"],
        normalized["female"],
    ) == EXPECTED_POPULATION
    assert int(raw_total * 1000) == normalized["total"]
    assert int(raw_male * 1000) == normalized["male"]
    assert int(raw_female * 1000) == normalized["female"]

    q = Decimal("0.01")
    t311 = population["reconciliation"]["table_3_1_1"]
    t312 = population["reconciliation"]["table_3_1_2"]
    assert Decimal(str(t311["reported_total_x1000_persons"])) == raw_total.quantize(q, rounding=ROUND_HALF_UP)
    assert Decimal(str(t312["reported_total_x1000_persons"])) == raw_total.quantize(q, rounding=ROUND_HALF_UP)
    assert Decimal(str(t312["male_x1000_persons"])) == raw_male.quantize(q, rounding=ROUND_HALF_UP)
    assert Decimal(str(t312["female_x1000_persons"])) == raw_female.quantize(q, rounding=ROUND_HALF_UP)
    assert population["chapter_narrative_crosscheck"]["reported_population_million"] == 4.22
    local = population["source_native_local_structure"]
    assert local["regencies"] == 8
    assert local["municipalities"] == 6
    assert local["total_units"] == 14
    assert "current 19-unit" in local["warning"]

    assert len(rows) == 1
    row = rows[0]
    assert row["source_record_id"] == "sumbar2000_table_3_1_3_province"
    assert row["source_id"] == "bps_sumbar2000_official_pdf"
    assert row["artifact_sha256"] == EXPECTED_SHA256
    assert row["source_year"] == "2000"
    assert row["pdf_page_index"] == "96"
    assert row["source_geography_name"] == "Sumatera Barat"
    assert row["source_geography_type"] == "province"
    assert row["unit"] == "persons"
    assert row["canonical_indicator_id"] == "historical_population"
    assert row["canonical_geography_id"] == "idn.13.h1958"
    assert row["mapping_status"] == "qualified_source_era"
    assert row["reconstruction_state"] == "derived_source_era"
    assert official_bps_url(row["official_page_url"])
    assert official_bps_url(row["official_direct_artifact_url"])
    row_values = tuple(int(row[key]) for key in ("value_total", "value_male", "value_female"))
    assert row_values == EXPECTED_POPULATION
    assert row_values[1] + row_values[2] == row_values[0]
    assert "14 source-era local units" in row["notes"]
    assert "current 19 kabupaten/kota" in row["notes"]

    return {
        "artifact_complete": True,
        "artifact_pages": EXPECTED_PAGES,
        "population_total": EXPECTED_POPULATION[0],
        "source_native_rows": len(rows),
        "blanket_numeric_promotion_authorized": False,
        "artifact_sha256": EXPECTED_SHA256,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
