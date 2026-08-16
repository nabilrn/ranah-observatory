# BPS Population Reference Periods: 2010, 2015, 2020

## Objective

This micro-milestone qualifies only the temporal semantics of the clean modern BPS population anchors for 2010, 2015, and 2020.

It does **not** derive `population_growth`.

The reason for separating this step is methodological: a population growth rate should not be constructed from year labels alone when the underlying observations have different census/survey timing semantics.

## 2010 — SP2010

Official BPS documentation states:

- national SP2010 fieldwork: **1–31 May 2010**;
- **Hari Sensus: 15 May 2010**.

Evidence:

- https://kalsel.bps.go.id/id/news/2012/06/24/292/sensus-penduduk-2010--sp2010-.html
- supporting national BPS announcement: https://www.bps.go.id/id/news/2010/05/01/3/bali-lakukan-sensus-lebih-awal.html

Decision:

- `reference_semantics=census_day`;
- point reference date: `2010-05-15`;
- temporal reference qualification: **point-qualified**.

This does not, by itself, qualify a 2010→2020 derived growth pair because the boundary-comparability decision remains separate.

## 2015 — SUPAS2015

Official BPS publication metadata states that SUPAS2015 enumeration was conducted during **1–31 May 2015**.

Evidence:

- https://www.bps.go.id/id/publication/2016/11/30/63daa471092bb2cb7c1fada6/profil-penduduk-indonesia-hasil-supas-2015

Decision:

- `reference_semantics=fieldwork_window`;
- qualified window: `2015-05-01` through `2015-05-31`;
- no single point reference date is inferred;
- temporal qualification: **window-only**.

Therefore the pipeline must not silently treat the 2015 anchor as a 15-May point estimate or another invented date.

## 2020 — SP2020

The official BPS national result identifies the population count as **SP2020 September 2020**. Official BPS fieldwork guidance describes the September field enumeration as occurring during **1–30 September 2020**.

Evidence:

- result: https://www.bps.go.id/id/pressrelease/2021/01/21/1854/hasil-sensus-penduduk-2020.html
- fieldwork window: https://bali.bps.go.id/id/news/2020/09/01/96/kick-off-sensus-penduduk-2020-provinsi-bali.html

Decision:

- `reference_semantics=result_month_window`;
- qualified window: `2020-09-01` through `2020-09-30`;
- no single point reference date is invented;
- temporal qualification: **month-window**.

This matches the 20 SP2020 population observations already frozen in the BPS expansion, whose canonical bounds are September 1–30, 2020.

## Why custom population growth is still blocked

The temporal audit improves the evidence state but does not complete a growth pair.

Current state:

- 2010: exact census day is qualified;
- 2015: only a one-month fieldwork window is qualified;
- 2020: a September result month/window is qualified;
- modern boundary compatibility still requires its own pair-level review.

A custom annualized growth calculation therefore remains blocked until a pair-specific interval rule and boundary-comparability decision are documented.

BPS itself publishes official 2010–2020 population growth statistics. That is a **separate future evidence lane** and should be qualified as an official BPS statistic rather than reverse-engineered into this reference-period step.

## Repository contract

The evidence is recorded in:

- `data/registries/bps_population_reference_periods.csv`;
- refined `reference_date_decision` fields in `data/registries/bps_population_anchor_qualification.csv`.

The validator requires:

1. only 2010, 2015, and 2020 in this bounded registry;
2. official HTTPS `bps.go.id` evidence URLs;
3. 2010 reference date exactly `2010-05-15`;
4. 2015 point date empty and May 2015 window preserved;
5. 2020 point date empty and September 2020 window preserved;
6. all custom growth statuses remain blocked;
7. all 20 existing canonical SP2020 rows retain September 2020 bounds.

## Exit decision

This milestone can say that modern population anchor **temporal semantics are substantially improved**.

It cannot yet say that a custom 2010→2015, 2015→2020, or 2010→2020 growth rate is safe to calculate.

The next micro-milestone should review **boundary compatibility for one pair only**, preferably 2010→2020, before deciding whether to derive anything or instead ingest BPS's official published growth statistic.
