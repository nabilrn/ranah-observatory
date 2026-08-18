# Milestone 15 — Causal Evidence Expansion v1

M15 expands the causal evidence layer without manufacturing a second causal coefficient.

## Library state

The machine-readable library contains three entries:

1. **2009 earthquake** — `completed_quasi_causal_study`; inherited from M8 without reinterpretation.
2. **Lagged rainfall → unemployment** — `not_identification_ready`.
3. **COVID structural exposure → local economic outcomes** — `not_identification_ready`.

## Why the M14 rainfall signal is not immediately causal

M14 discovered the rainfall/unemployment association using 2019–2024 target years. M10 currently extends unemployment through 2025, leaving only one genuinely new annual outcome year after the discovery sample.

A 2019–2025 causal panel would therefore reuse six of seven outcome years that generated the hypothesis. Treating the resulting p-value as an independent confirmation would be selection-on-result.

Additional blockers remain:

- CHIRPS remains `model_estimate` climate evidence with BMKG station validation pending;
- annual rainfall is temporally coarse for weather-shock mechanisms;
- weather shocks are spatially correlated and require dedicated inference.

No rainfall causal model is fit in M15 v1.

## Why the COVID candidate is blocked

M10 begins in 2018. For a 2020 event-study design this gives only 2018 and 2019 as complete pre-event annual outcome years.

M15 preregistered a minimum of three complete pre-event years. The current evidence provides only two, so the candidate fails the trend-diagnostic gate before any coefficient is estimated.

## Interpretation

`not_identification_ready` means the current evidence cannot support the proposed quasi-causal design under the locked rules. It does not mean the mechanism has no effect.

M15 therefore preserves failed identification attempts as evidence about what additional data are needed:

- rainfall/unemployment needs an independent confirmation window or genuinely new outcome frequency/years plus a qualified climate/inference design;
- COVID structural exposure needs compatible district outcomes extending to at least 2017, preferably earlier.

## Outputs

- `data/analysis/engine/causal_evidence_v1/m15-causal-evidence-library.csv`
- `data/manifests/milestone15_causal_evidence_expansion.json`
