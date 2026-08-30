# Historical Reconstruction Protocol

## Purpose

Ranah Observatory cannot answer long-run questions about Sumatera Barat by projecting today's province and kabupaten boundaries backward through time. The early-independence period contains changes in territorial administration, statistical institutions, source availability, and measurement practice that are themselves part of the evidence.

This phase therefore builds a **source-era timeline first**. Historical observations remain attached to the geography and statistical definition used by their source until a separately documented reconstruction is justified.

## Evidence hierarchy for historical claims

Prefer, in order:

1. contemporaneous laws, regulations, decrees, census publications, and official statistical publications;
2. official BPS WebAPI snapshots whose metadata identifies the historical source family;
3. official government/BPS archival catalogues that identify contemporaneous holdings;
4. later official publications that reproduce or explain earlier legal/statistical history;
5. scholarly archival work when primary material is unavailable;
6. secondary narrative only as a discovery lead, never as the sole basis for a canonical boundary or numeric observation when stronger evidence can reasonably be sought.

A modern website timestamp is not the historical event date. The repository records the date represented by the source and retains the modern retrieval location only as provenance.

## Current legal-geography anchors

### 1947 — Sumatra as an autonomous region

BPK's official legal database records PP No. 8 Tahun 1947, *Pemerintahan di Sumatra, Sebagai Daerah Otonomi*, effective 28 April 1947.

This is currently the earliest qualified post-independence legal anchor in the repository. It does not resolve the entire 1945–1946 administrative sequence and must not be used to pretend that the same structure existed continuously from 17 August 1945.

### 1948 — legal division of Sumatra

UU No. 10 Tahun 1948 is titled *Pembagian Sumatra dalam Tiga Propinsi*. BPK records enactment and promulgation on 15 April 1948 but leaves the effective-date metadata blank.

The event register therefore records 15 April 1948 as the enactment/promulgation date, not as an invented independent effective date.

The successor province concepts relevant to this project include Sumatera Tengah. Numerical observations labelled for the larger pre-division Sumatra unit must not be relabelled as Sumatera Tengah or Sumatera Barat.

### 1950 — Propinsi Sumatera Tengah

BPK records Perpu No. 4 Tahun 1950, *Pembentukan Propinsi Sumatera Tengah*. Its page provides the year but no enactment, promulgation, or effective date.

The canonical register therefore stores this event at **year precision**. A blank date is evidence of uncertainty, not a field to be guessed from secondary sources.

### 1957 — Sumatera Barat, Jambi, and Riau

UU Darurat No. 19 Tahun 1957 created the Tingkat I regions Sumatera Barat, Jambi, and Riau. BPK records enactment on 9 August 1957 and effect from 10 August 1957, and lists Perpu No. 4 Tahun 1950 as revoked.

A value for Sumatera Tengah before the reorganisation is **not** an observation for Sumatera Barat after the reorganisation merely because much of present-day Sumatera Barat lay within it.

### 1958 — confirmation and constituent-area detail

UU No. 61 Tahun 1958 confirmed UU Darurat No. 19 Tahun 1957 as law with changes. Its official abstract enumerates the constituent kabupaten and kotapraja relevant to the reorganisation.

The registry now contains `idn.13.h1958`, a source-era Sumatera Barat province version anchored to 31 July 1958. No end date or automatic equivalence with the current boundary is asserted.

When historical area membership is reconstructed at Tingkat II, this law and the underlying 1956/1957 instruments are preferred over modern boundary assumptions.

## Statistical-system anchors

Official BPS institutional history records that Kantor Pusat Statistik became Biro Pusat Statistik effective 1 June 1957 under Keppres No. 172 Tahun 1957. It also records that UU No. 6 Tahun 1960 on census and UU No. 7 Tahun 1960 on statistics replaced colonial-era ordinances, and that the 1961 Population Census was the first population census after independence.

A long-run series can span administrations and statistical regimes only when concepts and collection methods are explicitly checked.

## 1961 Population Census: a hard boundary warning

The official publication *Sensus Penduduk 1961 Republik Indonesia* states that population-density figures could be presented only at Daerah Tingkat I, not Tingkat II, because kabupaten areas were changing and required further study.

Ranah Observatory treats this statement as an enforceable comparability constraint:

- province/Tingkat I population observations may be usable after table-level verification;
- kabupaten counts may be usable if the source explicitly supplies them and their geography is retained;
- density, area-standardized metrics, or cross-year Tingkat II comparisons must not be reconstructed using modern areas by default;
- any historical area denominator must have its own provenance and boundary version.

## 1971 BPS WebAPI census anchor

BPS WebAPI variable `484`, *[Hasil Sensus dan SUPAS] Jumlah Penduduk Menurut Jenis Kelamin dan Kabupaten/Kota di Sumatera Barat*, explicitly states that 1971, 1980, 1990, 2000, 2010, and 2020 are sourced from Population Censuses, while 1995, 2005, and 2015 are sourced from SUPAS.

The exact 1971 response is frozen at `data/snapshots/bps/var-484-1971.json` with SHA-256 `b0d808a6b59b018c7a28f5d47b882f17248eb9ae2d0b05a6acb62366ca2813e1`.

For the total-sex category (`turvar=34`):

