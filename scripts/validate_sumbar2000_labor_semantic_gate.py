from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "validation" / "historical" / "sumbar2000"
ARTIFACT = BASE / "artifact_manifest.json"
INDEX = BASE / "structural_index.json"
GATE = BASE / "labor_semantic_gate.json"
PANEL_METADATA = ROOT / "data" / "analysis" / "engine" / "panel_v3" / "m46-indicator-metadata.csv"
QUALIFICATION_DOC = ROOT / "docs" / "BPS_NORMALIZED_PANEL.md"

EXPECTED_SHA256 = "689318d0760f99ff82a54866295b580a0159ed0e39051b4342b8b7e9d13648cf"
EXPECTED_INDICATORS = ["labor_force_participation", "unemployment_rate"]


def validate() -> dict[str, bool | int | str]:
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    qualification_doc = QUALIFICATION_DOC.read_text(encoding="utf-8")

    with PANEL_METADATA.open(encoding="utf-8", newline="") as handle:
        metadata = {row["indicator_id"]: row for row in csv.DictReader(handle)}

    assert gate["schema"] == "ranah-observatory/sumbar2000-labor-semantic-gate/v1"
    assert gate["artifact_sha256"] == EXPECTED_SHA256
    assert artifact["artifact_sha256"] == EXPECTED_SHA256
    assert index["artifact_sha256"] == EXPECTED_SHA256
    assert artifact["full_publication_artifact_acquired"] is True
    assert artifact["blanket_numeric_promotion_authorized"] is False
    assert gate["source_year"] == 2000
    assert gate["candidate_indicators"] == EXPECTED_INDICATORS

    evidence = gate["historical_source_evidence"]
    assert evidence["structural_index_path"] == (
        "data/validation/historical/sumbar2000/structural_index.json"
    )
    assert evidence["exact_tpak_table_verified"] is False
    assert evidence["exact_tpt_table_verified"] is False
    assert evidence["exact_tpak_value_verified"] is False
    assert evidence["exact_tpt_value_verified"] is False
    assert evidence["exact_reference_period_verified"] is False
    assert evidence["exact_population_universe_verified"] is False

    signals = evidence["related_labor_universe_signals"]
    assert [signal["pdf_page"] for signal in signals] == [92, 103]
    assert all("10 years and over" in signal["evidence"] for signal in signals)
    assert all(signal["role"].startswith("semantic caution only") for signal in signals)

    indexed_pages = {
        row["pdf_page"]
        for rows in index["domains"].values()
        for row in rows
    }
    assert {92, 103}.issubset(indexed_pages)

    for indicator_id in EXPECTED_INDICATORS:
        assert indicator_id in metadata
        row = metadata[indicator_id]
        assert row["domain"] == "labor_livelihoods"
        assert row["registry_unit"] == "percent"
        assert "BPS" in row["source_priority"]
        assert "August Sakernas" in row["semantic_caution"]

    modern = gate["modern_panel_identity"]
    assert modern["panel_metadata_path"] == (
        "data/analysis/engine/panel_v3/m46-indicator-metadata.csv"
    )
    assert modern["qualification_doc_path"] == "docs/BPS_NORMALIZED_PANEL.md"
    assert modern["labor_force_participation_source_family"] == "BPS August Sakernas"
    assert modern["unemployment_rate_source_family"] == "BPS August Sakernas"
    assert modern["cross_regime_weighting_comparability_resolved"] is False
    assert "### Labor-force participation — TPAK" in qualification_doc
    assert "### Open unemployment rate — TPT" in qualification_doc
    assert "Cross-regime comparability remains unresolved" in qualification_doc

    decision = gate["decision"]
    assert decision["source_native_numeric_extraction_authorized"] is False
    assert decision["canonical_promotion_authorized"] is False
    assert decision["panel_v3_backfill_authorized"] is False
    assert "exact TPAK/TPT table identity" in decision["reason"]
    assert "age-10-plus" in decision["reason"]

    next_gate = gate["next_gate"]
    assert len(next_gate) == 5
    assert any("table number" in item for item in next_gate)
    assert any("modern August-Sakernas contract" in item for item in next_gate)
    assert any("do not backfill Panel v3" in item for item in next_gate)
    assert any("Do not interpolate" in item for item in next_gate)

    return {
        "artifact_bound": True,
        "candidate_indicator_count": len(EXPECTED_INDICATORS),
        "historical_table_identity_resolved": False,
        "canonical_promotion_authorized": False,
        "panel_v3_backfill_authorized": False,
        "artifact_sha256": EXPECTED_SHA256,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
