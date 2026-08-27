# Sumbar 2000 construction-financing composition

## Decision

Ranah Observatory now preserves the complete BPS source-native financing decomposition for construction completed in Sumatera Barat in 2000.

The source concept is **construction value completed by construction establishments, classified by source of financing**. It is not a government-budget composition and is not a fiscal-account decomposition.

All values below use the source unit `000 Rupiah`.

| Source concept | Table | Value | Share of total |
|---|---:|---:|---:|
| Total construction completed | 14 | 345,371,439 | 100.000000% |
| APBN financing | 15.1 | 207,997,331 | 60.224242% |
| APBD financing | 15.2 | 39,956,642 | 11.569180% |
| Foreign-loan financing | 15.3 | 76,727,103 | 22.215822% |
| BUMN financing | 15.4 | 1,229,691 | 0.356049% |
| Other financing sources | 15.5 | 19,460,672 | 5.634708% |

Exact unit scaling gives total nominal completed-construction value of **IDR 345,371,439,000**.

## Exact arithmetic reconciliation

The five financing components reconcile exactly to the independently published total:

`207,997,331 + 39,956,642 + 76,727,103 + 1,229,691 + 19,460,672 = 345,371,439`

The difference between the component sum and Table 14 total is exactly zero in source units.

APBN plus APBD financing equals `247,953,973` thousand rupiah, or approximately `71.793422%` of the total under this BPS construction-financing concept. This percentage describes financing sources of completed construction only; it does not measure the share of government spending devoted to construction.

Independently rounded component shares sum to `100.000001%`; this is rounding noise only. Exact source values reconcile without residual.

## Primary evidence

The primary source is BPS `Statistik Konstruksi 2002`, released 15 September 2003.

Relevant tables are:

- Table 14, printed page 46 — total value of construction completed by province;
- Table 15.1, printed page 62 — APBN financing;
- Table 15.2, printed page 63 — APBD financing;
- Table 15.3, printed page 64 — foreign-loan financing;
- Table 15.4, printed page 65 — BUMN financing;
- Table 15.5, printed page 66 — other sources of financing.

The tables carry the note `Angka Sementara/Preliminary Figures`.

## Cross-publication verification

BPS `Statistik Konstruksi 2003`, released 19 July 2004, republishes the same table family. For Sumatera Barat, every 2000 value listed above—including the independently reported total—matches the 2002 publication exactly.

The later publication visibly marks historical year headers with `R`. This checkpoint retains that source marker but does not assign it a meaning without an explicit source definition.

The exact cross-publication match materially strengthens the 2000 observation family while not converting preliminary source data into a final fiscal-account record.

## Semantic boundary

The composition must not be relabelled as any of the following:

- government-budget composition;
- APBD expenditure composition;
- DJPK fiscal realization accounts;
- `Belanja Modal` / `capital_expenditure`;
- public-investment composition;
- gross fixed capital formation by institutional sector;
- construction-sector GRDP value added.

The reason is structural: BPS is classifying **completed construction output by financing source**. DJPK instead records **government fiscal accounts**. Similar financing labels do not establish metric equivalence.

The foreign-loan category also does not identify the debtor, borrower, guarantor, or fiscal incidence. No such institutional interpretation is inferred.

## Geography boundary

Only the source-era Sumatera Barat province aggregate is qualified and associated with historical geography `idn.13.h1958`. No current-district allocation or historical-to-current boundary reconstruction is performed.

## Evidence-surface boundary

Evidence is drawn from official BPS publication metadata and the official BPS AllStats/Deep Search full-text index. The exact publication PDFs are not SHA-fingerprinted in this checkpoint because current BPS access blocks GitHub-hosted cloud runners.

Therefore:

- indexed BPS table text is treated as table-level numeric evidence;
- indexed text is not treated as equivalent to possession of a SHA-bound PDF artifact;
- raw PDFs are not committed;
- the separate zero-hit `public_finance` finding inside the SHA-bound `Sumatera Barat Dalam Angka Tahun 2000` yearbook remains unresolved.

## Allowed use

This checkpoint authorizes:

- source-native description of the 2000 construction-financing composition;
- arithmetic statements derived directly from the five exact component values and total;
- source-native shares of total construction value;
- later within-family historical comparison when adjacent years are separately reviewed for revisions.

It does not authorize:

- Panel v3 integration;
- fiscal-account mapping;
- causal claims about government spending and growth;
- deflation or constant-price comparison without a separately defined price methodology;
- interpolation into missing years;
- treating APBN + APBD financing as government expenditure.

## Next gate

The high-value continuation is to qualify adjacent years in the same table family and explicitly measure publication-to-publication revisions. That can establish whether a defensible source-native financing trajectory exists before any downstream historical analysis is attempted.
