# Milestone 43 — BNPB Historical Semantics and Temporal-Geography Gate

## Status

**The 2000–2017 BNPB Sumatera Barat archive is now qualified for source-reported archival display with provenance, but it is still not authorized as a canonical longitudinal district/city panel.**

M42 proved that the full 2000–2017 archive is technically stable enough to stage: 18/18 annual workbooks were audited, 17 non-empty workbooks reconcile their explicit `Jumlah` rows across all 14 metric columns, and 202 source geography rows / 2,828 metric cells were materialized without zero-filling missing rows. M43 addresses the next failure mode: a structurally stable table can still be semantically non-comparable across time.

The machine-readable gate is frozen at:

`data/manifests/milestone43_bnpb_historical_semantics_geography_gate.json`

## Structural continuity is not semantic continuity

The archive repeatedly exposes the same 14 source metrics:

- `Jumlah Kejadian`
- `Meninggal`
- `Hilang`
- `Terluka`
- `Menderita`
- `Mengungsi`
- `Rusak Berat`
- `Rusak Sedang`
- `Rusak Ringan`
- `Terendam`
- `Pendidikan`
- `Kesehatan`
- `Peribadatan`
- `Umum`

M42 proves those columns are structurally present and numerically parseable. It does **not** prove that BNPB used an identical operational definition, event threshold, verification procedure, deduplication rule, damage threshold, or facility inclusion rule in every year from 2000 through 2017.

M43 therefore separates:

1. **source identity** — what the archive literally reports;
2. **conceptual successor mapping** — the closest current BNPB concept, where one exists;
3. **semantic equivalence** — a stronger claim that remains blocked until value-level overlap evidence supports it.

## Evidence timeline for disaster-data semantics

The official evidence is not temporally uniform across the archive window.

### 2011 — Standardisasi Data Kebencanaan

BNPB issued Perka No. 8 Tahun 2011 on standardization of disaster data. The current JDIH page marks the regulation as no longer in force:

`https://jdih.bnpb.go.id/dokumen/Peraturan/perka-nomor-8-tahun-2011`

This is a useful historical definition reference, but it cannot prove that annual workbooks from 2000–2010 were generated under exactly those rules.

### 2012 — Pedoman Pengelolaan Data dan Informasi Bencana Indonesia

BNPB issued Perka No. 7 Tahun 2012:

`https://jdih.bnpb.go.id/dokumen/Peraturan/perka-nomor-7-tahun-2012`

The current JDIH page also marks this regulation as no longer in force. Its adoption in 2012 is direct evidence against projecting one formally documented data-management regime backward over the entire 2000–2017 archive without qualification.

### 2023 — Satu Data Bencana

The current Satu Data governance reference is Perban BNPB No. 1 Tahun 2023:

`https://jdih.bnpb.go.id/dokumen/Peraturan/perban-nomor-1-tahun-2023`

Current governance helps interpret modern resources, but it is not evidence that historical counting practice was unchanged.

## Victim-category semantics

BPS SiRuSa metadata, citing BNPB's disaster-data standardization framework, provides official-government definitions for core victim concepts:

`https://sirusa.web.bps.go.id/metadata/indikator/1107`

The metadata distinguishes:

- **Meninggal** — people reported dead or deceased due to disaster;
- **Hilang** — people reported missing, not found, or whose whereabouts are unknown after disaster;
- **Terdampak** — people suffering adverse impacts while still able to occupy their residence;
- **Terluka/Sakit** — injured or ill people, from light to severe cases and outpatient to inpatient treatment;
- **Mengungsi** — people forced to leave their residence for a safer place due to disaster impacts.

The current BNPB Satu Data historical resources for 2010–2024 also expose `Terdampak` and `Mengungsi` as separate resources:

- dataset: `https://data.bnpb.go.id/dataset/data-bencana-indonesia`
- Terdampak: `https://data.bnpb.go.id/dataset/data-bencana-indonesia/resource/7f9e5218-bbba-4916-a2b8-13cf1764dc96`
- Mengungsi: `https://data.bnpb.go.id/dataset/data-bencana-indonesia/resource/d7b61b56-43d5-4dcc-8d7b-45c993e1bdb0`

### `Menderita` is not silently renamed to `Terdampak`

The M42 archive uses the historical field `Menderita`, whereas current BNPB publishing uses `Terdampak`.

M43 records `Terdampak` only as a **candidate conceptual successor**. It does not authorize a lossless rename. Before `Menderita` can become `Terdampak` in a canonical panel, M44 must reconcile overlapping 2010–2017 values and determine whether the fields behave equivalently in genuinely like-for-like slices.

Until then, public or analytical outputs must preserve the historical label `Menderita`.

### Victim categories are not unique-person arithmetic

Public BNPB historical summaries provide an additional warning. For example, the 2017 disaster-data book presents grouped display headings such as `Meninggal & Hilang` and `Menderita & Mengungsi`:

`https://bnpb.go.id/storage/app/media/uploads/24/buku-data-bencana/buku-data-bencana-2017-compressed.pdf`

This grouped presentation does not prove that the underlying source columns are merged. It does prove that consumers cannot safely infer mutual exclusivity or unique-person additivity from adjacent victim categories.

M43 therefore prohibits statements such as:

`unique victims = meninggal + hilang + terluka + menderita + mengungsi`

Annual aggregates may also contain repeated people across separate events. Source-reported category counts remain valid archival observations; unique-person totals do not.

## Physical-impact semantics

The current BNPB 2025 combined dictionary separates modern fields for:

- Rumah Rusak Berat
- Rumah Rusak Sedang
- Rumah Rusak Ringan
- Satuan Pendidikan Rusak
- Rumah Ibadat Rusak
- Fasilitas Pelayanan Kesehatan Rusak
- Kantor Rusak
- Jembatan Rusak

