#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/manifests/milestone19_dynamic_forecast_engine.json"
OUT_DIR = ROOT / "data/analysis/engine/dynamic_forecast_v1"
SPEC = ROOT / "research/MILESTONE19_DYNAMIC_FORECAST_ENGINE_SPEC.md"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("schema") != "ranah-observatory/milestone19-dynamic-forecast-engine/v1":
        raise SystemExit("unexpected M19 manifest schema")
    if manifest.get("milestone19_complete") is not True:
        raise SystemExit("M19 incomplete")
    if manifest.get("strictly_out_of_time_backtest") is not True:
        raise SystemExit("M19 backtest is not strictly out-of-time")
    if manifest.get("posthoc_algorithm_search_performed") is not False:
        raise SystemExit("M19 posthoc algorithm search boundary violated")
    if manifest.get("causal_claim_authorized") is not False:
        raise SystemExit("M19 causal claim boundary violated")
    if manifest.get("policy_counterfactual_authorized") is not False:
        raise SystemExit("M19 policy counterfactual boundary violated")
    if manifest.get("forecast_is_guaranteed_future") is not False:
        raise SystemExit("M19 forecast guarantee boundary violated")

    expected_outputs = {
        "model_frame": "m19-model-frame.csv",
        "backtest_predictions": "m19-backtest-predictions.csv",
        "target_summary": "m19-target-summary.csv",
        "coefficients": "m19-outer-fold-coefficients.csv",
        "forecast_2026": "m19-forecast-2026.csv",
    }
    for key, filename in expected_outputs.items():
        entry = manifest["outputs"][key]
        path = ROOT / entry["path"]
        if path != OUT_DIR / filename:
            raise SystemExit(f"unexpected output path for {key}")
        if sha256(path) != entry["sha256"]:
            raise SystemExit(f"hash drift for {key}")

    frame = read_csv(OUT_DIR / "m19-model-frame.csv")
    backtest = read_csv(OUT_DIR / "m19-backtest-predictions.csv")
    summary = read_csv(OUT_DIR / "m19-target-summary.csv")
    forecast = read_csv(OUT_DIR / "m19-forecast-2026.csv")

    if len(frame) != 133 or len(backtest) != 285 or len(summary) != 3 or len(forecast) != 57:
        raise SystemExit("M19 output footprint drift")
    if {int(row["forecast_year"]) for row in backtest} != {2021, 2022, 2023, 2024, 2025}:
        raise SystemExit("M19 outer forecast-year drift")
    if not all(row["strictly_out_of_time"] == "True" for row in backtest):
        raise SystemExit("M19 row-level temporal flag failure")
    if not all(int(row["training_end_year"]) < int(row["forecast_year"]) for row in backtest):
        raise SystemExit("M19 temporal leakage detected")

    target_qualification: dict[str, bool] = {}
    for row in summary:
        qualified = row["forecast_qualified"] == "True"
        expected = (
            float(row["dynamic_ridge_rmse"]) < float(row["persistence_rmse"])
            and float(row["dynamic_ridge_mae"]) < float(row["persistence_mae"])
        )
        if qualified != expected:
            raise SystemExit(f"qualification drift for {row['target_id']}")
        target_qualification[row["target_id"]] = qualified

    for row in forecast:
        target = row["target_id"]
        authorized = row["public_substantive_use_authorized"] == "True"
        if authorized != target_qualification[target]:
            raise SystemExit(f"public authorization drift for {target}")
        if int(row["forecast_year"]) != 2026 or int(row["information_cutoff_year"]) != 2025:
            raise SystemExit("M19 final forecast cutoff drift")
        if row["claim_type"] != "one_year_ahead_model_forecast_not_causal":
            raise SystemExit("M19 claim type drift")

    spec = SPEC.read_text(encoding="utf-8").lower()
    required_guards = [
        "predictive, not causal",
        "post hoc",
        "persistence",
        "substantive public forecast use is authorized only when",
    ]
    for guard in required_guards:
        if guard not in spec:
            raise SystemExit(f"missing M19 spec guardrail: {guard}")

    print(json.dumps({
        "milestone19_audit": "passed",
        "forecast_qualified_target_ids": manifest["forecast_qualified_target_ids"],
        "forecast_blocked_target_ids": manifest["forecast_blocked_target_ids"],
        "backtest_prediction_count": len(backtest),
    }, indent=2))


if __name__ == "__main__":
    main()
