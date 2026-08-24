# Milestone 38 — BNPB Historical District/City Impact Qualification

## Status

**Transport qualification in progress. Numeric promotion is not authorized.**

Milestone 38 investigates a separate source-native historical evidence lane from the M37 provincial 2024–2025 observed-impact compilation: BNPB Satu Data annual datasets titled `Jumlah kejadian dan Dampak Bencana Tahun YYYY`.

The official dataset descriptions state that these datasets contain disaster occurrence and impact data by `kabupaten/kota` for the named year. Portal discovery currently exposes the annual series across at least 2000–2017. This is potentially high-value historical evidence for Ranah Observatory because it can provide an observed-impact context at finer geography and much earlier dates than M37.

However, the portal does not expose a uniform resource transport contract across sampled years. Therefore no historical district/city impact number is promoted in this milestone until the transport and schema boundary are frozen.

## Why this lane matters

M37 added bounded, source-native **provincial** observed-impact context for Sumatera Barat in 2024–2025. It explicitly did not infer district/city values and did not resolve the M26 event-level retrieval gate.

M38 does not reinterpret M37 and does not claim to resolve the event-level gate. Instead, it asks a narrower question:

> Does BNPB provide a deterministic, source-native annual district/city impact archive for Sumatera Barat that can be qualified independently of event-level reconstruction?

If yes, this can later support a historical district/city observed-impact panel without allocating provincial totals downward and without inventing event records.

## Official portal evidence discovered before the CI probe

### Annual series exists

BNPB Satu Data exposes datasets named `Jumlah kejadian dan Dampak Bencana Tahun YYYY` for years spanning at least 2000 through 2017 in the portal catalogue.

Examples:

- 2000: <https://data.bnpb.go.id/dataset/datakejadian2000>
- 2001: <https://data.bnpb.go.id/dataset/jumlah-kejadian-dan-dampak-bencana-tahun-2001>
- 2002: <https://data.bnpb.go.id/dataset/jumlah-kejadian-dan-dampak-bencana-tahun-2002>
- 2005: <https://data.bnpb.go.id/dataset/jumlah-kejadian-dan-dampak-bencana-tahun-2005>
- 2017: <https://data.bnpb.go.id/dataset/jumlah-kejadian-dan-dampak-bencana-tahun-2017>

The portal descriptions characterize the content as disaster occurrence and impact data according to `kabupaten/kota` for the corresponding year. The source field points to DIBI/BNPB.

### Transport is visibly heterogeneous

The 2000 and 2001 dataset pages expose direct XLSX files partitioned by province code. In both years, a resource named `stat_by_wil_13_YYYY.xlsx` is visible, making code `13` a concrete **filename candidate** for the Sumatera Barat resource. Filename identity alone is not enough to promote its contents; the workbook schema and geography semantics still require validation.

Sampled later years do not show the same direct XLSX pattern in the public page. The 2002, 2005, and 2017 pages expose a resource labelled `Jumlah Kejadian Bencana Tahun YYYY` with `Go to resource`, indicating a different link/external-resource transport path.

This heterogeneity is the reason M38 begins with metadata and transport qualification rather than immediately downloading and concatenating annual values.

### National portal provenance cross-check

The Indonesian national data portal currently mirrors the BNPB 2000 package with the same dataset ID `b40b63a8-30dc-49b1-9b63-4f285270bbd3` and the same direct resource naming pattern, including `stat_by_wil_13_2000.xlsx`:

- <https://data.go.id/dataset/dataset/datakejadian2000>

This is only a provenance cross-check. BNPB Satu Data remains the source endpoint for M38; the national portal mirror is not used to replace BNPB metadata or values.

## CI probe contract

The workflow `.github/workflows/milestone38-bnpb-historical-district-impact-probe.yml` runs a read-only metadata probe against the official BNPB CKAN API.

The probe must:

1. discover packages matching the exact annual title pattern for 2000–2017;
2. freeze package IDs, names, titles, metadata timestamps, organization, and source metadata;
3. enumerate resource IDs, names, formats, URLs, datastore flags, and transport classes;
4. identify `stat_by_wil_13_YYYY` only as a Sumatera Barat **filename candidate**;
5. separate direct-file years from external/link-only years;
6. report missing or duplicate annual package candidates;
7. upload only a metadata/transport manifest as a CI artifact.

The probe must not download or parse impact values.

## Research boundary

Until a follow-up freeze explicitly authorizes numeric ingestion, M38 prohibits:

- treating a filename containing province code `13` as sufficient geography proof;
- treating link-only resources as equivalent to direct files;
- concatenating annual workbooks without schema-version checks;
- converting blank cells to zero without source-native missing-value semantics;
- summing affected/displaced/injured categories as unique people;
- reconstructing event-level rows from annual aggregates;
- allocating M37 provincial values to districts/cities;
- merging annual district/city aggregates with DIBI occurrence layers as if they share event identity;
- causal, monetary-loss, avoided-loss, composite-risk, or policy-ranking claims from this source alone.

## Decision gate after transport probe

M38 can advance to numeric qualification only if the CI artifact establishes a deterministic path for at least one Sumatera Barat annual source and allows us to freeze:

- source/resource identity;
- exact geography meaning;
- workbook or response schema;
- metric definitions and units;
- missing-value semantics;
- duplicate/aggregation semantics;
- temporal coverage and version boundary;
- reproducible raw-evidence checksums or source-row snapshots.

If those conditions are not met, the annual series remains a discovered source registry entry rather than an analytical panel.

## Relationship to earlier milestones

- **M26 event-level gate:** remains unresolved unless a future milestone independently freezes deterministic event-level retrieval and event identity.
- **M37 provincial observed-impact context:** remains valid and unchanged for its bounded 2024–2025 scope.
- **M38:** is a historical district/city source-qualification lane and cannot silently upgrade either M26 or M37 claims.
