# BPS Population Growth 2010–2020 Publication Contract

## Objective

This micro-milestone qualifies the **source contract** for the official BPS kabupaten/kota population-growth rates for 2010–2020.

It does not yet add canonical `population_growth` observations.

The source is Table **3.1.1** in:

- Agency: BPS Provinsi Sumatera Barat
- Publication: *Provinsi Sumatera Barat Dalam Angka 2021*
- Publication number: `13000.2106`
- Publication ID: `438e46e73d9a64df8d8c34f2`
- Official publication page:  
  https://sumbar.bps.go.id/id/publication/2021/02/26/438e46e73d9a64df8d8c34f2/provinsi-sumatera-barat-dalam-angka-2021.html

Table 3.1.1 contains, for each current Sumatera Barat kabupaten/kota:

- SP2010 population;
- SP2020 population;
- annual population growth for 2000–2010;
- annual population growth for 2010–2020.

The target indicator in Ranah Observatory is only the **2010–2020** growth column.

## Why this source supersedes var-484 for the growth pair

The earlier var-484 anchor audit showed that its 2010 response is not the appropriate pair source for this calculation.

A critical example is the province total:

- var-484 2010 audited value: `4,865,841`;
- official SP2010 census dataset and Table 3.1.1: **`4,846,909`**.

Several kabupaten/kota values also differ slightly between the var-484 2010 response and the final SP2010 dataset used by the publication.

Official SP2010 dataset:

https://sensus.bps.go.id/topik/tabular/sp2010/10/91625/0

The official SP2010 page gives all 19 current kabupaten/kota rows and total population **4,846,909**.

Official SP2020 dataset:

https://sensus.bps.go.id/topik/tabular/sp2020/1/4/0

The official SP2020 page gives the same 19 current geography codes and total population **5,534,472**.

Therefore the publication's paired source values, not the older var-484 2010 response, are the qualified basis for the official 2010–2020 rate.

## Temporal semantics and formula

BPS's official population-growth indicator methodology uses the geometric method.

For the 2020 indicator, BPS explicitly identifies the interval as:

- SP2010 population: **May 2010**;
- SP2020 population: **September 2020**.

That is **124 months**, or `124 / 12 = 10.333333...` years.

For source-contract validation the repository independently recomputes:

`100 × ((P2020 / P2010)^(1 / (124/12)) - 1)`

and requires the value rounded to two decimals to equal the BPS-published 2010–2020 rate for **all 19 geographies**.

This recomputation is a validation check. It does not change source attribution: the intended canonical value remains the **official BPS-derived statistic**.

## Source-contract values

The 19-row source contract is stored at:

`data/registries/bps_population_growth_2010_2020_publication.csv`

Its row sums must equal:

- SP2010: **4,846,909**;
- SP2020: **5,534,472**.

Examples of official 2010–2020 annual growth rates:

- Kepulauan Mentawai: **1.36%**;
- Tanah Datar: **0.91%**;
- Solok Selatan: **2.27%**;
- Padang: **0.84%**;
- Bukittinggi: **0.81%**;
- Pariaman: **1.71%**.

The province aggregate published by BPS is **1.29%** per year; it is context only and is not included among the 19 kabupaten/kota source rows.

## Extraction integrity note

The official BPS publication page is the source authority. During this research session, the BPS publication download endpoint was not retrievable reliably through the available tooling. A search-indexed full-text representation of the same publication was used only as a **transcription carrier** to expose Table 3.1.1.

That transcription is not accepted on trust. Every target row is independently checked against:

1. official BPS SP2010 current-kabupaten/kota counts;
2. official BPS SP2020 current-kabupaten/kota counts;
3. BPS's geometric LPP methodology and the May-2010 → September-2020 interval;
4. the exact 19-code current Sumatera Barat geography registry.

All 19 published 2010–2020 rates reproduce to the published two-decimal values.

A later canonical materialization must cite BPS sources, not the transcription carrier, and should acquire/checksum a durable official publication artifact if the BPS download route becomes reliably retrievable.

## Evidence class

`population_growth` remains:

- `claim_type=derived`;
- source: official BPS-derived statistic;
- not a direct observed count;
- not a Ranah Observatory model estimate.

This distinguishes it from the SP2010/SP2020 population counts used as inputs.

## Promotion boundary

This PR qualifies the source contract but deliberately sets:

- `canonical_promotion_ready=false`;
- `canonical_promotion_performed=false`.

The next micro-milestone may materialize exactly 19 canonical `population_growth` rows only after defining durable provenance fields, reference interval representation, and collision checks against existing canonical data.

## Deliberately not included

This phase does not:

- use the var-484 2010 values to calculate growth;
- create annual interpolated population estimates;
- promote the province-level 1.29% as a kabupaten/kota value;
- add 2000–2010 rates to the canonical panel;
- silently call the growth rates `observed`;
- add any canonical observation yet.
