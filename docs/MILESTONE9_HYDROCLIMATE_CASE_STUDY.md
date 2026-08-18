# Milestone 9 — 2024 West Sumatra Hydroclimate Disaster Case Study

## Result in one sentence

All 19 West Sumatra kabupaten/kota were wetter in 2024 than their own 1981–2023 CHIRPS annual-rainfall baseline, yet the cross-sectional spatial association between relative annual wetness and officially recorded BNPB disaster counts was weak: flood counts were weakly negative while landslide counts were weakly positive.

This is a **descriptive climate/disaster case study**, not a causal rainfall-attribution study.

## Why 2024

The study year was selected before inspecting the rainfall/disaster association. The qualified BNPB foundation currently provides one exact 19-geography, independently cross-checked disaster-type footprint: 2024 flood (`BANJIR`) and landslide (`TANAH LONGSOR`) event counts. Earlier 2010–2024 data in the current source contract are total-disaster context rather than a disaster-type-by-year-by-kabupaten cube.

The selection rule is recorded in `research/MILESTONE9_HYDROCLIMATE_CASE_STUDY_SPEC.md` and `data/manifests/milestone9_design_gate.json`.

## Evidence layers

### Rainfall

CHIRPS v3 Final monthly materialized to annual rainfall for 19 fixed-current-boundary BIG June-2026 kabupaten/kota polygons.

- coverage: 1981–2025;
- observations: 855;
- claim type: `model_estimate`;
- study baseline: 1981–2023, 43 years;
- independent BMKG station validation: pending;
- no station-observation equivalence is claimed.

The primary climate measure is each geography's 2024 annual rainfall z-score relative to its own 1981–2023 distribution.

### Recorded disasters

BNPB Satu Data 2024 independently cross-checked event-by-type resources.

- 19 geographies × 2 indicators = 38 canonical observations;
- indicators: `flood_events`, `landslide_events`;
- evidence: observed recorded-event counts;
- zero-event geographies are retained;
- reported event counts may reflect classification and reporting practice.

`hydroclimate_event_count = flood_events + landslide_events` is reported only as a derived summary.

## 2024 rainfall context

Every geography has a positive annual rainfall anomaly versus its 1981–2023 mean.

- positive-anomaly geographies: **19 / 19**;
- highest relative anomaly: **Pasaman Barat**, z ≈ **1.708**;
- lowest relative anomaly: **Solok Selatan**, z ≈ **0.861** — still wetter than its historical mean;
- Kepulauan Mentawai and Pasaman Barat reached the top of their baseline empirical distribution under the preregistered percentile rule.

The absolute wettest annual total is not identical to the largest standardized anomaly because each geography has a different rainfall climatology and variability. For example, coastal/western areas can have much higher absolute rainfall while a lower standardized anomaly than a normally drier geography.

## Recorded disaster pattern

The 2024 BNPB event counts are highly uneven across the 19 geographies.

- maximum recorded flood count: **15** in Pesisir Selatan;
- next-highest prominent count: **8** in Dharmasraya;
- maximum recorded landslide count: **3** in Padang Pariaman;
- many geographies record zero landslides under this annual BNPB resource.

A zero in this table means zero events in the qualified BNPB annual category field. It does not prove that no local slope failure, inundation, or unrecorded incident occurred.

## Preregistered association results

Primary climate metric: 2024 rainfall z-score relative to 1981–2023.

| Disaster metric | Pearson | Spearman |
|---|---:|---:|
| Flood events | −0.263 | −0.184 |
| Landslide events | +0.264 | +0.221 |
| Flood + landslide derived count | −0.183 | −0.146 |

Sensitivity using raw 2024 annual rainfall instead of within-geography standardized anomaly remains weak:

| Disaster metric | Pearson | Spearman |
|---|---:|---:|
| Flood events | −0.139 | −0.074 |
| Landslide events | +0.220 | +0.199 |
| Flood + landslide derived count | −0.074 | +0.035 |

No significance threshold was selected after seeing these results. The case study is intended to diagnose spatial alignment, not to produce a causal coefficient.

## Influence / leave-one-out sensitivity

The preregistration requires repeating the primary association after excluding each geography in turn.

Spearman ranges across all 19 exclusions:

- flood events: **−0.280 to −0.047**;
- landslide events: **+0.128 to +0.306**;
- combined derived event count: **−0.239 to −0.009**.

Thus no single geography is responsible for the broad sign pattern. Flood association remains negative under every one-geography exclusion, while landslide association remains positive. The magnitudes remain weak.

## Interpretation

The strongest defensible finding is **non-equivalence between annual wetness and annual recorded disaster burden**.

2024 was broadly wet across West Sumatra in the CHIRPS annual frame, but the spatial ranking of annual rainfall anomaly did not map monotonically onto BNPB flood-event counts. This is not surprising scientifically: annual totals discard rainfall timing and intensity, and flood occurrence also depends on drainage, river geometry, land cover, exposure, antecedent conditions, infrastructure and reporting. Landslides additionally depend strongly on slope, geology, soil state and local triggering rainfall.

The weak positive landslide association is mechanism-consistent but is not evidence that the annual rainfall anomaly caused the recorded landslides. Likewise, the weak negative flood association must not be interpreted as rainfall reducing flood risk.

The result instead tells the next research layer what **not** to do: annual rainfall totals should not be used as a simple proxy for local flood-event burden.

## What this case study does not establish

It does not establish:

- event-day rainfall intensity;
- a rainfall threshold for flood or landslide initiation;
- causal rainfall elasticity of disaster occurrence;
- climate-change attribution;
- affected population or unique-person exposure;
- disaster damage or economic loss;
- absence of disaster where the annual count is zero;
- BMKG station equivalence for CHIRPS.

## Why this completes the initial climate/disaster criterion

The Research Charter asks for one climate/disaster case study relevant to West Sumatra. This study links two independently qualified evidence systems over the same exact 19-geography footprint:

1. a 43-year historical CHIRPS climatology plus 2024 rainfall model estimates; and
2. independently cross-checked official BNPB 2024 flood/landslide event counts.

It produces a reproducible, bounded conclusion while keeping meteorological hazard and disaster records semantically distinct. More granular event-window rainfall and observed BMKG validation remain future research improvements, not hidden prerequisites for the initial foundation.

## Reproduction

```bash
python -m scripts.build_milestone9_hydroclimate_case_study
python -m scripts.audit_milestone9_hydroclimate_case_study --require-complete
PYTHONPATH=. python -m unittest tests.test_milestone9_hydroclimate_case_study -v
```

Authoritative outputs:

- `data/analysis/climate_disaster/m9-hydroclimate-2024-geography-frame.csv`
- `data/analysis/climate_disaster/m9-hydroclimate-2024-correlations.csv`
- `data/analysis/climate_disaster/m9-hydroclimate-2024-leave-one-out.csv`
- `data/manifests/milestone9_hydroclimate_case_study.json`
