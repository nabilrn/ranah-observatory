# Milestone 23 — Data Value & Model Readiness Audit Specification

## Purpose

M23 determines **what evidence should be acquired next before additional model complexity is introduced**.

M19–M22 provide direct evidence that the current analytical limit is not simply a lack of algorithms:

- M19: no one-year-ahead target beats persistence;
- M20: long-run rainfall slopes fail the monotonic stability gate;
- M21: a candidate climate breakpoint fails predictive/stability qualification;
- M22: only 4/7 short-panel socioeconomic indicator families benefit from hierarchical partial pooling, and real-GRDP growth has 0 robust geography trajectories.

M23 is therefore a dependency and evidence-value audit, **not a statistical model** and not a claim that more data always improves a model.

## Locked upstream evidence

Required completed inputs:

- M10 analytical panel;
- M16 spatial/climate risk engine;
- M18 final analytical synthesis and RQ readiness;
- M19 dynamic forecast engine;
- M20 historical climate trend engine;
- M21 climate regime-shift engine;
- M22 hierarchical socioeconomic trajectory engine.

## Priority principle

M23 does **not** create a pseudo-precise numeric score. Data families are assigned explicit priority tiers according to which unresolved research dependencies they unlock.

### Tier A — immediate evidence acquisition

A family is Tier A when it addresses at least one currently blocking dependency for a core research question **and** either:

- expands the comparison/sample universe used by major analytical engines; or
- supplies a component explicitly required before action/risk synthesis is allowed.

Locked Tier A families:

1. **National comparable regional panel — BPS**
   - unlocks larger comparison universes for RQ2;
   - directly addresses RQ3's missing comparable Indonesian regional panel;
   - increases sample size for predictive/expected-performance validation beyond 19 Sumbar geographies.

2. **District/city public-finance panel — DJPK/SIKD**
   - supplies own-source revenue, expenditure, capital expenditure and fiscal-capacity evidence;
   - adds a major institutional/fiscal mechanism absent from M11–M22;
   - directly addresses RQ5's missing cost/implementation/fiscal feasibility layer.

3. **Complete disaster-risk chain — BNPB/InaRISK and qualified companion sources**
   - M16 explicitly lacks exposure, vulnerability, capacity and observed impact;
   - without these, composite risk synthesis and resilience intervention ranking remain blocked.

### Tier B — next expansion after Tier A

4. **Investment realization panel — Kementerian Investasi/BKPM**
   - adds PMA/PMDN capital-formation evidence at kabupaten/kota level where available;
   - improves structural/explanatory coverage for RQ4 and scenario context for RQ5.

5. **Broader outcome and infrastructure/health panel — BPS and sector ministries**
   - expands attainable-development analysis beyond poverty, unemployment and GRDP growth;
   - candidates include real GRDP per capita, health, internet/electricity, roads and demographic structure.

6. **Station/daily climate validation — BMKG**
   - improves evidence class for climate analysis and extreme-rainfall measurement;
   - does not by itself solve causal rainfall→socioeconomic identification, so it is below the comparison/fiscal/risk priorities.

### Tier C — valuable but no longer a completion blocker

7. **Archival historical series**
   - supports RQ1 and long-run public narrative;
   - remains valuable wherever defensible sources exist;
   - continuous 1945–present reconstruction is not required and no artificial backfill is allowed.

## Official-source verification snapshot

M23 freezes a dated source-discovery registry. Verification means the official source currently exposes the stated access surface; it does not guarantee full historical coverage or semantic comparability.

Verified on 2026-08-19:

- BPS WebAPI: JSON programmatic access to BPS website/statistical table content across national, province and regency domains;
- DJPK SIKD APBD portal: filterable APBD data with regional/subregional filters and hundreds of local governments;
- BKPM Satu Data: public downloadable CSV/JSON investment datasets containing province and kabupaten/kota fields in current releases;
- InaRISK: official national disaster-risk methodology and coverage, while M16's exact raster version binding remains unresolved.

## Model-readiness states

M23 emits one of:

- `ready_with_current_data` — current evidence supports the analytical task under existing guardrails;
- `partially_ready` — useful bounded result exists but broader/stronger evidence is needed;
- `data_limited` — algorithm changes should not be prioritized before acquiring the identified evidence;
- `identification_limited` — more predictors alone will not solve the causal design problem;
- `component_limited` — a required risk/action component is missing.

## Anti-method-shopping gate

M23 explicitly blocks a new model family when the latest failure is primarily attributable to:

- insufficient comparison universe;
- short temporal panel;
- missing required risk/action components; or
- causal identification failure.

A new algorithm may be introduced later only when it answers a genuinely different estimand or when new evidence materially changes the validation regime.

## Required outputs

1. `data/analysis/engine/data_value_readiness_v1/m23-data-priorities.csv`
2. `data/analysis/engine/data_value_readiness_v1/m23-model-readiness.csv`
3. `data/analysis/engine/data_value_readiness_v1/m23-next-actions.csv`
4. `data/manifests/milestone23_data_value_model_readiness.json`
5. `data/registries/m23-official-source-candidates.csv`

## Completion gate

M23 completes when:

- all required upstream manifests are complete;
- every priority tier is traceable to an explicit RQ/engine limitation;
- current official source surfaces are frozen with source and access semantics;
- the next action sequence clearly separates data acquisition from later model fitting;
- no numeric pseudo-ranking, causal upgrade, or unsupported data-availability claim is emitted;
- focused tests pass;
- permanent CI is read-only and reproduces committed outputs byte-for-byte.

## Forbidden interpretations

M23 does not claim that:

- Tier A data will necessarily make a future model accurate;
- a source surface guarantees all desired years/variables are available;
- more features solve causal identification;
- archival history is unimportant because it is Tier C;
- an unqualified model should be replaced post hoc by a more complex algorithm until one wins.
