#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data/analysis/quasi_causal/m8-real-grdp-panel-2005-2013-resolved.csv"
EXPOSURE = ROOT / "data/analysis/quasi_causal/m8-shakemap-exposure-candidate.csv"
DESIGN_GATE = ROOT / "data/manifests/milestone8_design_gate.json"
INFERENCE_PROTOCOL = ROOT / "research/MILESTONE8_INFERENCE_PROTOCOL.md"

MODEL_FRAME = ROOT / "data/analysis/quasi_causal/m8-event-study-model-frame.csv"
PRIMARY_OUTPUT = ROOT / "data/analysis/quasi_causal/m8-event-study-primary.csv"
INFLUENCE_OUTPUT = ROOT / "data/analysis/quasi_causal/m8-event-study-influence.csv"
SENSITIVITY_OUTPUT = ROOT / "data/analysis/quasi_causal/m8-event-study-exposure-sensitivity.csv"
MANIFEST = ROOT / "data/manifests/milestone8_event_study.json"

EVENT_TIMES = (-4, -3, -2, 0, 1, 2, 3, 4)
PRE_EVENT_TIMES = (-4, -3, -2)
POST_FULL_YEAR_EVENT_TIMES = (1, 2, 3, 4)
PRIMARY_EXPOSURE = "area_mean_pga_pct_g"
SENSITIVITY_EXPOSURES = (
    "area_median_pga_pct_g",
    "area_p90_pga_pct_g",
    "area_max_pga_pct_g",
    "area_mean_mmi",
)
NAMED_INFLUENCE = {
    "idn.13.1371": "Kota Padang",
    "idn.13.1306": "Padang Pariaman",
    "idn.13.1377": "Kota Pariaman",
}
EXPECTED_GEOGRAPHIES = {
    "idn.13.1301", "idn.13.1302", "idn.13.1303", "idn.13.1304", "idn.13.1305",
    "idn.13.1306", "idn.13.1307", "idn.13.1308", "idn.13.1309", "idn.13.1310",
    "idn.13.1311", "idn.13.1312", "idn.13.1371", "idn.13.1372", "idn.13.1373",
    "idn.13.1374", "idn.13.1375", "idn.13.1376", "idn.13.1377",
}


@dataclass(frozen=True)
class Fit:
    beta: np.ndarray
    residual: np.ndarray
    fitted: np.ndarray
    xtx_inv: np.ndarray
    cr1_cov: np.ndarray
    cr1_se: np.ndarray
    n: int
    p: int
    g: int
    rank: int
    correction: float


@dataclass(frozen=True)
class Design:
    y: np.ndarray
    x: np.ndarray
    columns: tuple[str, ...]
    cluster_codes: np.ndarray
    cluster_labels: tuple[str, ...]
    rows: tuple[dict[str, Any], ...]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def require_locked_gate() -> dict[str, Any]:
    gate = json.loads(DESIGN_GATE.read_text(encoding="utf-8"))
    required = {
        "schema": "ranah-observatory/milestone8-design-gate/v4",
        "criterion": "one focused causal or quasi-causal case study",
        "primary_outcome": "log_real_grdp_constant_2000",
        "primary_exposure": PRIMARY_EXPOSURE,
        "primary_exposure_standardized_form": "z(area_mean_pga_pct_g)",
        "primary_design": "continuous_intensity_two_way_fixed_effects_event_study",
        "baseline_year": 2008,
        "partial_treatment_year": 2009,
        "design_preregistered": True,
        "inference_protocol_locked_before_outcome_model_fit": True,
        "model_fit_authorized": True,
        "outcome_model_fit": False,
        "postperiod_source_anomalies_resolved": True,
        "full_exposure_19_geographies_frozen": True,
        "overlap_2009_reconciled": True,
        "causal_claim_authorized": False,
        "milestone8_complete": False,
    }
    for key, expected in required.items():
        if gate.get(key) != expected:
            raise RuntimeError(f"Milestone 8 model gate drift: {key} expected={expected!r} actual={gate.get(key)!r}")
    inference = {
        "wild_cluster_bootstrap_distribution": "rademacher",
        "wild_cluster_bootstrap_draws": 1999,
        "wild_cluster_bootstrap_seed": 20090930,
        "pretrend_joint_pvalue_minimum": 0.10,
        "pretrend_max_absolute_log_point_coefficient": 0.10,
        "placebo_pvalue_minimum": 0.10,
        "placebo_max_absolute_log_point_coefficient": 0.10,
        "named_influence_max_absolute_log_point_change": 0.10,
    }
    for key, expected in inference.items():
        if gate.get(key) != expected:
            raise RuntimeError(f"Milestone 8 inference gate drift: {key}")
    if not INFERENCE_PROTOCOL.exists():
        raise RuntimeError("locked Milestone 8 inference protocol is missing")
    return gate


