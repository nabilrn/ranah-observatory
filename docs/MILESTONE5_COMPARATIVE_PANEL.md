# Milestone 5 — Comparative Indonesian Panel

## Research Charter criterion

Milestone 5 operationalizes the Research Charter criterion:

> **a comparative Indonesian panel where feasible**

The milestone stops at a reproducible comparative data product. It does **not** perform the later exploratory ranking, peer discovery, frontier modelling, causal attribution, or policy simulation stages.

## Panel scope

The frozen comparison panel is intentionally narrow and defensible:

- geography level: **province**;
- current geography regime: **38 provinces**;
- time window: **2024–2025**;
- source authority: **Badan Pusat Statistik (BPS-Statistics Indonesia)**;
- BPS WebAPI domain: **`0000`**;
- six qualified comparison indicators;
- no imputation;
- exact source selectors, units, reference periods, and source notes are retained in the series registry and panel provenance.

The panel uses the comparability regime identifier:

`bps_current_38_province_2024plus`

## Why the panel starts in 2024

The national BPS poverty and Gini source notes explicitly state that Papua and Papua Barat observations before 2024 represent the provinces before the later autonomous-region splits. Ranah Observatory therefore does not backcast the four current Papua-area provinces into earlier years and does not silently treat pre-2024 and current geography as the same boundary system.

Starting the core panel in 2024 allows all six selected indicators to be represented on one current 38-province footprint without inventing a historical geography crosswalk.

## Qualified core indicators

| Indicator | BPS var | Source selector | Canonical treatment |
|---|---:|---|---|
| `poverty_rate` | 192 | `Jumlah` × `Semester 1 (Maret)` | Percent; March poverty headcount |
| `gini_ratio` | 98 | `Perkotaan+Perdesaan` × `Semester 1 (Maret)` | Gini index; March |
| `unemployment_rate` | 543 | `Tidak ada` × `Agustus` | Percent; Sakernas August |
| `underemployment_rate` | 1181 | `Tidak ada` × source `Tahun` period | Percent; no month inferred where metadata does not state one |
| `real_grdp_per_capita` | 288 | `Harga Konstan 2010` × source `Tahun` period | BPS-published derived statistic; thousand rupiah converted exactly to million rupiah per person at constant 2010 prices |
| `neet_rate` | 1186 | `Tidak ada` × source `Tahun` period | Percent; age 15–24 NEET universe preserved |

The machine-readable selector contract is `data/registries/bps_comparative_panel_series.csv`.

## Candidate review and explicit holds

The discovery probe intentionally considered more indicators than were promoted. Structural availability alone is not sufficient for comparability.

### Population total and population growth

National-domain variables 1975 and 1976 expose an Indonesia-level vertical geography in the probed source rather than a 38-province panel. They are held from the Milestone 5 panel.

### Fertility and mortality anchors

The probed total-fertility-rate source is an older survey anchor rather than a current annual 2024–2025 panel.

The probed infant- and under-five-mortality variables expose province labels in metadata for the reviewed 2017 period, but the BPS source note states that province figures for 2017 are unavailable and the returned data footprint is not a current province panel. They are therefore held rather than fabricated or copied from another source.

### Mobile-phone candidate

National BPS variable 1221 measures individuals who **possess/control a mobile phone**. The existing Ranah Observatory `mobile_phone_use` concept is qualified against a different BPS construct: persons age 5+ using a mobile phone within the source recall period. The ownership candidate is not silently relabelled as use and is excluded from this panel.

## Evidence chain

Initial source discovery is recorded in:

- `data/registries/bps_comparative_panel_candidates.csv`;
- `data/manifests/milestone5_bps_comparative_probe.json`.

Frozen source evidence for the promoted panel is stored under:

- `data/raw/bps/comparative/`.

The comparative products are stored under:

- `data/analysis/comparative/bps-current38-province-panel-long.csv`;
- `data/analysis/comparative/bps-current38-province-panel-wide.csv`;
- `data/analysis/comparative/bps-current38-province-panel-provenance.csv`;
- `data/analysis/comparative/bps-current38-province-panel.manifest.json`.

The long panel intentionally uses `panel_observation_id` / `panel_provenance_id` rather than the canonical observation schema. This prevents the comparison layer from duplicating Sumatera Barat canonical observations already present in the Milestone 4 data foundation.

## Completion gate

`scripts/audit_milestone5_comparative_panel.py` fails closed unless the frozen panel satisfies all of the following:

- exactly **38** current provinces;
- exactly **2024 and 2025**;
- exactly **6** qualified indicators;
- exactly **456** long panel observations (`38 × 2 × 6`);
- exactly **76** complete province-year rows in the wide panel;
- exactly **12** source provenance records (`6 × 2`);
- no duplicate panel IDs or semantic keys;
- all values finite and source-linked;
- every source snapshot and manifest resolves;
- snapshot byte and semantic SHA-256 checks pass;
- all rows use the current-38 comparability regime;
- Sumatera Barat (`idn.13`) has complete coverage;
- wide and long representations agree numerically.

The committed audit report is `data/manifests/milestone5_comparative_panel_audit.json`.

## Boundary of this milestone

Milestone 5 establishes the comparison substrate. It does not yet assert that a specific province is a valid causal counterfactual or structural peer for Sumatera Barat. Choosing peers, measuring gaps, estimating efficiency/frontiers, and explaining causes require later milestones and additional model assumptions.
