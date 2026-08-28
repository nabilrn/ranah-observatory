# Sumatera Barat Construction — Current CSA Table 652 Boundary

## Question

Can the current BPS Sumatera Barat statistical table **“Banyaknya Usaha/Perusahaan Konstruksi Menurut Kabupaten/Kota dan Kode Kualifikasi Usaha di Sumatera Barat”** supply the missing 2005 post-directory-update qualification composition needed for the historical construction revision investigation?

## Public page identity

The current BPS Sumatera Barat page uses the statistics-table URL identity:

`NjUyIzI=`

Base64-decoding that value gives:

`652#2`

This identity must not be interpreted as legacy WebAPI `statictable` ID `652`. A bounded probe confirmed that legacy `statictable` 652 is `not-available` in domain `1300`.

The current website instead resolves through the CSA statistics-table model:

- endpoint family: `https://webapi.bps.go.id/v1/api/view`
- model: `tablestatistic`
- domain: `1300`
- language: `ind`
- ID: `NjUyIzI=`

The official CSA response is available and reproduces the target title.

## What the CSA object actually contains

The object exposes only one source-native year:

- **2016** (`val = 116`)

It does **not** expose 2005.

The source-native variable metadata are:

- variable ID: `652`
- unit: `Usaha`
- subject text: `Sensus Ekonomi`
- geography dimension: `Kabupaten/Kota`
- 19 kabupaten/kota rows plus one Sumatera Barat provincial total row.

The qualification categories are:

- Perseorangan
- K1
- K2
- K3
- M1
- M2
- B1
- B2
- Lainnya
- Jumlah

For the Sumatera Barat provincial total in 2016, the response reports:

| Category | Count |
|---|---:|
| Perseorangan | 4,106 |
| K1 | 482 |
| K2 | 143 |
| K3 | 82 |
| M1 | 210 |
| M2 | 32 |
| B1 | 14 |
| B2 | 7 |
| Lainnya | 790 |
| Jumlah | 5,866 |

The nine component categories sum exactly to `5,866`.

## Why this does not solve the 2005 gate

The historical pre-update baseline frozen from `Statistik Konstruksi 2004` publishes Sumatera Barat 2003 categories as:

`B, M1, M2, K1, K2, K3`

The current 2016 CSA table instead separates `B1/B2` and adds `Perseorangan` and `Lainnya`. Its own source field says `Sensus Ekonomi`, and its only available year is 2016.

Therefore this table is useful for two bounded conclusions only:

1. the current BPS page is a real machine-readable CSA object and is no longer a transport mystery; and
2. it is **not** the missing 2005 post-directory-update source and must not be used as a proxy for that period.

Shared category names such as `K1`, `K2`, `K3`, `M1`, and `M2` do not by themselves prove identical definitions across 2003 and 2016.

## Historical revision boundary remains unchanged

This checkpoint does not authorize:

- a 2003-to-2005 qualification-composition comparison;
- use of 2016 as a substitute for 2005;
- frame-change quantification;
- reconstruction of old/new Sumatera Barat sampling-frame counts;
- attribution of the 2001–2003 construction-value revision to the end-2005 directory updating;
- a cross-vintage bridge or backcast;
- bridged Panel v3 integration;
- a causal claim.

The next useful source must explicitly expose **2005** Sumatera Barat post-update qualification counts with enough period-specific definition context to test comparability. Book II `05230.0610` remains the preferred target, but another contemporaneous official BPS reproduction is acceptable.

## Reproducibility

The exact CSA response was obtained through a GitHub Actions run using the repository's existing BPS WebAPI secret. The API key was not persisted. The canonicalized response hash and workflow provenance are frozen in:

`data/validation/historical/public_finance_2000/bps_construction_current_csa_table_652_boundary.json`