def load_inputs() -> tuple[list[dict[str, Any]], dict[str, dict[str, float]], dict[str, Any]]:
    gate = require_locked_gate()
    raw_panel = read_csv(PANEL)
    raw_exposure = read_csv(EXPOSURE)
    if len(raw_panel) != 171:
        raise RuntimeError(f"resolved panel cardinality drift: {len(raw_panel)}")
    if len(raw_exposure) != 19:
        raise RuntimeError(f"exposure cardinality drift: {len(raw_exposure)}")

    exposure_by_gid: dict[str, dict[str, float]] = {}
    for row in raw_exposure:
        gid = row["geography_id"]
        if gid in exposure_by_gid:
            raise RuntimeError(f"duplicate exposure geography {gid}")
        exposure_by_gid[gid] = {
            name: float(row[name]) for name in (PRIMARY_EXPOSURE, *SENSITIVITY_EXPOSURES)
        }
    if set(exposure_by_gid) != EXPECTED_GEOGRAPHIES:
        raise RuntimeError("exposure geography footprint drift")

    z_by_exposure: dict[str, dict[str, float]] = {}
    for exposure_name in (PRIMARY_EXPOSURE, *SENSITIVITY_EXPOSURES):
        values = np.array([exposure_by_gid[gid][exposure_name] for gid in sorted(EXPECTED_GEOGRAPHIES)], dtype=float)
        if not np.isfinite(values).all():
            raise RuntimeError(f"nonfinite exposure values: {exposure_name}")
        mean = float(values.mean())
        sd = float(values.std(ddof=0))
        if not sd > 0:
            raise RuntimeError(f"zero exposure SD: {exposure_name}")
        z_by_exposure[exposure_name] = {
            gid: (exposure_by_gid[gid][exposure_name] - mean) / sd for gid in EXPECTED_GEOGRAPHIES
        }

    panel_rows: list[dict[str, Any]] = []
    keys: set[tuple[str, int]] = set()
    for row in raw_panel:
        gid = row["geography_id"]
        year = int(row["year"])
        key = (gid, year)
        if key in keys:
            raise RuntimeError(f"duplicate resolved-panel key {key}")
        keys.add(key)
        value = float(row["real_grdp_constant_2000_million_rupiah"])
        logged = float(row["log_real_grdp"])
        if gid not in EXPECTED_GEOGRAPHIES or year not in range(2005, 2014):
            raise RuntimeError(f"unexpected resolved-panel key {key}")
        if not (math.isfinite(value) and value > 0 and math.isfinite(logged)):
            raise RuntimeError(f"invalid resolved outcome {key}")
        if abs(logged - math.log(value)) > 1e-10:
            raise RuntimeError(f"resolved outcome/log mismatch {key}")
        if row.get("source_internal_consistency_status") == "postperiod_level_growth_internal_mismatch_unresolved":
            raise RuntimeError(f"unresolved source inconsistency leaked into model frame {key}")
        parsed: dict[str, Any] = dict(row)
        parsed["year"] = year
        parsed["event_time"] = year - 2009
        parsed["real_grdp_constant_2000_million_rupiah"] = value
        parsed["log_real_grdp"] = logged
        for exposure_name in (PRIMARY_EXPOSURE, *SENSITIVITY_EXPOSURES):
            parsed[exposure_name] = exposure_by_gid[gid][exposure_name]
            parsed[f"z_{exposure_name}"] = z_by_exposure[exposure_name][gid]
        panel_rows.append(parsed)

    if len(keys) != 171 or {gid for gid, _year in keys} != EXPECTED_GEOGRAPHIES:
        raise RuntimeError("resolved model frame footprint drift")
    for gid in EXPECTED_GEOGRAPHIES:
        if {year for geography, year in keys if geography == gid} != set(range(2005, 2014)):
            raise RuntimeError(f"incomplete model years for {gid}")
    panel_rows.sort(key=lambda row: (row["geography_id"], row["year"]))
    return panel_rows, z_by_exposure, gate


