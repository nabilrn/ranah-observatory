# Milestone 45 — BNPB Total-Event Canonical Candidate

## Status

**Candidate canonicalization is under verification. Global analytical-panel integration remains blocked until the candidate artifact and geography interpretation pass CI.**

M44 established that the modern BNPB `Jumlah Kejadian Bencana Menurut Kabupaten Tahun 2010-2024` matrix is highly aligned with the older 2010–2017 historical release while preserving explicit evidence of small retrospective revisions. M45 tests whether that modern matrix can support a canonical **all-disaster recorded-event** series without overstating geography or incidence semantics.

## Candidate indicator

Proposed indicator ID:

`total_disaster_events`

Definition:

> Count of all disaster events recorded by BNPB for the stated district/city and calendar year under the qualified source release.

This is **not** a flood series, landslide series, unique-event reconstruction across external sources, or estimate of true disaster incidence.

## Why the modern matrix is the candidate source

The qualified modern BNPB resource provides a complete district/city matrix for 2010–2024. M44 compared the overlap against the historical annual archive for Sumatera Barat:

- 119 explicit historical rows were compared;
- 113 matched exactly;
- 6 differed;
- every difference was `modern = historical + 1 event`;
- all 33 modern geography-year cells lacking an explicit historical row were zero;
- there was no positive backfill hidden behind historical sparsity.

Therefore the modern release is the stronger complete-matrix representation for this source-defined metric, while M42 remains the historical-release provenance/crosscheck layer.

## Geography qualification

M45 distinguishes **entity continuity** from **exact polygon harmonization**.

Evidence available before promotion:

1. M41 legally anchors the creation of Kota Pariaman, Solok Selatan, Pasaman Barat, and Dharmasraya before 2010, and the Sijunjung rename before 2010.
2. BPS Population Census 2010 exposes the modern Sumatera Barat district/city entity set.
3. BPS national administrative tables report 12 Sumatera Barat regencies through 2009–2013.
4. Permendagri No. 72 Tahun 2019 reports Sumatera Barat as 12 regencies and 7 cities.
5. The reviewed BNPB 2010–2024 matrix is represented on one 19-row current Permendagri-coded entity set.

This supports stable **entity identity** across the candidate 2010–2024 series. It does not prove that every historical value was spatially recomputed on an identical 2024 polygon.

Consequently candidate rows:

- map to canonical current district/city entity IDs;
- preserve source geography code/name in notes;
- leave the generic `comparable` flag unset rather than asserting exact-boundary comparability;
- explicitly state `exact_polygon_harmonization=not_proven`;
- authorize within-source longitudinal use only with this caveat.

## Promotion boundary

M45 may authorize a candidate canonical artifact when CI proves:

- exactly 19 Sumatera Barat district/city entities;
- exactly 15 years, 2010–2024;
- exactly 285 geography-year observations;
- one non-negative integer event count per geography-year;
- one frozen BNPB source snapshot identity;
- successful M44 overlap/revision contract;
- frozen resource metadata and provenance;
- no type-specific relabeling;
- no claim that the series is complete true incidence;
- no claim of exact 2024-polygon reconstruction for historical years.

## Still blocked after candidate generation

M45 does not by itself modify the global indicator registry or M10/M28 analytical panel. Those changes require a separate integration gate so the existing reviewed BNPB baseline remains stable while the new series is audited.

## External evidence references

- BPS Sensus Penduduk 2010 — Sumatera Barat district/city table: https://sensus.bps.go.id/topik/tabular/sp2010/10/91625/0
- BPS Statistical Yearbook of Indonesia 2014 — administrative-area tables for 2009–2013.
- Permendagri No. 72 Tahun 2019 — amendment to codes and administrative-area data.
- BPS Master Wilayah Administrasi Provinsi Sumatera Barat 2025 — current dynamic administrative-area reference.

## Research boundaries

M45 forbids:

- interpreting `total_disaster_events` as a hazard-specific series;
- summing it with flood/landslide event indicators;
- treating release revisions as source error without event-level evidence;
- claiming historical values are exactly current-polygon harmonized;
- treating recorded events as complete true incidence;
- causal attribution, avoided-loss estimation, monetary-loss estimation, composite-risk scoring, or policy ranking from this series alone.
