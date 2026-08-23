from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "analysis" / "engine" / "hierarchical_trajectory_v1" / "m22-geography-trajectories.csv"
DEFAULT_OUTPUT = ROOT / "site" / "data" / "districts.json"

INDICATORS: dict[str, dict[str, Any]] = {
    "labor_force_participation": {
        "label": "Partisipasi angkatan kerja",
        "short_label": "Partisipasi kerja",
        "unit": "%",
        "decimals": 2,
        "source_claim_id": "C22_LFP_TRAJECTORY",
        "favorable_semantics": "Kenaikan umumnya lebih menguntungkan, tetapi tidak otomatis berarti kualitas pekerjaan membaik.",
        "boundary": "Trajectory 2018–2025; bukan efek kebijakan dan bukan ramalan setelah 2025.",
    },
    "unemployment_rate": {
        "label": "Tingkat pengangguran",
        "short_label": "Pengangguran",
        "unit": "%",
        "decimals": 2,
        "source_claim_id": "C22_UNEMPLOYMENT_TRAJECTORY",
        "favorable_semantics": "Penurunan umumnya lebih menguntungkan; kenaikan berarti arah yang kurang menguntungkan dalam indikator ini.",
        "boundary": "Trajectory 2018–2025; tidak mengidentifikasi penyebab perubahan pengangguran.",
    },
    "real_grdp_growth": {
        "label": "Pertumbuhan PDRB riil",
        "short_label": "Pertumbuhan PDRB",
        "unit": "%",
        "decimals": 2,
        "source_claim_id": "C22_GRDP_GROWTH_TRAJECTORY",
        "favorable_semantics": "Laju yang lebih tinggi umumnya lebih menguntungkan, tetapi slope tidak boleh dibaca sebagai akselerasi struktural.",
        "boundary": "Model indikator lolos tipis, tetapi 0/19 trajectory daerah robust; seluruh daerah harus tampil sebagai arah belum robust.",
    },
    "rice_yield": {
        "label": "Produktivitas padi",
        "short_label": "Produktivitas padi",
        "unit": "ton/ha",
        "decimals": 3,
        "source_claim_id": "C22_RICE_YIELD_TRAJECTORY",
        "favorable_semantics": "Nilai yang lebih tinggi umumnya lebih menguntungkan dalam indikator produktivitas hasil.",
        "boundary": "Trajectory deskriptif 2018–2025; unit canonical tonnes_per_hectare, produktivitas KSA-based, dan hasil tidak mengidentifikasi efek kebijakan atau iklim.",
    },
}