def encode_clusters(rows: Iterable[dict[str, Any]]) -> tuple[np.ndarray, tuple[str, ...]]:
    labels = tuple(sorted({str(row["geography_id"]) for row in rows}))
    index = {label: position for position, label in enumerate(labels)}
    codes = np.array([index[str(row["geography_id"])] for row in rows], dtype=int)
    return codes, labels


def event_design(
    all_rows: list[dict[str, Any]],
    exposure_name: str,
    excluded_geographies: set[str] | None = None,
) -> Design:
    excluded = excluded_geographies or set()
    rows = [row for row in all_rows if row["geography_id"] not in excluded]
    rows.sort(key=lambda row: (row["geography_id"], row["year"]))
    gids = sorted({str(row["geography_id"]) for row in rows})
    years = sorted({int(row["year"]) for row in rows})
    if years != list(range(2005, 2014)):
        raise RuntimeError(f"event-study year footprint drift after exclusions: {years}")
    if len(gids) < 2:
        raise RuntimeError("event-study requires multiple geographies")

    columns = ["intercept"]
    columns.extend(f"geo:{gid}" for gid in gids[1:])
    columns.extend(f"year:{year}" for year in years[1:])
    columns.extend(f"event:{event_time}" for event_time in EVENT_TIMES)

    x = np.zeros((len(rows), len(columns)), dtype=float)
    y = np.array([float(row["log_real_grdp"]) for row in rows], dtype=float)
    x[:, 0] = 1.0
    column_index = {name: idx for idx, name in enumerate(columns)}
    for obs_index, row in enumerate(rows):
        gid = str(row["geography_id"])
        year = int(row["year"])
        event_time = int(row["event_time"])
        if gid != gids[0]:
            x[obs_index, column_index[f"geo:{gid}"]] = 1.0
        if year != years[0]:
            x[obs_index, column_index[f"year:{year}"]] = 1.0
        if event_time in EVENT_TIMES:
            x[obs_index, column_index[f"event:{event_time}"]] = float(row[f"z_{exposure_name}"])
    clusters, cluster_labels = encode_clusters(rows)
    return Design(y=y, x=x, columns=tuple(columns), cluster_codes=clusters, cluster_labels=cluster_labels, rows=tuple(rows))


def placebo_design(all_rows: list[dict[str, Any]]) -> Design:
    rows = [row for row in all_rows if int(row["year"]) <= 2008]
    rows.sort(key=lambda row: (row["geography_id"], row["year"]))
    gids = sorted({str(row["geography_id"]) for row in rows})
    years = sorted({int(row["year"]) for row in rows})
    if years != [2005, 2006, 2007, 2008] or len(gids) != 19:
        raise RuntimeError("placebo frame must be exact 19 x 2005-2008")
    columns = ["intercept"]
    columns.extend(f"geo:{gid}" for gid in gids[1:])
    columns.extend(f"year:{year}" for year in years[1:])
    columns.append("placebo:post_2007")
    index = {name: pos for pos, name in enumerate(columns)}
    x = np.zeros((len(rows), len(columns)), dtype=float)
    y = np.array([float(row["log_real_grdp"]) for row in rows], dtype=float)
    x[:, 0] = 1.0
    for obs_index, row in enumerate(rows):
        gid = str(row["geography_id"])
        year = int(row["year"])
        if gid != gids[0]:
            x[obs_index, index[f"geo:{gid}"]] = 1.0
        if year != years[0]:
            x[obs_index, index[f"year:{year}"]] = 1.0
        if year >= 2007:
            x[obs_index, index["placebo:post_2007"]] = float(row[f"z_{PRIMARY_EXPOSURE}"])
    clusters, cluster_labels = encode_clusters(rows)
    return Design(y=y, x=x, columns=tuple(columns), cluster_codes=clusters, cluster_labels=cluster_labels, rows=tuple(rows))


