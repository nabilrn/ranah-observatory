from __future__ import annotations

import csv
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "validation" / "historical" / "public_finance_2000"
MANIFEST = BASE / "bps_construction_revision_localization_2001_2004.json"
PRIOR_BREAK = BASE / "bps_construction_financing_major_release_break_2002_2003.json"
PRIOR_REVISION = BASE / "bps_construction_financing_revision_audit_1998_2003.json"
DATA = ROOT / "data" / "processed" / "bps" / "historical_construction_revision_localization_2001_2004.csv"

EXPECTED = {
    2001: (397_936_972, 397_937, 622_547_470, Decimal("56.443737"), Decimal("1.564437370")),
    2002: (458_502_968, 458_503, 717_299_178, Decimal("56.443737"), Decimal("1.564437371")),
    2003: (469_007_986, 469_008, 844_516_928, Decimal("80.064509"), Decimal("1.800645092")),
}


def _official_bps_url(value: str) -> bool:
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower().rstrip(".")
    return parsed.scheme == "https" and (host == "bps.go.id" or host.endswith(".bps.go.id"))


def _rows() -> list[dict[str, str]]:
    with DATA.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _rounded_million(exact_thousand: int) -> int:
    return int((Decimal(exact_thousand) / Decimal(1000)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def validate() -> dict[str, object]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    prior_break = json.loads(PRIOR_BREAK.read_text(encoding="utf-8"))
    prior_revision = json.loads(PRIOR_REVISION.read_text(encoding="utf-8"))
    rows = _rows()

    assert manifest["schema"] == "ranah-observatory/bps-construction-revision-localization-2001-2004/v1"
    assert manifest["source_geography_name"] == "Sumatera Barat"
    assert manifest["canonical_historical_geography_id"] == "idn.13.h1958"
    assert manifest["measure"] == "value of construction completed by province"

    earlier = manifest["earlier_yearbook"]
    later = manifest["later_yearbook"]
    assert earlier["title"] == "Statistik Indonesia 2004"
    assert earlier["catalog_number"] == "1101001"
    assert earlier["publication_number"] == "07330.0508"
    assert earlier["official_bps_metadata_release_date"] == "2005-05-15"
    assert _official_bps_url(earlier["official_page_url"])
    assert earlier["table_number"] == "6.4.5"
    assert earlier["table_unit"] == "million rupiahs"
    assert "Annual Construction Establishment Survey" in earlier["construction_basis_note"]

    assert later["title"] == "Statistik Indonesia 2005/2006"
    assert later["catalog_number"] == "1101001"
    assert later["publication_number"] == "07330.0608"
    assert later["official_bps_metadata_release_date"] == "2006-05-15"
    assert _official_bps_url(later["official_page_url"])
    assert later["pdf_preface_date_text"] == "Jakarta, Juli 2006"
    assert later["metadata_preface_date_conflict_preserved"] is True
    assert later["table_number"] == "6.4.5"
    assert later["table_unit"] == "thousand rupiahs"
    assert later["status_legend"] == {
        "r": "Angka yang diperbaiki / Revised figures",
        "x": "Angka sementara / Preliminary figures",
        "e": "Angka perkiraan / Estimated figures",
    }
    assert "Based on Construction Establishment Survey" in later["construction_basis_note"]

    binding = manifest["earlier_exact_release_binding"]
    assert binding["source_checkpoint"] == "bps_construction_financing_revision_audit_1998_2003.json"
    for year, (earlier_exact, earlier_display, later_exact, _, _) in EXPECTED.items():
        assert binding["values_thousand_rupiah"][str(year)] == earlier_exact
        crosscheck = binding["yearbook_2004_rounding_crosscheck"][str(year)]
        assert crosscheck["rounded_million"] == earlier_display
        assert crosscheck["matches"] is True
        assert _rounded_million(earlier_exact) == earlier_display
        assert int(prior_revision["values_thousand_rupiah"]["total_construction_completed"]["construction_statistics_2003"][str(year)]) == earlier_exact

    old = earlier["sumatera_barat"]
    new = later["sumatera_barat"]
    assert old == {
        "2000": {"display_value_million_rupiah": 345371, "status": "revised"},
        "2001": {"display_value_million_rupiah": 397937, "status": "revised"},
        "2002": {"display_value_million_rupiah": 458503, "status": "published_without_revision_marker"},
        "2003": {"display_value_million_rupiah": 469008, "status": "preliminary"},
        "2004": {"display_value_million_rupiah": 520179, "status": "estimated"},
    }
    assert new == {
        "2001": {"value_thousand_rupiah": 622547470, "status": "revised"},
        "2002": {"value_thousand_rupiah": 717299178, "status": "revised"},
        "2003": {"value_thousand_rupiah": 844516928, "status": "revised"},
        "2004": {"value_thousand_rupiah": 932441815, "status": "preliminary"},
        "2005": {"value_thousand_rupiah": 1046561944, "status": "estimated"},
    }

    localization = manifest["revision_localization"]
    assert localization["earlier_yearbook_still_carries_old_2001_2003_vintage"] is True
    assert localization["later_yearbook_explicitly_marks_2001_2003_as_revised"] is True
    assert localization["revision_first_confirmed_by_examined_yearbook_vintage"] == "Statistik Indonesia 2005/2006"
    assert localization["publication_vintage_window"] == "after Statistik Indonesia 2004 and by Statistik Indonesia 2005/2006"
    assert localization["exact_day_window_authorized"] is False
    assert "metadata dates" in localization["reason_exact_day_window_not_authorized"]
    assert localization["year_2001_revision_delta_thousand_rupiah"] == 224_610_498
    assert Decimal(str(localization["year_2001_revision_delta_percent"])) == Decimal("56.443737")
    assert Decimal(str(localization["year_2001_later_to_earlier_ratio"])) == Decimal("1.564437370")
    assert localization["year_2002_revision_delta_thousand_rupiah"] == 258_796_210
    assert Decimal(str(localization["year_2002_revision_delta_percent"])) == Decimal("56.443737")
    assert Decimal(str(localization["year_2002_later_to_earlier_ratio"])) == Decimal("1.564437371")
    assert localization["year_2001_and_2002_common_scaling_pattern"] is True
    assert localization["common_scaling_pattern_is_descriptive_not_causal"] is True
    assert localization["year_2003_status_transition"] == "preliminary_to_revised"
    assert localization["year_2004_status_transition"] == "estimated_to_preliminary"

    refinement = manifest["classification_refinement"]
    assert refinement["prior_checkpoint_year_2002_classification"] == "major_release_break_unexplained"
    assert prior_break["break_findings"]["year_2002"]["classification"] == refinement["prior_checkpoint_year_2002_classification"]
    assert refinement["refined_year_2002_classification"] == "major_release_break_explicit_revision_cause_unexplained"
    assert refinement["revision_event_confirmed_by_bps_status_marker"] is True
    assert refinement["revision_mechanism_or_formula_documented"] is False
    assert set(refinement["candidate_mechanisms_not_asserted"]) == {
        "rebenchmarking", "reweighting", "coverage expansion", "frame revision", "reprocessing"
    }
    assert refinement["year_2003_status_transition_checkpoint_remains_valid"] is True

    gate = manifest["gate"]
    assert gate["retain_all_vintages"] is True
    assert gate["silent_overwrite_authorized"] is False
    assert gate["single_continuous_1998_2006_trajectory_authorized"] is False
    assert gate["cross_vintage_bridge_authorized"] is False
    assert gate["canonical_fiscal_mapping_authorized"] is False
    assert gate["panel_v3_integration_authorized"] is False
    assert gate["causal_explanation_of_revision_authorized"] is False

    source = manifest["source_boundary"]
    assert source["official_bps_metadata_pages_verified"] is True
    assert "mirrored BPS Statistical Yearbook PDFs" in source["table_text_evidence_surface"]
    assert source["screenshot_attempted"] is True
    assert source["screenshot_status"] == "cache miss for both yearbook PDF mirrors"
    assert source["yearbook_pdf_sha256_available_in_repository"] is False
    assert source["mirror_treated_as_official_artifact_sha_equivalent"] is False

    assert len(rows) == 4
    by_year = {int(row["year"]): row for row in rows}
    assert set(by_year) == {2001, 2002, 2003, 2004}

    for year, (earlier_exact, earlier_display, later_exact, pct, ratio) in EXPECTED.items():
        row = by_year[year]
        assert row["source_geography_name"] == "Sumatera Barat"
        assert row["canonical_historical_geography_id"] == "idn.13.h1958"
        assert int(row["earlier_exact_value_thousand_rupiah"]) == earlier_exact
        assert int(row["yearbook_2004_display_value_million_rupiah"]) == earlier_display
        assert int(row["yearbook_2005_2006_value_thousand_rupiah"]) == later_exact
        assert int(row["revision_delta_from_earlier_exact_thousand_rupiah"]) == later_exact - earlier_exact
        assert Decimal(row["revision_delta_percent_from_earlier_exact"]) == pct
        assert Decimal(row["later_to_earlier_exact_ratio"]) == ratio
        assert row["revision_event_confirmed"] == "true"
        assert row["revision_mechanism_explained"] == "false"

    row_2004 = by_year[2004]
    assert row_2004["earlier_exact_value_thousand_rupiah"] == ""
    assert int(row_2004["yearbook_2004_display_value_million_rupiah"]) == 520179
    assert row_2004["yearbook_2004_status"] == "estimated"
    assert int(row_2004["yearbook_2005_2006_value_thousand_rupiah"]) == 932441815
    assert row_2004["yearbook_2005_2006_status"] == "preliminary"
    assert row_2004["revision_delta_from_earlier_exact_thousand_rupiah"] == ""
    assert row_2004["revision_event_confirmed"] == "true"
    assert row_2004["revision_mechanism_explained"] == "false"

    return {
        "rows": len(rows),
        "revision_event_confirmed": True,
        "revision_mechanism_explained": False,
        "first_confirmed_revised_yearbook_vintage": "Statistik Indonesia 2005/2006",
        "year_2001_and_2002_common_scaling_pattern": True,
        "refined_2002_classification": "major_release_break_explicit_revision_cause_unexplained",
        "single_continuous_1998_2006_trajectory_authorized": False,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
