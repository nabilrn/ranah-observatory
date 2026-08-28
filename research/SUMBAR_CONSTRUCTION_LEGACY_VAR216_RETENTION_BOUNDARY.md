# Sumatera Barat Construction — Legacy Variable 216 Retention Boundary

## Question

Can the official BPS machine-readable system recover the missing **2005** Sumatera Barat construction-establishment qualification composition, or at least explain why the already-confirmed 2005 total is visible while the component strata remain missing?

## Legacy BPS variable recovered

A bounded search of the official central BPS WebAPI found one construction variable with an explicit source-native 2005 period:

- subject: `Konstruksi`
- variable ID: `216`
- title: **Banyaknya Perusahaan Konstruksi**
- source: **Direktori Perusahaan Konstruksi**
- annual periods: **2000–2025**
- 2005 period ID: `105`

The same variable defines one derived-variable group, **Jenis Golongan Perusahaan**, with:

- `454` — Kecil
- `455` — Menengah
- `456` — Besar
- `457` — Jumlah

This is the strongest surviving official machine-readable identity found so far for the historical construction-directory series.

## The 2005 Sumatera Barat total is directly retrievable

Using the legacy dynamic-data contract with:

- domain `0000`
- variable `216`
- period `105` = 2005
- derived variable `457` = Jumlah
- annual derived period `0`

BPS returns a `38 Provinsi` geography dimension containing:

- `1300` — `SUMATERA BARAT`

The corresponding data-content key is:

`13002164571050`

and its value is:

**2,435 construction establishments**.

This independently reproduces the already-frozen 2005 Sumatera Barat total from the historical BPS table `Jumlah Perusahaan Konstruksi Menurut Propinsi`.

The response reports `last_update = 2025-12-31 06:32:26`.

## Why the 2005 component composition is still missing

The legacy metadata clearly knows the component strata `Kecil`, `Menengah`, and `Besar`. However, bounded requests for the 2005 selections:

- `turvar=454` — Kecil
- `turvar=455` — Menengah
- `turvar=456` — Besar

all return **data not available** under the tested legacy dynamic-data contract.

That result must be interpreted narrowly. It means those component values are **not exposed through this tested API selection**. It does **not** prove that the underlying 2005 directory publication lacked the component counts.

## Current CSA table confirms a retention-window split

The public BPS page for the same statistical product is:

`https://www.bps.go.id/id/statistics-table/2/MjE2IzI=/banyaknya-perusahaan-konstruksi.html`

The encoded identity `MjE2IzI=` decodes to:

`216#2`

The official CSA `tablestatistic` object is available and uses the same:

- variable ID `216`
- title `Banyaknya Perusahaan Konstruksi`
- source `Direktori Perusahaan Konstruksi`
- derived variables Kecil / Menengah / Besar / Jumlah

But its `available_years` are only:

**2016–2025**.

Therefore the two official BPS machine-readable surfaces have different historical retention:

| Surface | Historical coverage relevant here | 2005 total | 2005 Kecil/Menengah/Besar |
|---|---|---:|---:|
| Legacy variable/period API | 2000–2025 period metadata | available | not available under tested selection |
| Current CSA `216#2` | 2016–2025 | not exposed | not exposed |

The bounded classification is therefore:

**legacy total survives before the current CSA component-retention window**.

## What this adds to the revision investigation

This checkpoint materially narrows the evidence problem.

We no longer need to ask whether BPS has a persistent machine-readable historical identity for the construction-directory count series: it does. Variable `216` explicitly reaches back to 2000 and directly reproduces Sumatera Barat 2005 total `2,435`.

The remaining missing evidence is more specific: **the 2005 component composition** and the period-specific semantics needed to compare it with the 2003 six-category baseline.

This also prevents a misleading inference from the current website. The absence of 2005 from CSA `216#2` is a current digital-retention limitation, not evidence that the historical series did not exist.

## Category-mapping caution

Modern BPS construction directories explicitly group:

- K1/K2/K3 as **Kecil**
- M1/M2 as **Menengah**
- B1/B2 as **Besar**

But the 2003 Sumatera Barat baseline uses `B, M1, M2, K1, K2, K3`, and qualification rules changed over time.

Therefore this checkpoint does **not** authorize silently aggregating the 2003 baseline into Kecil/Menengah/Besar and comparing it with an eventual 2005 aggregate result. A period-specific 2003/2005 mapping must be evidenced first.

## Gates that remain closed

This checkpoint does not authorize:

- a 2003-to-2005 qualification-composition delta;
- inferred Kecil/Menengah/Besar values for 2005;
- use of 2016–2025 composition as a proxy for 2005;
- sampling-frame change quantification;
- attribution of the earlier construction-value revision to the end-2005 directory updating;
- a cross-vintage bridge or backcast;
- a causal claim;
- Panel v3 integration.

## Next useful evidence

The highest-value next sources are now tightly defined:

1. Book II `05230.0610` or another contemporaneous official BPS reproduction containing Sumatera Barat 2005 qualification counts;
2. another official BPS transport that exposes 2005 `Kecil / Menengah / Besar` for variable `216`; or
3. period-specific BPS/LPJK documentation that proves the exact aggregation relationship between the 2003 six categories and the 2005 size groups.

## Reproducibility

The source responses were obtained through GitHub Actions using the repository's existing BPS WebAPI secret. The API key was not persisted.

Permanent hashes and workflow provenance are frozen in:

`data/validation/historical/public_finance_2000/bps_construction_legacy_var216_retention_boundary.json`