CLASSIFICATION_LABELS = {
    "persistent_increase": "naik persisten",
    "persistent_decrease": "turun persisten",
    "trajectory_not_robust": "arah belum robust",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def as_float(value: str) -> float:
    return float(value)


def load_selected_rows(source: Path) -> list[dict[str, str]]:
    with source.open(encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row["indicator_id"] in INDICATORS]
    expected = len(INDICATORS) * 19
    assert len(rows) == expected, f"expected {expected} selected M22 rows, found {len(rows)}"
    return rows


def build(source: Path = SOURCE) -> dict[str, Any]:
    rows = load_selected_rows(source)
    by_geo: dict[str, dict[str, Any]] = {}

    for row in rows:
        indicator_id = row["indicator_id"]
        meta = INDICATORS[indicator_id]
        assert row["indicator_hierarchical_trajectory_qualified"] == "True"
        assert row["causal_claim_authorized"] == "False"
        assert row["guaranteed_future_trajectory_authorized"] == "False"
        assert row["historical_boundary_continuity_claimed"] == "False"
        classification = row["trajectory_classification"]
        assert classification in CLASSIFICATION_LABELS, classification

        geo_id = row["geography_id"]
        geography = by_geo.setdefault(
            geo_id,
            {
                "id": geo_id,
                "name": row["geography_name"],
                "administrative_type": "kota" if ".137" in geo_id else "kabupaten",
                "period": [2018, 2025],
                "indicators": {},
            },
        )
        assert geography["name"] == row["geography_name"]

        start = as_float(row["observed_2018"])
        end = as_float(row["observed_2025"])
        change = as_float(row["observed_change_2018_2025"])
        assert abs((end - start) - change) < 1e-9

        robust = classification != "trajectory_not_robust"
        if indicator_id == "real_grdp_growth":
            assert robust is False, "M22 authorizes no robust geography-level real-GRDP growth trajectories"

        geography["indicators"][indicator_id] = {
            "label": meta["label"],
            "short_label": meta["short_label"],
            "unit": meta["unit"],
            "decimals": meta["decimals"],
            "observed_2018": start,
            "observed_2025": end,
            "observed_change": change,
            "trajectory_classification": classification,
            "trajectory_label": CLASSIFICATION_LABELS[classification],
            "trajectory_robust": robust,
            "hierarchical_slope_per_year": as_float(row["hierarchical_slope_per_year"]),
            "loo_min_slope_per_year": as_float(row["loo_min_slope_per_year"]),
            "loo_max_slope_per_year": as_float(row["loo_max_slope_per_year"]),
            "favorable_direction_semantics": row["favorable_direction_semantics"],
            "plain_favorable_semantics": meta["favorable_semantics"],
            "boundary": meta["boundary"],
            "source_claim_id": meta["source_claim_id"],
        }

    districts = sorted(by_geo.values(), key=lambda row: (row["administrative_type"], row["name"]))
    assert len(districts) == 19
    for district in districts:
        assert set(district["indicators"]) == set(INDICATORS)

    counts: dict[str, dict[str, int]] = {}
    for indicator_id in INDICATORS:
        counts[indicator_id] = {key: 0 for key in CLASSIFICATION_LABELS}
        for district in districts:
            classification = district["indicators"][indicator_id]["trajectory_classification"]
            counts[indicator_id][classification] += 1

    assert counts["labor_force_participation"] == {
        "persistent_increase": 17,
        "persistent_decrease": 0,
        "trajectory_not_robust": 2,
    }
    assert counts["unemployment_rate"] == {
        "persistent_increase": 5,
        "persistent_decrease": 11,
        "trajectory_not_robust": 3,
    }
    assert counts["real_grdp_growth"] == {
        "persistent_increase": 0,
        "persistent_decrease": 0,
        "trajectory_not_robust": 19,
    }
    assert counts["rice_yield"] == {
        "persistent_increase": 10,
        "persistent_decrease": 3,
        "trajectory_not_robust": 6,
    }

    return {
        "schema": "ranah-observatory/public-district-explorer/v1",
        "version": "0.1.0",
        "language": "id",
        "period": [2018, 2025],
        "geography_regime": "current_sumatera_barat_bps_19_kabupaten_kota",
        "source": {
            "path": "data/analysis/engine/hierarchical_trajectory_v1/m22-geography-trajectories.csv",
            "sha256": sha256_file(source),
            "source_milestone": 22,
            "claim_ids": [meta["source_claim_id"] for meta in INDICATORS.values()],
        },
        "interpretation": {
            "headline": "Pilih daerah untuk melihat perubahan 2018–2025 yang lolos disiplin trajectory M22.",
            "boundary": "Nilai awal/akhir adalah observasi sumber; klasifikasi trajectory berasal dari model hierarkis M22. Klasifikasi bukan sebab-akibat, bukan ranking, dan bukan forecast.",
            "not_qualified_for_hierarchical_explorer": [
                "expected_years_schooling",
                "mean_years_schooling",
                "poverty_rate",
            ],
        },
        "indicator_summary": [
            {
                "id": indicator_id,
                **meta,
                "classification_counts": counts[indicator_id],
            }
            for indicator_id, meta in INDICATORS.items()
        ],
        "districts": districts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build claim-bounded public M22 district explorer data")
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    payload = build(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "districts": len(payload["districts"]),
        "indicators": len(payload["indicator_summary"]),
        "source_sha256": payload["source"]["sha256"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
