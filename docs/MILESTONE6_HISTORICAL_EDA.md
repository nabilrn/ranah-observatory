# Milestone 6 — Exploratory Historical Analysis

Milestone 6 satisfies the Research Charter criterion **“exploratory historical analysis.”**

This milestone is deliberately descriptive. It does **not** estimate causal effects, expected performance, efficiency frontiers, counterfactual output, or “wasted potential.” Those belong to later milestones.

## Why the analysis is segmented

There is no defensible single continuous historical panel for Sumatera Barat yet. The repository contains several evidence regimes with different spatial and statistical meanings, so the EDA keeps them separate:

1. **Source-era legal geography, 1945–1961**
   - 1945–1946 remains an explicit source gap.
   - 1947 Sumatra, 1948 three-province division, 1950 Sumatera Tengah, the 1957 reorganization, the 1958 confirmation, and the 1961 census boundary warning are retained as qualified chronology.
   - The 1957 reorganization is an analytical boundary break. Earlier Sumatera Tengah records are not silently relabelled as later Sumatera Barat.

2. **1971 source-era population**
   - The qualified BPS WebAPI province anchor is attached to `idn.13.h1958`, not current `idn.13`.
   - Fourteen local source-era rows sum exactly to the province total.
   - No 1971-to-current population growth rate is calculated because local boundary lineage is unresolved.

3. **CHIRPS annual rainfall, 1981–2025**
   - 45 annual observations for each of 19 **current June 2026** kabupaten/kota.
   - `claim_type=model_estimate`.
   - This is a fixed-current-boundary environmental diagnostic, not historical administrative reconstruction.
   - Independent BMKG station validation remains pending.
   - The 1997→1998 signal is descriptive only; no ENSO causal claim is made.

4. **Modern BPS province trajectory**
   - Seven Sumatera Barat province series are retained for 2018–2025 (life expectancy begins in 2020).
   - Five series are qualified for endpoint/min/max trend summaries: poverty, real GRDP growth, mean years of schooling, expected years of schooling, and life expectancy.
   - Labor-force participation and unemployment are retained as context, but their source cross-regime comparability remains unresolved and they are not used as trend-qualified endpoint claims.

## Frozen outputs

`data/analysis/historical/` contains:

- `west-sumatra-source-era-timeline.csv`
- `west-sumatra-1971-population-anchor.csv`
- `west-sumatra-modern-trajectory-2018-2025.csv`
- `west-sumatra-modern-trend-summary.csv`
- `west-sumatra-chirps-regional-year-summary.csv`
- `west-sumatra-chirps-geography-signals.csv`
- `west-sumatra-exploratory-findings.csv`

The source/output checksum contract is:

- `data/manifests/milestone6_historical_eda.json`

The completion audit is:

- `data/manifests/milestone6_historical_eda_audit.json`

## Completion gates

Milestone 6 is complete only when all of the following hold:

- all six qualified 1947–1961 historical anchors are present;
- the 1945–1946 and 1951–1960 gaps remain explicit;
- the 1971 population anchor remains on `idn.13.h1958`;
- the 14 local 1971 source-era values sum to the province total without current-boundary remapping;
- CHIRPS contains exactly 45 years × 19 current geographies and remains labelled `model_estimate`;
- no CHIRPS row claims historical boundary continuity or completed station validation;
- at least five modern trend-qualified province series have at least six annual observations;
- all generated source/output checksums resolve;
- every exploratory finding is explicitly non-causal;
- no frontier, expected-performance, counterfactual, or wasted-potential model is run.

## Reproduction

```bash
python scripts/build_milestone6_historical_eda.py
python scripts/audit_milestone6_historical_eda.py --require-complete
python -m unittest tests.test_milestone6_historical_eda -v
```

The build is deterministic from frozen repository evidence. No live API request is required.
