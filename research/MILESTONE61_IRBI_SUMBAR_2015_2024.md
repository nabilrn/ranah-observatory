# Milestone 61 — BNPB IRBI Sumatera Barat 2015–2024

## Outcome

M61 materializes the official BNPB Disaster Risk Index (IRBI) for all 19 current Sumatera Barat regencies/cities from 2015 through 2024.

The result is a 190-row canonical risk-index timeseries suitable for a clean regional risk map and proof table. It is intentionally kept separate from disaster-event counts and from forecast outputs.

## Official source

The source is BNPB's `Indeks Risiko Bencana Indonesia Tahun 2024` publication.

The Sumatera Barat section provides:

- page 66: province-level IRBI trend 2015–2024 and the 2024 province class;
- page 67: 19 kabupaten/kota × 10 annual IRBI scores and the 2024 risk class for each district/city.

The frozen source-native table is acquired from the official InaRISK basic-HTML representation of page 67. The official BNPB PDF is the publication-level reference.

## Footprint

- 19 kabupaten/kota;
- 10 years: 2015–2024;
- 190 district-year observations;
- 2024 risk classes: 8 `tinggi`, 11 `sedang`, 0 `rendah`.

The 2024 highest-score group consists of Agam, Pasaman Barat, Kepulauan Mentawai, Pasaman, Kota Padang, Kota Pariaman, Padang Pariaman, and Pesisir Selatan; these are the eight rows classified `TINGGI` by the source.

## Province reconciliation

BNPB reports the Sumatera Barat province series on page 66 as:

`153.16, 153.16, 151.56, 151.56, 150.24, 149.53, 147.36, 144.39, 144.38, 142.55`

for 2015–2024 respectively, with 2024 classified `SEDANG`.

The mean of the 19 district/city scores for each year, rounded to two decimals, reproduces every one of those province values exactly. This is consistent with the methodology statement that provincial IRB is the average of district/city IRB values.

## Methodology boundary

IRBI is a composite risk index based on:

- hazard;
- vulnerability;
- capacity.

The 2024 publication states that hazard and vulnerability are treated as baseline components while regional capacity is calculated periodically and is the principal component driving year-to-year IRBI changes. Therefore:

- a lower annual IRBI score can be described as lower composite disaster risk under the IRBI methodology;
- a yearly change must **not** be described as proof that the physical hazard itself increased or decreased;
- IRBI is not an observed disaster-event count;
- IRBI is not a forecast of how many disasters will occur next year.

## Dashboard contract

M61 authorizes:

- a 2015–2024 regional risk timeseries;
- a 2024 choropleth/map using the 19 official IRBI scores;
- the official 2024 district/city risk classes;
- the province trend as a reconciliation/proof context;
- sorting/filtering by area, year, score, and 2024 risk class.

M61 does not authorize:

- hazard-specific risk scores;
- causal attribution of score changes to weather, earthquakes, or event frequency;
- prediction labels such as “will flood next year”;
- substitution of IRBI for BPBD/BNPB event observations;
- treating index points as percentages or probabilities.

## Product relevance

This dataset fills the dashboard's **risk/potential** layer with a source that is much more defensible than attempting to infer future danger from raw event frequency alone. It can be shown alongside event, impact, loss, rainfall, and topography evidence while retaining clear semantic boundaries.
