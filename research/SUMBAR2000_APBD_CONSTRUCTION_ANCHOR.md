# Sumbar 2000 APBD-financed construction anchor

## Decision

A BPS source-native historical observation is qualified for **Sumatera Barat, 2000**:

- source measure: `Nilai konstruksi yang diselesaikan dari sumber dana APBD`;
- English source label: `Value of completed construction financed by local government budget`;
- source unit: `000 Rupiah`;
- source value: `39,956,642`;
- exact normalized nominal value: `IDR 39,956,642,000`.

This observation is **not** promoted to a canonical fiscal indicator and is **not** integrated into Panel v3.

## Primary evidence

BPS `Statistik Konstruksi 2002` contains Table 15.2 on printed page 63. The table reports completed construction financed by local-government budget sources by province for 1998–2002.

For Sumatera Barat the source row is:

| Year | Value (`000 Rupiah`) |
|---:|---:|
| 1998 | 47,227,148 |
| 1999 | 26,004,489 |
| 2000 | **39,956,642** |
| 2001 | 46,038,043 |
| 2002 | 53,045,033 |

The table note says `Angka Sementara/Preliminary Figures`.

Publication metadata:

- publisher: Badan Pusat Statistik;
- publication: `Statistik Konstruksi 2002`;
- current BPS catalog number: `6301003`;
- source-native PDF catalog number visible in the indexed publication: `6513`;
- publication number: `05230.0307`;
- release date: 2003-09-15.

## Independent annual-publication cross-check

BPS `Statistik Konstruksi 2003` repeats Table 15.2 on printed page 63 with year headers `1999 R`, `2000 R`, `2001 R`, `2002`, and `2003`.

For Sumatera Barat it reports:

| Year | Value (`000 Rupiah`) |
|---:|---:|
| 1999 | 26,004,489 |
| 2000 | **39,956,642** |
| 2001 | 46,038,043 |
| 2002 | 53,045,032 |
| 2003 | 54,260,376 |

The 2000 value is therefore an exact cross-publication match. The adjacent 2002 value changes by one thousand rupiah between the two publications, which demonstrates that later annual tables can revise historical entries while the 2000 value remained stable in this comparison.

The `R` marker is retained as source text. This checkpoint does not infer its meaning without an explicit source definition.

## Semantic boundary

The source measure is a construction-industry output measure classified by financing source. It must not be relabelled as:

- total APBD expenditure;
- APBD `Belanja Modal` / DJPK `capital_expenditure`;
- infrastructure budget appropriation;
- infrastructure expenditure realization;
- total public investment.

The modern DJPK lane in Ranah Observatory uses exact fiscal-account labels and recorded fiscal realization. That accounting concept is materially different from BPS construction value grouped by funding source. No bridge is authorized simply because both contain the term APBD.

## Geography boundary

Only the source-era Sumatera Barat province aggregate is used. The observation is associated with historical province geography `idn.13.h1958` and is not projected onto current kabupaten/kota.

## Evidence surface boundary

This checkpoint uses official BPS publication metadata and the official BPS AllStats/Deep Search full-text index. The exact publication PDFs are not committed or SHA-fingerprinted in this checkpoint because current BPS access blocks GitHub-hosted cloud runners.

Therefore:

- AllStats text is accepted as table-level numeric evidence;
- AllStats text is **not** treated as an artifact-SHA substitute;
- raw PDF remains absent;
- canonical promotion remains fail-closed.

This external national BPS source does not resolve the zero-hit `public_finance` discovery result inside the separately SHA-bound `Sumatera Barat Dalam Angka Tahun 2000` yearbook.

## Allowed use

Allowed now:

- source-native historical evidence;
- historical descriptive discussion with the exact source concept and unit;
- later comparison to similarly defined BPS construction-financing tables if separately qualified.

Not allowed now:

- Panel v3 integration;
- chaining to DJPK `capital_expenditure`;
- inflation-adjusted or real-value claims without a separately specified deflator and methodology;
- interpolation between 2000 and modern fiscal years;
- treating the value as the size of the Sumatera Barat APBD.

## Next gate

When BPS artifact access permits, acquire and fingerprint the exact publication PDFs and bind the table transcription to artifact hashes. Any canonical bridge to a fiscal-account or public-investment indicator requires a separate semantic qualification rather than label matching.
