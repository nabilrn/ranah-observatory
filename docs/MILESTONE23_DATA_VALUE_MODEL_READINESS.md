# Milestone 23 — Data Value & Model Readiness Audit

Status: **complete; next work is evidence acquisition rather than algorithm escalation**.

M23 formalizes the lesson from M19–M22: several current analytical limits are driven primarily by sample size, comparison-universe breadth, missing required evidence components, or causal-identification constraints. Adding a more complex algorithm before addressing those limitations would risk method-shopping rather than improve the scientific basis of Ranah Observatory.

## Priority tiers

### Tier A — immediate

1. **National comparable regional panel — BPS**
   - highest leverage for RQ2 attainable-development comparisons and RQ3 long-run/comparable regional divergence;
   - expands the analytical universe beyond 19 West Sumatra kabupaten/kota;
   - the repository already uses `BPS_API_KEY` as a GitHub Secret, so the first discovery/harvest can proceed without user credential handling.

2. **District/city public-finance panel — DJPK/SIKD**
   - adds PAD, expenditure, capital expenditure, and fiscal-capacity evidence;
   - directly supports institutional mechanism analysis and RQ5 feasibility/cost context.

3. **Complete disaster-risk chain — BNPB/InaRISK**
   - M16 still lacks exposure, vulnerability, capacity, and observed impact;
   - composite risk synthesis remains blocked until these components are version-bound and qualified.

### Tier B — next

4. BKPM investment realization panel;
5. broader health/infrastructure/demographic/outcome panel;
6. BMKG station/daily climate validation.

### Tier C — opportunistic historical expansion

7. archival historical series with explicit source-era geography and methodology.

Archival evidence remains valuable, but continuous 1945–present quantitative reconstruction is not a completion requirement and must never be manufactured through backfilling.

## Model-readiness implications

- **One-year-ahead socioeconomic forecasting:** `data_limited`; M19's 0/3 benchmark result means a new forecasting algorithm is not the next priority.
- **Attainable development:** `partially_ready`; useful bounded results exist, but the comparison universe is too narrow.
- **Long-run regional divergence:** `data_limited`; a comparable Indonesian regional panel is missing.
- **Rainfall→unemployment causal explanation:** `identification_limited`; adding predictors does not create exogenous treatment variation.
- **Disaster risk synthesis:** `component_limited`; required risk components are missing.
- **Policy action ranking:** `component_limited`; causal policy effects, costs, fiscal feasibility, implementation horizon, and risk-chain evidence remain incomplete.
- **Qualified modern labor/yield trajectory summaries:** `ready_with_current_data` for bounded descriptive publication under M22 guardrails.

## Next sequence

1. discover and harvest a national/comparable BPS panel;
2. probe and qualify DJPK district/city public-finance data;
3. resolve InaRISK component version/vintage metadata;
4. inventory historical kabupaten/kota BKPM investment datasets;
5. only then re-open the model-selection gate if the new evidence materially changes the sample, component, or identification regime.

## Claim boundary

M23 is a research dependency audit, not a statistical model and not a prediction that Tier A data will necessarily improve future model accuracy. Source verification means the official access surface exists and exposes the stated type of data; it does not guarantee every desired variable/year is available or comparable.
