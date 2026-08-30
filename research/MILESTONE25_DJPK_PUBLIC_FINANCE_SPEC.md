# Milestone 25 — DJPK/SIKD Public-Finance Panel Specification

## Purpose

M25 adds a fiscal/institutional evidence layer for the 19 current West Sumatra kabupaten/kota. The immediate objective is not to fit a fiscal model. It is to determine which APBD realization accounts can be represented consistently over 2018–2025 and then freeze only those qualified series with explicit taxonomy semantics.

The milestone is staged because the DJPK/SIKD APBD account presentation changes across time. Account labels must not be silently equated across taxonomy regimes.

## Official source

Official DJPK/SIKD APBD portal:

`https://djpk.kemenkeu.go.id/portal/data/apbd`

Locked query semantics for the annual realization discovery regime:

- `provinsi=03` — Sumatera Barat in the DJPK portal;
- `periode=12` — locked annual-final selector. Historical source pages may report final status as `s.d Desember`, `s.d Audited <year>`, or `s.d Perda <year>`; intermediate-month and unaudited states are not accepted;
- `tahun=YYYY` — fiscal year;
- `pemda=01..19` — DJPK local-government selector within Sumatera Barat.

M25 does not assume that the DJPK selector is a BPS geography code. An explicit crosswalk is stored in `data/registries/djpk_sumbar_pemda.csv`.

The annual-final semantic compatibility is a representation amendment only. It does not change the locked `periode=12` selector, target years, geographies, account-family set, or statistical design. The HTML page remains blocking evidence for jurisdiction, fiscal year, accepted annual-final status, and the same-selector export link; exact numeric account values come from the official SpreadsheetML export. Rounded HTML table values are diagnostic only.

## Geography crosswalk

The locked 19-selector mapping is derived from official DJPK regional-code ordering and portal evidence. The current West Sumatra geography IDs remain the canonical project identifiers.

No historical boundary reconstruction is performed. The analytical geography regime is the current 19 kabupaten/kota used by M10.

## Stage 0 — taxonomy discovery

Before any fiscal account is promoted to a canonical series, M25 probes a fixed reference local government:

- Kota Padang;
- DJPK `provinsi=03`, `pemda=12`;
- December (`periode=12`);
- years 2018–2025 inclusive.

The probe freezes or reports, for each year:

- HTTP/source retrieval status;
- page jurisdiction and fiscal-year identity;
- source note describing realization period;
- complete APBD postur account labels;
- raw `Anggaran/Pagu`, `Realisasi`, and `%` cell text;
- response SHA-256;
- normalized account-label presence.

Stage 0 is a structural/taxonomy audit only. It does not authorize a public-finance panel or derived fiscal ratios.

## Pre-declared conceptual account families

The following conceptual families are the only families eligible for Stage 1 promotion. Exact source labels are not locked until Stage 0 reveals the taxonomy:

1. total local-government revenue;
2. own-source revenue (PAD);
3. total expenditure;
4. capital expenditure;
5. central-government transfer revenue / transfer dependence.

No additional account family may be introduced after inspecting the values merely because it produces a desirable association.

## Taxonomy qualification rules

### Exact-label series

A conceptual account qualifies as an exact-label 2018–2025 series when the same normalized source account label appears exactly once in every Stage 0 year and the row role is substantively the same.

### Explicit bridge series

If source labels differ across years, a bridge may be created only when:

1. both labels clearly refer to the same accounting concept at the same hierarchy level;
2. the bridge is documented before inspecting cross-geography fiscal outcomes;
3. the year-to-label mapping is explicit;
4. no addition/subtraction of incomparable subaccounts is used to manufacture continuity;
5. tests fail closed on unexpected labels.

A mere lexical similarity is not sufficient.

### Held series

A conceptual family remains held when taxonomy or hierarchy cannot be reconciled defensibly. M25 may complete with fewer than five qualified fiscal families.

## Stage 1 — full 19 × 2018–2025 source probe

Only Stage-0-qualified account contracts may proceed.

For each of 19 kabupaten/kota × 8 years (`152` jurisdiction-years), M25 must verify:

- requested page corresponds to the expected local government and fiscal year;
- accepted annual-final realization semantics are present (`Desember`, `Audited`, or `Perda` for the same fiscal year);
- each locked account contract appears exactly once;
- realization values are parseable using the documented Indonesian-number format;
- source page response and retrieval metadata are frozen or checksum-bound;
- no jurisdiction-year is silently imputed.

## Stage 2 — canonical fiscal panel

Only Stage-1-qualified contracts are materialized.

Canonical observations retain:

- canonical geography ID/name;
- DJPK province/pemda selector;
- fiscal year;
- conceptual account ID;
- exact source account label;
- realization value and unit;
- source response checksum/provenance;
- taxonomy regime/bridge ID;
- retrieval metadata;
- claim type `observed_recorded_fiscal_realization`.

## Derived fiscal ratios

Derived ratios are a later sub-gate and are allowed only when both numerator and denominator are qualified observations from the same jurisdiction-year and taxonomy-compatible concepts.

Potential ratios include:

- PAD share of total revenue;
- capital-expenditure share of total expenditure;
- central-transfer share of total revenue.

No ratio is created when its source components are held.

## Model boundary

M25 is evidence acquisition/harmonization. It does not itself estimate:

- fiscal causality;
- policy effectiveness;
- fiscal multipliers;
- treatment effects;
- cost-benefit rankings;
- monetary wasted potential.

A later model gate may use the panel only after coverage, taxonomy, scale, and temporal semantics are audited.

## Required Stage 0 outputs

1. `data/manifests/milestone25_design_gate.json`
2. `data/registries/djpk_sumbar_pemda.csv`
3. `data/analysis/engine/djpk_finance_v1/m25-taxonomy-discovery.csv`
4. `data/analysis/engine/djpk_finance_v1/m25-account-presence.csv`
5. `data/manifests/milestone25_taxonomy_discovery.json`

Later Stage 1/2 outputs are locked only after Stage 0 completes.

## Completion semantics

M25 Stage 0 completes when all eight Kota Padang December pages are retrieved and parsed, the account-label regimes are explicit, and each of the five conceptual families is classified as exact-label-qualified, explicit-bridge-candidate, or held.

Full M25 completes only after the 19 × 8 panel is frozen and canonicalized for all promoted account families.

## Forbidden interpretations

M25 does not authorize statements that:

- APBD budget appropriation equals realized expenditure;
- similarly named accounts across taxonomy regimes are automatically equivalent;
- a fiscal association is causal;
- more PAD is automatically welfare-improving without context;
- current jurisdiction codes establish historical boundary continuity;
- missing fiscal observations can be interpolated or copied from neighboring years.
