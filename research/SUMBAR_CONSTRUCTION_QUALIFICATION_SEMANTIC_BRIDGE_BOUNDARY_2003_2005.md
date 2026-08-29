# Sumatera Barat Construction Qualification Semantic Bridge Boundary, 2003–2005

## Research question

Can the detailed Sumatera Barat construction-establishment qualification classes published by BPS for 2003 — `B`, `M1`, `M2`, `K1`, `K2`, and `K3` — be collapsed into `Kecil`, `Menengah`, and `Besar` and then compared directly with the legacy BPS variable-216 labels for 2005?

## What is directly confirmed for 2003

The official BPS publication **Statistik Konstruksi 2004** (`05230.0506`, legacy catalogue `6513`, ISBN `979-724-383-4`) contains Table 4.3, **JUMLAH PERUSAHAAN KONSTRUKSI MENURUT KUALIFIKASI PER KABUPATEN TAHUN 2003**, for Sumatera Barat.

The source-native columns are:

- `B`
- `M1`
- `M2`
- `K1`
- `K2`
- `K3`
- `TOTAL`

The Sumatera Barat totals are:

| Class | Establishments |
|---|---:|
| B | 0 |
| M1 | 16 |
| M2 | 134 |
| K1 | 334 |
| K2 | 1,084 |
| K3 | 1,314 |
| **Total** | **2,882** |

This confirms the detailed six-class qualification composition as a source-native BPS publication construct for 2003.

## Arithmetic three-group candidate

If the six published cells are *only arithmetically* collapsed as:

- `Kecil = K1 + K2 + K3`
- `Menengah = M1 + M2`
- `Besar = B`

then the deterministic result is:

- Kecil: **2,732** (94.795281%)
- Menengah: **150** (5.204719%)
- Besar: **0**
- total: **2,882**

The three arithmetic components reconcile exactly to the published total.

This calculation is useful as a reproducible candidate representation, but it is **not** evidence that BPS itself defined the 2003 table in those three aggregate groups, and it is not a bridge to 2005.

## What is directly confirmed for 2005

The official legacy BPS machine-readable surface exposes variable `216`, **Banyaknya Perusahaan Konstruksi**, sourced to **Direktori Perusahaan Konstruksi**.

Its source-native period metadata includes:

- `2005`
- `th_id = 105`

Its derived-variable group **Jenis Golongan Perusahaan** identifies:

- `454` — Kecil
- `455` — Menengah
- `456` — Besar
- `457` — Jumlah

For Sumatera Barat, the 2005 `Jumlah` value is directly retrievable as **2,435** establishments.

However, bounded 2005 requests for Kecil, Menengah, and Besar are not available under the tested legacy dynamic-data contract, and the digital surface does not expose `B/M1/M2/K1/K2/K3` values for 2005.

## Why the semantic bridge remains closed

The labels are intuitively compatible, but that is not enough for a historical statistical bridge.

The evidence currently proves two different source-native representations:

1. **2003:** six detailed classes `B/M1/M2/K1/K2/K3`;
2. **2005:** metadata identities `Kecil/Menengah/Besar/Jumlah`, with only the total retrievable for Sumatera Barat.

No contemporaneous source has yet been recovered that explicitly states that variable-216's 2005 aggregate groups are formed by exactly:

- `Kecil = K1 + K2 + K3`;
- `Menengah = M1 + M2`;
- `Besar = B`.

This matters because the variable-216 source note itself states that construction-company classification rules changed multiple times. Later classification conventions therefore cannot be silently projected backward onto 2005.

The correct classification is:

`arithmetic_aggregation_candidate_reproducible_semantic_bridge_not_authorized`

## Research consequences

The following facts may be retained:

- the 2003 six-class composition is confirmed;
- the 2003 three-group arithmetic candidate is reproducible;
- the 2005 Sumatera Barat total of 2,435 is confirmed;
- variable 216 identifies Kecil/Menengah/Besar as derived variables for 2005 metadata.

The following remain unauthorized:

- treating the arithmetic 2003 grouping as source-native BPS aggregate data;
- assuming the same grouping definitions for 2005;
- calculating a 2003→2005 qualification-composition delta;
- inferring missing 2005 components from the total;
- treating establishment totals as sampling-frame counts;
- frame-change quantification;
- bridge or backcast;
- attribution of the 2001–2003 construction-value revision to the 2005 directory update;
- causal claims;
- bridged Panel v3 integration.

## Next evidence target

The semantic gate can be reconsidered only after recovering period-specific official evidence, preferably:

1. **Statistik Konstruksi 2005** (`05230.0607`, ISBN `979-724-567-5`) with the relevant qualification table and definitions;
2. **Profil Perusahaan Konstruksi di Luar Pulau Jawa 2005** (`05230.0610`, ISBN `979-724-565-9`) with Sumatera Barat qualification values and definitions; or
3. contemporaneous 2005 BPS/LPJK documentation that explicitly maps Kecil/Menengah/Besar to the six detailed qualification classes for the statistical series represented by variable 216.

Until then, the arithmetic candidate is retained only as a diagnostic transformation, not as a historical bridge.