def cluster_scores(x: np.ndarray, residual: np.ndarray, cluster_codes: np.ndarray, g: int) -> list[np.ndarray]:
    return [x[cluster_codes == cluster].T @ residual[cluster_codes == cluster] for cluster in range(g)]


def fit_ols(design: Design) -> Fit:
    x, y = design.x, design.y
    n, p = x.shape
    rank = int(np.linalg.matrix_rank(x))
    if rank != p:
        raise RuntimeError(f"design matrix is rank deficient: rank={rank} p={p}")
    xtx_inv = np.linalg.inv(x.T @ x)
    beta = xtx_inv @ x.T @ y
    fitted = x @ beta
    residual = y - fitted
    g = len(design.cluster_labels)
    if g <= 1 or n <= p:
        raise RuntimeError(f"invalid CR1 dimensions n={n} p={p} g={g}")
    correction = (g / (g - 1.0)) * ((n - 1.0) / (n - p))
    meat = np.zeros((p, p), dtype=float)
    for score in cluster_scores(x, residual, design.cluster_codes, g):
        meat += np.outer(score, score)
    cov = xtx_inv @ meat @ xtx_inv * correction
    diagonal = np.diag(cov)
    if np.any(diagonal < -1e-12):
        raise RuntimeError("CR1 covariance has materially negative diagonal")
    se = np.sqrt(np.maximum(diagonal, 0.0))
    return Fit(
        beta=beta,
        residual=residual,
        fitted=fitted,
        xtx_inv=xtx_inv,
        cr1_cov=cov,
        cr1_se=se,
        n=n,
        p=p,
        g=g,
        rank=rank,
        correction=float(correction),
    )


def restricted_fit(design: Design, drop_indices: tuple[int, ...]) -> tuple[np.ndarray, np.ndarray]:
    keep = [idx for idx in range(design.x.shape[1]) if idx not in set(drop_indices)]
    x_restricted = design.x[:, keep]
    rank = int(np.linalg.matrix_rank(x_restricted))
    if rank != x_restricted.shape[1]:
        raise RuntimeError("restricted design matrix is rank deficient")
    beta = np.linalg.solve(x_restricted.T @ x_restricted, x_restricted.T @ design.y)
    fitted = x_restricted @ beta
    return fitted, design.y - fitted


def coefficient_cr1_se(
    x: np.ndarray,
    residual: np.ndarray,
    xtx_inv: np.ndarray,
    cluster_codes: np.ndarray,
    g: int,
    correction: float,
    coefficient_index: int,
) -> float:
    row = xtx_inv[coefficient_index, :]
    variance = 0.0
    for score in cluster_scores(x, residual, cluster_codes, g):
        projected = float(row @ score)
        variance += projected * projected
    variance *= correction
    return math.sqrt(max(variance, 0.0))


def subcovariance_cr1(
    x: np.ndarray,
    residual: np.ndarray,
    xtx_inv: np.ndarray,
    cluster_codes: np.ndarray,
    g: int,
    correction: float,
    indices: tuple[int, ...],
) -> np.ndarray:
    rows = xtx_inv[np.array(indices), :]
    covariance = np.zeros((len(indices), len(indices)), dtype=float)
    for score in cluster_scores(x, residual, cluster_codes, g):
        projected = rows @ score
        covariance += np.outer(projected, projected)
    covariance *= correction
    return covariance


