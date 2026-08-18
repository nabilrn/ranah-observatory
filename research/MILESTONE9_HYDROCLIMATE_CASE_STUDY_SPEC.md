# Milestone 9 — 2024 West Sumatra Hydroclimate Disaster Case Study

## Charter criterion

Milestone 9 targets the remaining initial-success criterion in `research/RESEARCH_CHARTER.md`:

> one climate/disaster case study relevant to West Sumatra

This case study is intentionally distinct from Milestone 8. Milestone 8 studies a geophysical earthquake with a quasi-causal economic design. Milestone 9 studies the spatial alignment between a hydroclimate estimate and officially recorded flood/landslide events.

## Why 2024 is selected

The year is selected **from the qualified disaster-source contract before inspecting the rainfall/disaster association**.

The current BNPB foundation provides one exact, independently cross-checked disaster-type-by-kabupaten/kota footprint for West Sumatra: 2024 `BANJIR` and `TANAH LONGSOR` counts for all 19 kabupaten/kota. Earlier 2010–2024 BNPB material in the repository is total-disaster context rather than a disaster-type-by-year-by-kabupaten cube, and is therefore not relabelled as historical flood/landslide counts.

Thus 2024 is selected because it is the first/only currently qualified exact 19-unit type-specific year, not because its CHIRPS rainfall appears extreme.

## Research question

Across West Sumatra's 19 current kabupaten/kota, did the 2024 spatial distribution of officially recorded flood and landslide events align with how wet 2024 was relative to each geography's own long-run CHIRPS rainfall baseline?

This is a **descriptive climate/disaster case study**. It does not estimate the causal effect of rainfall on disasters.

## Geography

- 19 canonical West Sumatra kabupaten/kota.
- BNPB 2024 observations are mapped through the reviewed explicit Permendagri-to-canonical crosswalk.
- CHIRPS rainfall uses BIG June-2026 fixed-current-boundary polygons.
- The join key is canonical `geography_id`.
- The study does not claim that the BIG June-2026 geometry reconstructs any different historical boundary regime.

## Climate evidence

Source: CHIRPS v3 Final monthly materialized annual rainfall.

Evidence class: `model_estimate`.

The study must retain all of the existing CHIRPS limitations:

- gridded blended satellite/station estimate, not a BMKG gauge observation;
- fixed-current-boundary June-2026 zonal frame;
- independent station validation remains pending;
- no daily/extreme-rainfall-day claim is inferred from annual totals.

### Primary climate metric

For each geography:

`rainfall_z_2024 = (rainfall_2024 - mean(rainfall_1981..2023)) / sample_sd(rainfall_1981..2023)`

Baseline is fixed at **1981–2023**, excluding the study year 2024 and post-study year 2025.

Additional preregistered descriptive climate metrics:

- 2024 annual rainfall in millimetres;
- absolute anomaly from 1981–2023 mean;
- percentage anomaly from 1981–2023 mean;
- 2024 percentile position relative to the 43 baseline years, defined as `100 * count(baseline_year <= 2024_value) / 43`.

No alternative climatology window may be selected because it increases the apparent association.

## Disaster evidence

Source: BNPB Satu Data, independently cross-checked 2024 event-by-type resource family.

Evidence class: `observed` recorded-event counts, subject to reporting intensity and classification practice.

Primary disaster outcomes are kept separate:

- `flood_events`;
- `landslide_events`.

A derived summary may also be reported:

`hydroclimate_event_count = flood_events + landslide_events`

This sum is a derived count of two BNPB categories, not an estimate of unique disasters, affected persons, economic loss, or hazard exposure.

## Preregistered analyses

Before association results are inspected, the study locks the following:

1. build one 19-row geography frame containing 2024 rainfall/anomaly metrics and both BNPB counts;
2. report complete descriptive rankings for rainfall anomaly, floods, and landslides;
3. report Pearson and Spearman correlations between `rainfall_z_2024` and:
   - `flood_events`;
   - `landslide_events`;
   - derived `hydroclimate_event_count`;
4. report the same correlations using raw 2024 rainfall as a sensitivity check;
5. report leave-one-geography-out ranges for the primary Spearman correlations to show whether one geography dominates the spatial association;
6. do not select a significance threshold after seeing the results;
7. do not transform event counts, exclude zero-event geographies, or introduce terrain/urbanization covariates in this initial case study after seeing the association.

## Interpretation rules

Permitted claims:

- descriptive spatial alignment or non-alignment;
- which geographies were unusually wet relative to their own CHIRPS baseline;
- which geographies recorded more/fewer BNPB flood or landslide events in 2024;
- whether simple cross-sectional association is positive, negative, weak, or sensitive to individual geographies.

Prohibited claims:

- annual rainfall caused a specific flood or landslide;
- CHIRPS annual rainfall measures event-day precipitation intensity;
- the correlation is a rainfall-disaster causal elasticity;
- a zero BNPB count proves no disaster occurred;
- BNPB event counts measure affected population, damage, or economic loss;
- CHIRPS is observed BMKG station rainfall;
- the case study estimates climate-change attribution.

## Key limitations

Annual rainfall is temporally coarse for event-trigger analysis. Floods and landslides depend on rainfall timing and intensity, antecedent moisture, slope, geology, drainage, land cover, exposure, vulnerability, reporting, and other mechanisms. The annual spatial association is therefore a foundation case study linking qualified climate and disaster evidence layers, not a substitute for event-window hydrometeorological attribution.

## Completion gates

Milestone 9 completes only if:

- CHIRPS input contract remains exact 1981–2025 × 19 = 855 observations;
- 2024 CHIRPS exists for all 19 geographies and baseline 1981–2023 has exact 43 years per geography;
- BNPB canonical input remains exact 19 × 2 indicators = 38 observations for 2024 with independent official cross-check passed;
- the canonical geography sets match exactly;
- all rainfall and event-count values are finite and non-negative;
- no BNPB zero-event row is dropped;
- no station-observation equivalence or causal attribution is claimed;
- all preregistered association/sensitivity outputs are reported regardless of sign;
- leave-one-out sensitivity is complete for all 19 exclusions;
- outputs are deterministic, hashed, documented, tested, and reproducible in read-only CI.

## Current status

Preregistered before Milestone 9 association computation. No rainfall/disaster correlation from this design has yet been interpreted.
