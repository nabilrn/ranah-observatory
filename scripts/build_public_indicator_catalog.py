from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
METADATA = ROOT / "data" / "analysis" / "engine" / "panel_v3" / "m46-indicator-metadata.csv"
COVERAGE = ROOT / "data" / "analysis" / "engine" / "panel_v3" / "m46-indicator-coverage.csv"
DEFAULT_OUTPUT = ROOT / "site" / "data" / "indicators.json"

DOMAIN_LABELS = {
    "education_knowledge": "Pendidikan & pengetahuan",
    "health": "Kesehatan",
    "labor_livelihoods": "Pasar kerja",
    "income_productivity_poverty_inequality": "Ekonomi & kesejahteraan",
    "production_trade": "Produksi & struktur ekonomi",
    "demography_migration": "Demografi",
    "environment_climate": "Iklim & lingkungan",
    "disaster_resilience": "Bencana & ketahanan",
    "infrastructure_connectivity": "Infrastruktur & konektivitas",
}

UNIT_LABELS = {
    "years": "tahun",
    "percent": "%",
    "count": "kejadian",
    "persons": "orang",
    "millimetres": "mm",
    "tonnes_per_hectare": "ton/ha",
    "thousand_idr_constant_2010_per_capita": "ribu rupiah konstan 2010 per kapita",
    "ratio": "rasio",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def split_pipe(value: str) -> list[str]:
    return [part for part in value.split("|") if part]


def build(metadata_path: Path = METADATA, coverage_path: Path = COVERAGE) -> dict[str, Any]:
    metadata_rows = read_csv(metadata_path)
    coverage_rows = read_csv(coverage_path)

    metadata = {row["indicator_id"]: row for row in metadata_rows}
    coverage = {row["indicator_id"]: row for row in coverage_rows}
    assert len(metadata_rows) == len(metadata), "duplicate indicator id in Panel v3 metadata"
    assert len(coverage_rows) == len(coverage), "duplicate indicator id in Panel v3 coverage"
    assert set(metadata) == set(coverage), "Panel v3 metadata/coverage indicator sets differ"
    assert len(metadata) == 23, f"expected 23 Panel v3 indicators, found {len(metadata)}"

    indicators: list[dict[str, Any]] = []
    for indicator_id in sorted(metadata):
        meta = metadata[indicator_id]
        cov = coverage[indicator_id]
        assert meta["source_artifact"] == cov["source_artifact"], f"source artifact drift: {indicator_id}"
        assert meta["registry_unit"] == cov["units"], f"unit drift: {indicator_id}"
        assert meta["domain"] in DOMAIN_LABELS, f"unmapped domain: {meta['domain']}"
        assert meta["registry_unit"] in UNIT_LABELS, f"unmapped unit: {meta['registry_unit']}"

        present = int(cov["present_cells"])
        total = int(cov["total_possible_cells"])
        missing = int(cov["missing_cells"])
        rate = float(cov["coverage_rate"])
        assert present + missing == total
        assert abs((present / total) - rate) < 1e-8

        indicators.append({
            "id": indicator_id,
            "name": meta["name"],
            "domain": meta["domain"],
            "domain_label": DOMAIN_LABELS[meta["domain"]],
            "definition": meta["definition"],
            "registry_unit": meta["registry_unit"],
            "unit_label": UNIT_LABELS[meta["registry_unit"]],
            "frequency": meta["registry_frequency"],
            "allowed_claim_types": split_pipe(meta["allowed_claim_types"]),
            "present_claim_types": split_pipe(cov["claim_types"]),
            "source_priority": split_pipe(meta["source_priority"]),
            "source_artifact": meta["source_artifact"],
            "semantic_caution": meta["semantic_caution"],
            "coverage": {
                "present_cells": present,
                "total_possible_cells": total,
                "missing_cells": missing,
                "rate": rate,
                "first_year": int(cov["first_year"]),
                "last_year": int(cov["last_year"]),
                "years_present_count": int(cov["years_present_count"]),
                "years_present": [int(year) for year in split_pipe(cov["years_present"])],
                "exact_19_geography_year_count": int(cov["exact_19_geography_year_count"]),
            },
            "comparability": cov["comparable_values"],
            "methodology_versions": cov["methodology_versions"],
            "price_bases": cov["price_bases"],
            "reference_period_patterns": cov["reference_period_patterns"],
        })

    domains = sorted({row["domain_label"] for row in indicators})
    complete = sum(row["coverage"]["rate"] == 1.0 for row in indicators)

    return {
        "schema": "ranah-observatory/public-indicator-catalog/v1",
        "version": "0.1.0",
        "language": "id",
        "title": "Katalog data Panel v3",
        "intro": (
            "Katalog ini menunjukkan data yang tersedia di panel analitis saat ini. "
            "Coverage bukan skor kualitas daerah dan keberadaan indikator bukan izin untuk membuat klaim sebab-akibat."
        ),
        "summary": {
            "indicator_count": len(indicators),
            "domain_count": len(domains),
            "complete_2018_2025_indicator_count": complete,
            "panel_years": [2018, 2025],
            "geography_count": 19,
        },
        "sources": {
            "metadata": {
                "path": "data/analysis/engine/panel_v3/m46-indicator-metadata.csv",
                "sha256": sha256_file(metadata_path),
            },
            "coverage": {
                "path": "data/analysis/engine/panel_v3/m46-indicator-coverage.csv",
                "sha256": sha256_file(coverage_path),
            },
        },
        "domains": domains,
        "indicators": indicators,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the bounded public Panel v3 indicator catalog")
    parser.add_argument("--metadata", type=Path, default=METADATA)
    parser.add_argument("--coverage", type=Path, default=COVERAGE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    payload = build(args.metadata, args.coverage)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "indicators": payload["summary"]["indicator_count"],
        "domains": payload["summary"]["domain_count"],
        "complete_2018_2025": payload["summary"]["complete_2018_2025_indicator_count"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
