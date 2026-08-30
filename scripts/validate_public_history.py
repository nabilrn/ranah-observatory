from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from build_public_history import DEFAULT_OUTPUT, SOURCE_PATHS, build_payload


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError(f"expected object JSON: {path}")
    return payload


def validate(path: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    frozen = load_json(path)
    rebuilt = build_payload()
    assert frozen == rebuilt, "site/data/history.json drifted from canonical historical manifests"

    assert frozen["schema"] == "ranah-observatory/public-history/v1"
    assert frozen["language"] == "id"
    assert frozen["source_paths"] == SOURCE_PATHS

    cards = {card["id"]: card for card in frozen["cards"]}
    assert set(cards) == {
        "construction-annual-2002-2006",
        "construction-se06-2006",
        "construction-qualification-bridge",
    }

    annual = cards["construction-annual-2002-2006"]
    assert [(row["year"], row["value"]) for row in annual["series"]] == [
        (2002, 2779),
        (2003, 2882),
        (2004, 2837),
        (2005, 2435),
        (2006, 2664),
    ]
    assert annual["key_fact"] == {
        "label": "Perubahan 2003 → 2005",
        "value": -447,
        "percent": -15.510062,
    }

    same_year = cards["construction-se06-2006"]["comparison"]
    assert same_year["annual_survey"] == 2664
    assert same_year["se06_full_listing"] == 4504
    assert same_year["se06_legal"] == 1379
    assert same_year["se06_nonlegal"] == 3125
    assert same_year["annual_percent_of_listing"] == 59.147425

    qualification = cards["construction-qualification-bridge"]
    assert qualification["qualification_2003"] == {
        "B": 0,
        "M1": 16,
        "M2": 134,
        "K1": 334,
        "K2": 1084,
        "K3": 1314,
        "total": 2882,
    }
    assert qualification["arithmetic_candidate_2003"] == {
        "Kecil": 2732,
        "Menengah": 150,
        "Besar": 0,
        "Jumlah": 2882,
    }
    assert qualification["total_2005"] == 2435
    assert qualification["component_values_2005_recovered"] is False
    assert qualification["semantic_mapping_verified"] is False

    authorizations = frozen["authorizations"]
    assert authorizations["historical_context_display"] is True
    for key, value in authorizations.items():
        if key != "historical_context_display":
            assert value is False, key

    copy = json.dumps(frozen, ensure_ascii=False).casefold()
    for token in (
        "bukan",
        "tidak boleh",
        "belum",
        "sampling frame",
        "bridge/backcast",
        "kausal",
        "panel v3",
    ):
        assert token in copy, f"public history lost boundary token: {token}"

    return {
        "cards": len(cards),
        "annual_points": len(annual["series"]),
        "historical_context_display": True,
        "harmonized_series_authorized": False,
        "causal_claim_authorized": False,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
