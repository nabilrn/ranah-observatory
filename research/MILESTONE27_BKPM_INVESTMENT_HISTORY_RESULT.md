# Milestone 27 — BKPM Investment-Realization History Result

## Final status

Milestone 27 is complete as a **bounded quarterly-history qualification**, not as an uninterrupted annualized investment series.

The official BKPM Satu Data `Data Realisasi Investasi Triwulan` family was inventoried for every quarter from 2010-Q1 through 2025-Q4. Stage 0 established 64/64 official dataset identities, declared schema continuity, public preview transport, resource UUID binding, and geography/period gates before target values were materialized.

Stage 1 then materialized only the Sumatera Barat public-preview subset under explicit quarter, province, geography, status-modal, missingness, and source-dimension checks.

## Qualified numeric coverage

- Inventory coverage: **64/64 quarters** from 2010-Q1 through 2025-Q4.
- Numeric-qualified quarters: **63**.
- Explicitly held quarters: **1**.
- Held period: **2024-Q1**.
- Materialized qualified observations: **1,440 geography × quarter × status-modal rows**.
- Geography regime: the 19 current Sumatera Barat kabupaten/kota, mapped explicitly to the canonical registry.
- Status modal remains separate as `PMA` and `PMDN`.
- Source-native metrics remain separate as `investasi_rp_juta` and `investasi_us_ribu`.

No absent geography/status group or missing metric is converted to zero.

## 2025-Q2 metadata conflict

The 2025-Q2 dataset page description contains a representation conflict that refers to Triwulan I. A preregistered prefix-only probe read only the first source-native `periode` scalar and stopped before subsequent observation fields. The source row states `2025 - Triwulan 2`, matching the dataset title and inventory target. The period identity was therefore resolved as Q2 without using target investment values for the decision.

## Geography representation amendment

The first numeric pilot failed closed because BKPM uses the source-native label `Kota Sawah Lunto`, while the canonical registry uses `Sawahlunto`. The original failure was preserved. A separate representation amendment explicitly bound the typed BKPM label to canonical geography `idn.13.1373`; no fuzzy geography identity inference was introduced.

After this amendment, the locked pilot periods 2010-Q1, 2025-Q2, and 2025-Q4 all qualified. The two 2025 controls mapped all 19 current Sumatera Barat kabupaten/kota.

## Why 2024-Q1 is held

The first full-history acquisition reconstructed exactly **1,107 Sumatera Barat source rows** for 2024-Q1 and mapped all 19 current kabupaten/kota, but the preregistered complete public-dimension uniqueness gate failed.

An offline diagnostic over the already-frozen 2024-Q1 evidence found:

- **174** duplicate public-dimension groups;
- **850** rows participating in those groups;
- **47** groups containing exact full-row duplicates;
- **127** groups containing the same 11 public dimensions but distinct full rows;
- **21** public-dimension groups spanning the two deterministic pages;
- only **2** exact full-row duplicate groups spanning pages;
- differing fields among dimension-colliding distinct rows include `investasi_rp_juta`, `investasi_us_ribu`, and `tki`.

This is classified as **mixed duplicate mechanisms**. The evidence does not support treating the anomaly as pagination overlap alone, because many exact duplicates and metric-divergent dimension collisions occur within a single page. It also does not support blind source-row deduplication, because many rows sharing public dimensions have different metrics/TKI.

Official BKPM metadata describes this dataset family as aggregated investment-realization data grouped principally by business sector, project location, and investor country. The observed 2024-Q1 public representation therefore does not provide a sufficiently defensible unique row key for forced deduplication. 2024-Q1 remains `held_methodology_or_coverage_discontinuity` and contributes no promoted numeric observation.

## Reproducibility

All live retrieval outputs are frozen in the repository. A permanent offline rebuild:

1. reads the frozen 64-quarter evidence without network access;
2. verifies page checksums, declared schema, post-search counts, period identity, Sumatera Barat province identity, typed geography mapping, status modal, and source-dimension uniqueness;
3. reproduces the 63 qualified quarters while retaining 2024-Q1 as held;
4. rebuilds the quarterly analytical CSV and quarter-audit CSV;
5. requires both rebuilt outputs to be byte-identical to the committed live-acquisition outputs.

The current offline certificate passes with:

- 64 quarters rebuilt;
- 63 qualified;
- 1 held (`2024-Q1`);
- 1,440 materialized observations;
- byte-identical quarterly output;
- byte-identical quarter audit.

## Authorized interpretation

M27 authorizes only **bounded quarterly numeric use for the 63 qualified quarters**. It does not authorize interpolation across 2024-Q1 or interpretation of the dataset as an uninterrupted balanced panel.

The official fields describe `investasi_rp_juta` and `investasi_us_ribu` as additional investment realization reported through LKPM, and every promoted row is bound to its source-native quarter identity. However, M27 does **not** establish cross-quarter additivity or a continuous annual accounting identity.

## Still forbidden

M27 does not authorize:

- treating missing or held observations as zero;
- deduplicating 2024-Q1 to manufacture a usable quarter;
- combining PMA and PMDN;
- externally converting USD and rupiah metrics;
- summing Q1–Q4 into annual totals;
- interpreting Q4 as an annual total;
- per-capita normalization or investment ranking as an M27 claim;
- statistical/ML model fitting from BKPM evidence as an M27 result;
- causal interpretation of investment relationships;
- monetary wasted-potential estimation.

## Canonical outputs

- `data/analysis/engine/investment_realization_v1/m27-bkpm-resource-inventory.csv`
- `data/analysis/engine/investment_realization_v1/m27-bkpm-quarterly-history.csv`
- `data/analysis/engine/investment_realization_v1/m27-bkpm-quarter-audit.csv`
- `data/manifests/milestone27_bkpm_full_history.json`
- `data/manifests/milestone27_bkpm_stage1_qualification.json`
- `data/manifests/milestone27_bkpm_2024q1_duplicate_diagnostic.json`
- `data/manifests/milestone27_bkpm_offline_reproducibility.json`

## Exit decision

`milestone27_complete = true`

`bounded_quarterly_investment_history_qualified = true`

`continuous_64_quarter_history_qualified = false`

`2024_q1_numeric_promotion_authorized = false`

`annual_sum_authorized = false`

`causal_claim_authorized = false`

`monetary_wasted_potential_estimate_authorized = false`

M27 therefore closes Tier-B priority #4 from the M23 data-value audit with an explicit boundedness condition rather than hiding the source anomaly.