Reference:

`https://data.bnpb.go.id/dataset/kompilasi-data-kejadian-dan-dampak-bencana-2025/resource/6e947c9c-2404-4c02-b743-34dc5320f399`

This provides useful current concept labels, but it does not prove unchanged thresholds or asset-counting rules for the 2000–2017 archive.

### House-damage counts

`Rusak Berat`, `Rusak Sedang`, and `Rusak Ringan` can be retained as archive-reported annual unit counts. M43 does not authorize:

- assuming identical damage-severity thresholds in every archive year;
- assuming the annual sum is a deduplicated count of unique physical houses across multiple events;
- converting unit counts into monetary loss without independent valuation evidence.

### `Terendam`

The historical archive contains `Terendam` as a separate field. A flooded house may conceptually overlap with a damaged house, and the current direct successor field has not been frozen. `Terendam` therefore remains its own historical category and is not added to the three damage-severity classes as if all four were mutually exclusive.

### Facility `Umum` is arithmetically ambiguous

The historical table contains four facility-related columns:

- `Pendidikan`
- `Kesehatan`
- `Peribadatan`
- `Umum`

A 2017 BNPB public summary describes damaged *fasilitas umum* as an umbrella total and then breaks it into education, worship, and health facilities. That communication pattern creates two competing interpretations for the historical `Umum` field:

1. `Umum` may be a separate residual category; or
2. `Umum` may act as a broader/aggregate concept related to the three specific facility categories.

M43 authorizes neither interpretation without value-level proof. In particular:

- do not add `Umum` to the three specific facility columns as a fourth disjoint category;
- do not assume `Umum = Pendidikan + Kesehatan + Peribadatan` across the archive.

M44 must test the arithmetic relationship directly.

## Temporal-geography qualification

M41 already froze legal lineage anchors and M42 applied source-row lineage flags. M43 makes the analytical consequence explicit: **legal identity is not the same thing as current-boundary geometric equivalence.**

The lineage registry is:

`data/registries/bnpb_historical_geography_lineage.csv`

### 2002 — Kota Pariaman split

UU No. 12 Tahun 2002 became effective on 10 April 2002 and created Kota Pariaman from part of Padang Pariaman:

`https://peraturan.bpk.go.id/Details/44443/uu-no-12-tahun-2002`

The 2002 annual observation therefore spans a within-year boundary transition. Parent/successor values may not be silently allocated or treated as current-boundary equivalents.

### 2003 — three district creations

UU No. 38 Tahun 2003 became effective on 18 December 2003 and created:

- Dharmasraya from Sawahlunto/Sijunjung;
- Solok Selatan from Solok;
- Pasaman Barat from Pasaman.

Reference:

`https://peraturan.bpk.go.id/Details/44168/uu-no-38-tahun-2003`

Because the split occurs near the end of the calendar year, 2003 parent observations remain source-native and cannot be proportionally reallocated to successors.

### 2008 — Sijunjung rename

The 2008 legal rename is a same-entity name transition rather than a boundary split. Source-label timing still remains versioned because the archive uses `SIJUNJUNG` before the legal rename date.

### Later years are not automatically geometry-equivalent

After a successor district has existed for a full year, its source row may be legally lineage-eligible for that entity. That is still weaker than proving that the observation geometry is identical to today's boundary.

M43 therefore does not promote any row merely because no split is currently registered. Absence of a known lineage event is not positive proof that all boundary geometry remained unchanged.

## Missingness remains unchanged

M43 preserves the M41/M42 missingness contract:

- the 2001 workbook remains `empty_body`, not zero;
- an absent district/city row is not zero;
- an absent row is not proof that a geography did not exist;
- only explicit numeric `0` cells on explicit source rows become `observed_zero`.

The 2004 counterexample remains decisive: Solok Selatan, Dharmasraya, and Pasaman Barat were legally active for the full calendar year but absent from that workbook.

## What M43 authorizes

M43 permits:

- source-native archival tables that preserve original metric names;
- year/geography-specific display of BNPB archive-reported counts with source provenance;
- explicit zero / missing / empty-body states;
- QA and total-row reconciliation summaries;
- diagnostics that clearly label values as **archive-reported counts**, not harmonized incidence estimates.

## What M43 still blocks

M43 does **not** authorize:

- a canonical current-boundary 2000–2017 district/city panel;
- unqualified long-run trend claims as true disaster incidence;
- automatic `Menderita` → `Terdampak` renaming;
- unique-person aggregation across victim categories;
- unique-asset aggregation across house/facility categories or events;
- arithmetic assumptions involving historical `Umum`;
- parent-to-successor allocation in transition years;
- direct comparison with current BNPB resources without overlap reconciliation;
- causal attribution, monetary-loss estimation, avoided-loss estimation, composite-risk scoring, or policy ranking from these archive values alone.

## Next gate — M44 overlap-year reconciliation

The strongest next evidence is already available: the M42 archive overlaps current official BNPB historical resources for **2010–2017**.

M44 should therefore perform value-level reconciliation rather than another broad source-discovery pass:

1. build genuinely like-for-like 2010–2017 comparisons wherever source dimensions permit;
2. compare archive `Menderita` against current `Terdampak` before deciding whether they are interchangeable;
3. compare shared victim concepts and quantify revisions/disagreements instead of assuming equality;
4. test the arithmetic relationship between historical `Umum` and specific facility categories;
5. promote only metric-year-geography slices whose semantic gate and temporal-geography gate both pass.

This is the shortest defensible path from the M42 source-native archive toward a usable historical analytical panel without manufacturing comparability that the evidence has not established.