def bootstrap_weights(draws: int, seed: int, clusters: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    raw = rng.integers(0, 2, size=(draws, clusters), endpoint=False)
    return np.where(raw == 0, -1.0, 1.0)


def coefficient_wild_cluster_pvalue(
    design: Design,
    full_fit: Fit,
    coefficient_index: int,
    weights: np.ndarray,
) -> dict[str, Any]:
    fitted_null, residual_null = restricted_fit(design, (coefficient_index,))
    observed_se = float(full_fit.cr1_se[coefficient_index])
    if not observed_se > 0:
        raise RuntimeError(f"zero observed CR1 SE for {design.columns[coefficient_index]}")
    observed_t = float(full_fit.beta[coefficient_index] / observed_se)
    a = full_fit.xtx_inv @ design.x.T
    extreme = 0
    finite_draws = 0
    for draw in range(weights.shape[0]):
        observation_weights = weights[draw, design.cluster_codes]
        y_star = fitted_null + residual_null * observation_weights
        beta_star = a @ y_star
        residual_star = y_star - design.x @ beta_star
        se_star = coefficient_cr1_se(
            design.x,
            residual_star,
            full_fit.xtx_inv,
            design.cluster_codes,
            full_fit.g,
            full_fit.correction,
            coefficient_index,
        )
        if not (math.isfinite(se_star) and se_star > 0):
            continue
        t_star = float(beta_star[coefficient_index] / se_star)
        if not math.isfinite(t_star):
            continue
        finite_draws += 1
        if abs(t_star) >= abs(observed_t) - 1e-15:
            extreme += 1
    if finite_draws != weights.shape[0]:
        raise RuntimeError(
            f"nonfinite wild-bootstrap draws for {design.columns[coefficient_index]}: "
            f"finite={finite_draws} total={weights.shape[0]}"
        )
    return {
        "observed_t": observed_t,
        "extreme_draw_count": extreme,
        "finite_draw_count": finite_draws,
        "p_value": (extreme + 1.0) / (finite_draws + 1.0),
    }


def joint_pretrend_wild_cluster_pvalue(
    design: Design,
    full_fit: Fit,
    indices: tuple[int, ...],
    weights: np.ndarray,
) -> dict[str, Any]:
    observed_beta = full_fit.beta[np.array(indices)]
    observed_cov = full_fit.cr1_cov[np.ix_(indices, indices)]
    observed_cov_rank = int(np.linalg.matrix_rank(observed_cov))
    if observed_cov_rank != len(indices):
        raise RuntimeError(f"observed pretrend covariance is rank deficient: {observed_cov_rank}")
    observed_wald = float(observed_beta.T @ np.linalg.inv(observed_cov) @ observed_beta)

    fitted_null, residual_null = restricted_fit(design, indices)
    a = full_fit.xtx_inv @ design.x.T
    extreme = 0
    finite_draws = 0
    singular_draws = 0
    for draw in range(weights.shape[0]):
        y_star = fitted_null + residual_null * weights[draw, design.cluster_codes]
        beta_star = a @ y_star
        residual_star = y_star - design.x @ beta_star
        covariance_star = subcovariance_cr1(
            design.x,
            residual_star,
            full_fit.xtx_inv,
            design.cluster_codes,
            full_fit.g,
            full_fit.correction,
            indices,
        )
        if np.linalg.matrix_rank(covariance_star) != len(indices):
            singular_draws += 1
            continue
        beta_sub = beta_star[np.array(indices)]
        wald_star = float(beta_sub.T @ np.linalg.inv(covariance_star) @ beta_sub)
        if not math.isfinite(wald_star):
            continue
        finite_draws += 1
        if wald_star >= observed_wald - 1e-15:
            extreme += 1
    if finite_draws != weights.shape[0]:
        raise RuntimeError(
            f"joint pretrend bootstrap did not retain all draws: finite={finite_draws} "
            f"singular={singular_draws} total={weights.shape[0]}"
        )
    return {
        "observed_wald": observed_wald,
        "observed_covariance_rank": observed_cov_rank,
        "restriction_count": len(indices),
        "extreme_draw_count": extreme,
        "finite_draw_count": finite_draws,
        "singular_draw_count": singular_draws,
        "p_value": (extreme + 1.0) / (finite_draws + 1.0),
    }


def event_results(design: Design, fit: Fit, weights: np.ndarray) -> tuple[list[dict[str, Any]], dict[int, int]]:
    index_by_event = {event_time: design.columns.index(f"event:{event_time}") for event_time in EVENT_TIMES}
    rows: list[dict[str, Any]] = []
    for event_time in EVENT_TIMES:
        idx = index_by_event[event_time]
        bootstrap = coefficient_wild_cluster_pvalue(design, fit, idx, weights)
        beta = float(fit.beta[idx])
        se = float(fit.cr1_se[idx])
        rows.append(
            {
                "event_time": event_time,
                "calendar_year": 2009 + event_time,
                "period_class": (
                    "pre_event" if event_time < -1 else
                    "omitted_baseline" if event_time == -1 else
                    "partial_treatment_year" if event_time == 0 else
                    "full_post_event_year"
                ),
                "coefficient_log_points_per_1sd_pga": beta,
                "cr1_cluster_se": se,
                "cr1_t": bootstrap["observed_t"],
                "wild_cluster_bootstrap_p_value": bootstrap["p_value"],
                "wild_cluster_extreme_draw_count": bootstrap["extreme_draw_count"],
                "wild_cluster_draw_count": bootstrap["finite_draw_count"],
            }
        )
    return rows, index_by_event


def influence_results(
    all_rows: list[dict[str, Any]],
    full_coefficients: dict[int, float],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    output: list[dict[str, Any]] = []
    named_max = 0.0
    named_failures: list[dict[str, Any]] = []
    for gid in sorted(EXPECTED_GEOGRAPHIES):
        design = event_design(all_rows, PRIMARY_EXPOSURE, {gid})
        fit = fit_ols(design)
        excluded_name = next(str(row["geography_name"]) for row in all_rows if row["geography_id"] == gid)
        named = gid in NAMED_INFLUENCE
        for event_time in EVENT_TIMES:
            idx = design.columns.index(f"event:{event_time}")
            beta = float(fit.beta[idx])
            change = beta - full_coefficients[event_time]
            row = {
                "excluded_geography_id": gid,
                "excluded_geography_name": excluded_name,
                "named_influence_gate_geography": named,
                "event_time": event_time,
                "calendar_year": 2009 + event_time,
                "coefficient_log_points_per_1sd_pga": beta,
                "full_sample_coefficient": full_coefficients[event_time],
                "change_from_full_sample": change,
                "absolute_change_from_full_sample": abs(change),
            }
            output.append(row)
            if named and event_time in POST_FULL_YEAR_EVENT_TIMES:
                named_max = max(named_max, abs(change))
                if abs(change) > 0.10:
                    named_failures.append(row)
    return output, {
        "named_geographies": NAMED_INFLUENCE,
        "threshold_log_points": 0.10,
        "max_absolute_change_2010_2013": named_max,
        "failure_count": len(named_failures),
        "failures": named_failures,
        "passed": len(named_failures) == 0,
    }


def sensitivity_results(all_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for exposure_name in SENSITIVITY_EXPOSURES:
        design = event_design(all_rows, exposure_name)
        fit = fit_ols(design)
        for event_time in EVENT_TIMES:
            idx = design.columns.index(f"event:{event_time}")
            output.append(
                {
                    "exposure": exposure_name,
                    "event_time": event_time,
                    "calendar_year": 2009 + event_time,
                    "coefficient_log_points_per_1sd_exposure": float(fit.beta[idx]),
                    "cr1_cluster_se": float(fit.cr1_se[idx]),
                }
            )
    return output


def build_model_frame(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = [
        "geography_id", "geography_name", "year", "event_time",
        "real_grdp_constant_2000_million_rupiah", "log_real_grdp",
        PRIMARY_EXPOSURE, f"z_{PRIMARY_EXPOSURE}",
        *SENSITIVITY_EXPOSURES,
        *(f"z_{name}" for name in SENSITIVITY_EXPOSURES),
        "source_block", "source_table", "source_pdf_page", "revision_status",
        "source_internal_consistency_status", "source_anomaly_resolution_status",
        "source_anomaly_resolution_source",
    ]
    return [{field: row.get(field, "") for field in fields} for row in rows]


def main() -> int:
    all_rows, _z_by_exposure, gate = load_inputs()
    draws = int(gate["wild_cluster_bootstrap_draws"])
    seed = int(gate["wild_cluster_bootstrap_seed"])

    primary_design = event_design(all_rows, PRIMARY_EXPOSURE)
    primary_fit = fit_ols(primary_design)
    weights = bootstrap_weights(draws, seed, primary_fit.g)
    primary_rows, index_by_event = event_results(primary_design, primary_fit, weights)
    full_coefficients = {int(row["event_time"]): float(row["coefficient_log_points_per_1sd_pga"]) for row in primary_rows}

    pre_indices = tuple(index_by_event[event_time] for event_time in PRE_EVENT_TIMES)
    pretrend_joint = joint_pretrend_wild_cluster_pvalue(primary_design, primary_fit, pre_indices, weights)
    max_abs_pre = max(abs(full_coefficients[event_time]) for event_time in PRE_EVENT_TIMES)
    pretrend_passed = (
        float(pretrend_joint["p_value"]) >= float(gate["pretrend_joint_pvalue_minimum"])
        and max_abs_pre <= float(gate["pretrend_max_absolute_log_point_coefficient"])
    )

    placebo = placebo_design(all_rows)
    placebo_fit = fit_ols(placebo)
    placebo_idx = placebo.columns.index("placebo:post_2007")
    placebo_bootstrap = coefficient_wild_cluster_pvalue(placebo, placebo_fit, placebo_idx, weights)
    placebo_beta = float(placebo_fit.beta[placebo_idx])
    placebo_passed = (
        float(placebo_bootstrap["p_value"]) >= float(gate["placebo_pvalue_minimum"])
        and abs(placebo_beta) <= float(gate["placebo_max_absolute_log_point_coefficient"])
    )

    influence_rows, influence_gate = influence_results(all_rows, full_coefficients)
    sensitivity_rows = sensitivity_results(all_rows)

    model_frame_rows = build_model_frame(all_rows)
    model_frame_fields = list(model_frame_rows[0])
    write_csv(MODEL_FRAME, model_frame_rows, model_frame_fields)
    write_csv(PRIMARY_OUTPUT, primary_rows, list(primary_rows[0]))
    write_csv(INFLUENCE_OUTPUT, influence_rows, list(influence_rows[0]))
    write_csv(SENSITIVITY_OUTPUT, sensitivity_rows, list(sensitivity_rows[0]))

    core_identification_diagnostics_passed = pretrend_passed and placebo_passed and bool(influence_gate["passed"])
    manifest = {
        "schema": "ranah-observatory/milestone8-event-study/v1",
        "criterion": "one focused causal or quasi-causal case study",
        "case_study": "2009 West Sumatra earthquake differential economic trajectory",
        "outcome": "log_real_grdp_constant_2000",
        "primary_exposure": PRIMARY_EXPOSURE,
        "primary_exposure_scale": "one population-SD across fixed 19-geography exposure universe",
        "exposure_standardization_ddof": 0,
        "event_year": 2009,
        "baseline_year": 2008,
        "partial_treatment_year": 2009,
        "event_times_estimated": list(EVENT_TIMES),
        "geography_count": 19,
        "year_count": 9,
        "observation_count": 171,
        "primary_design": {
            "n": primary_fit.n,
            "p": primary_fit.p,
            "cluster_count": primary_fit.g,
            "matrix_rank": primary_fit.rank,
            "cr1_finite_sample_correction": primary_fit.correction,
            "geography_fixed_effects": True,
            "year_fixed_effects": True,
            "covariate_search_performed": False,
        },
        "wild_cluster_bootstrap": {
            "distribution": "rademacher",
            "draws": draws,
            "seed": seed,
            "cluster": "geography",
            "null_imposed": True,
            "test_statistic": "CR1_studentized_t for coefficient tests; CR1 Wald for joint pretrend",
            "add_one_pvalue_correction": True,
        },
        "pretrend": {
            "event_times": list(PRE_EVENT_TIMES),
            "joint_wild_cluster_bootstrap_p_value": pretrend_joint["p_value"],
            "joint_observed_wald": pretrend_joint["observed_wald"],
            "joint_restriction_count": pretrend_joint["restriction_count"],
            "max_absolute_pre_coefficient_log_points": max_abs_pre,
            "pvalue_minimum_gate": float(gate["pretrend_joint_pvalue_minimum"]),
            "max_absolute_coefficient_gate": float(gate["pretrend_max_absolute_log_point_coefficient"]),
            "passed": pretrend_passed,
            "note": "Passing is only a screening condition and does not prove parallel trends.",
        },
        "placebo": {
            "sample_years": [2005, 2006, 2007, 2008],
            "pseudo_event_year": 2007,
            "coefficient_log_points_per_1sd_pga": placebo_beta,
            "cr1_cluster_se": float(placebo_fit.cr1_se[placebo_idx]),
            "cr1_t": placebo_bootstrap["observed_t"],
            "wild_cluster_bootstrap_p_value": placebo_bootstrap["p_value"],
            "pvalue_minimum_gate": float(gate["placebo_pvalue_minimum"]),
            "max_absolute_coefficient_gate": float(gate["placebo_max_absolute_log_point_coefficient"]),
            "passed": placebo_passed,
        },
        "influence": influence_gate,
        "exposure_sensitivity": {
            "exposures": list(SENSITIVITY_EXPOSURES),
            "all_reported_without_significance_selection": True,
            "wild_bootstrap_not_repeated_for_sensitivity_models": True,
            "purpose": "pre-specified point-estimate stability diagnostics",
        },
        "core_identification_diagnostics_passed": core_identification_diagnostics_passed,
        "housing_damage_validation_complete": False,
        "grdp_growth_robustness_complete": False,
        "small_cluster_inference_implemented": True,
        "outcome_model_fit": True,
        "quasi_causal_effect_estimated": False,
        "causal_claim_authorized": False,
        "claim_classification": (
            "quasi_causal_candidate_pending_remaining_required_diagnostics"
            if core_identification_diagnostics_passed
            else "association_or_failed_identification_pending_remaining_diagnostics"
        ),
        "model_frame_path": str(MODEL_FRAME.relative_to(ROOT)),
        "model_frame_sha256": sha256(MODEL_FRAME),
        "primary_output_path": str(PRIMARY_OUTPUT.relative_to(ROOT)),
        "primary_output_sha256": sha256(PRIMARY_OUTPUT),
        "influence_output_path": str(INFLUENCE_OUTPUT.relative_to(ROOT)),
        "influence_output_sha256": sha256(INFLUENCE_OUTPUT),
        "sensitivity_output_path": str(SENSITIVITY_OUTPUT.relative_to(ROOT)),
        "sensitivity_output_sha256": sha256(SENSITIVITY_OUTPUT),
        "resolved_panel_path": str(PANEL.relative_to(ROOT)),
        "resolved_panel_sha256": sha256(PANEL),
        "exposure_path": str(EXPOSURE.relative_to(ROOT)),
        "exposure_sha256": sha256(EXPOSURE),
        "design_gate_path": str(DESIGN_GATE.relative_to(ROOT)),
        "design_gate_sha256": sha256(DESIGN_GATE),
        "inference_protocol_path": str(INFERENCE_PROTOCOL.relative_to(ROOT)),
        "inference_protocol_sha256": sha256(INFERENCE_PROTOCOL),
        "milestone8_complete": False,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