- the province total is **2,789,822 persons**;
- fourteen local total rows are present in `datacontent`;
- those fourteen local totals sum exactly to the province total;
- current-looking labels/codes for later split units may appear in response metadata, but missing 1971 values are not synthesized;
- only the province aggregate is currently mapped to `idn.13.h1958`;
- local 1971 rows remain `historical_geography_pending` and are not mapped directly to the 19 current kabupaten/kota.

This is the first frozen historical numeric family in the repository with source-era provenance. It satisfies the historical-foundation numeric extraction gate without claiming that the local administrative units are already harmonized.

The source also creates an explicit cross-source conflict: BPS WebAPI reports Bukittinggi population `63,356` for 1971, while a later official Bukittinggi annual publication candidate reproduces `63,132`. The repository records both in the anomaly register and does not average, overwrite, or silently prefer one source family outside its qualified context.

## Available late-1960s statistical anchors

BPS currently exposes official digital publication pages for:

- *Statistical Pocketbook of Indonesia 1964-1967*;
- *Statistical Pocketbook of Indonesia 1968-1969*;
- *Sensus Penduduk 1961 Republik Indonesia*;
- the 1971 census publication series, useful as an independent cross-check on the WebAPI family.

The BPS digital library catalogue also records a softcopy holding for *Provinsi Sumatera Barat Dalam Angka 1970*. Regional publication pages separately verify the 1970 annual volume and subsequent anchors.

These sources provide a bridge from early-independence reconstruction into the regular `Sumatera Barat Dalam Angka` era without pretending that the coverage is continuous.

## Explicit unresolved periods

### 1945–1946

No primary source has yet been qualified in this repository for the exact administrative sequence covering the area that later became Sumatera Barat. This is an **open research gap**.

Until resolved:

- do not assign current Sumatera Barat boundaries to 1945 or 1946;
- do not create synthetic `Sumatera Barat` observations from broader Sumatra statistics;
- secondary descriptions may generate search terms but cannot create canonical geography records.

### 1951–1960 statistical series

The legal-geography sequence is increasingly constrained, but a comprehensive pre-1961 statistical publication inventory has not yet been qualified. BPS library holdings, national statistical compilations, regional government archives, and archival collections remain targets.

The 1961 census publication remains a P0 acquisition target because it can move the population anchor a decade earlier than the currently frozen 1971 WebAPI family.

## Reconstruction states

Every historical value should be in exactly one of these states:

- `observed_source_era`: extracted without changing the source geography or definition;
- `derived_source_era`: calculated from compatible source-era inputs without geographic harmonisation;
- `reconstructed_geography`: allocated or combined across geography versions using an explicit crosswalk;
- `reconstructed_definition`: transformed across category/definition systems using an explicit mapping;
- `not_comparable`: retained as evidence but excluded from a continuous analytical series.

`reconstructed_geography` and `reconstructed_definition` are never silently downgraded to `observed`.

## Crosswalk policy

A historical crosswalk may be created only when its evidence identifies the relationship sufficiently to support the intended operation.

Examples:

- legal containment can support membership statements but not population allocation weights;
- a split law can identify successor units but does not reveal how a historical statistic should be divided;
- area weights require compatible historical geometry or defensible area evidence;
- population weights require a temporally relevant population source;
- an unknown weight remains unknown.

No `1/n` equal split is allowed merely because there are `n` successor units.

## Extraction record minimum

A historical source record should retain the fields appropriate to its artifact type.

For publication tables this includes:

- source record ID;
- artifact checksum/version;
- page number;
- table number/title;
- row/column labels exactly as printed;
- source-era geography label;
- reference period;
- unit;
- numeric/text value;
- extraction method;
- transcription/reconstruction confidence;
- definition/boundary notes;
- canonical indicator mapping status.

For BPS WebAPI snapshots this includes:

- exact snapshot checksum;
- API domain and source variable ID;
- `vervar`, `turvar`, `th`, and `turth` IDs and labels;
- source `last_update` metadata;
- retrieval timestamp;
- source key and value;
- source-era mapping status;
- any cross-source conflict.

OCR output is evidence for review, not automatically a canonical observation.

## Immediate analytical consequence

The initial long-run panel should **not** start in 1945 merely because the project aspires to cover the independence era. Each indicator starts at the earliest point where its geography and definition can be defended.

For example:

- historical population now has a validated province-level 1971 census anchor; 1961 remains the next earlier target;
- regular multi-domain Sumatera Barat annual publication extraction may anchor at 1970 where definitions are qualified;
- a historical qualitative/legal timeline can extend to 1947 with current primary evidence;
- 1945–1946 remain visible as research gaps rather than fabricated rows.

This produces a panel with uneven start dates but substantially higher evidentiary quality than a cosmetically complete time series.

## Exit criteria for this phase

Before historical reconstruction is considered mature enough for baseline EDA:

- legal geography events are machine-readable and source-linked;
- unresolved periods remain explicitly represented as gaps;
- 1961 boundary warnings are enforced in methodology/validation;
- representative 1960s and 1970 publication anchors are registered;
- table/API extraction contracts exist;
- at least one historical indicator family is extracted with source-era provenance;
- no harmonised historical value is indistinguishable from a direct observation.

The **historical-foundation exit gate is now satisfied** by the validated 1971 BPS census snapshot and source-native population family. This does not mean historical reconstruction is complete: the 1961 census, local boundary lineage, pre-1961 statistics, and publication cross-checks remain active research tasks.
