# Milestone 56 — BPBD/Pusdalops DIBI 2022 PPID Raw-Artifact Recovery

## Purpose

M56 closes the raw-artifact acquisition gate opened by M53 for **Buku DIBI Tahun 2022**.

The objective is deliberately narrow: map legacy PPID record `20769` to the current PPID UUID route, freeze the exact official PDF identity, and verify the high-value M53 table targets against the raw source before any machine-readable materialization.

## Current PPID identity recovered

Three legacy record forms were tested:

- `https://ppid.sumbarprov.go.id/home/details/20769-buku-dibi-tahun-2022.html`
- `https://ppid.sumbarprov.go.id/home/details/20769-buku-dibi-tahun-2022`
- `https://ppid.sumbarprov.go.id/home/details/20769`

All three resolve to the same current PPID information UUID:

`faf18bd0-76d9-44b2-8092-b89f70f29e6e`

Stable information route:

`https://ppid.sumbarprov.go.id/home/information/faf18bd0-76d9-44b2-8092-b89f70f29e6e`

Stable download route:

`https://ppid.sumbarprov.go.id/home/download/faf18bd0-76d9-44b2-8092-b89f70f29e6e`

The resolved information page visibly contains the exact title **Buku DIBI Tahun 2022**.

The current `/home/dip` exact-title POST did not return the record during this audit. That does not invalidate the legacy mapping: three independent legacy detail forms converge on the same exact-title UUID page. It does show that current inventory-search visibility and record accessibility are not equivalent.

## Frozen raw artifact

The UUID download route returns a complete official PDF:

- HTTP status: `200`;
- content type: `application/pdf`;
- bytes: `13,044,950`;
- SHA256: `f0ce706388d54c361ecd36f7c5da2a3bd749f59b32f807c9e8c5bb25fef67ba3`;
- PDF version: `1.7`;
- page count: `154`;
- complete `%PDF-` header and `%%EOF` marker verified;
- a second retrieval reproduced the same SHA256.

The binary is not committed to the repository. The source is reproducible from the stable official UUID route, while the repository freezes the exact checksum, byte count, page count, and table locators.

## Raw table locators

The source-native Chapter III tables are located at these PDF pages:

| Table | PDF page | Content |
|---|---:|---|
| 3.1 | 36 | Events and estimated loss by kabupaten/kota |
| 3.2 | 38 | Events by kabupaten/kota × hazard |
| 3.3 | 39 | Human impacts by hazard |
| 3.4 | 39 | Human impacts by kabupaten/kota |
| 3.5 | 40 | Settlement impacts by hazard |
| 3.6 | 40 | Settlement impacts by kabupaten/kota |
| 3.7 | 41 | Public-facility impacts by hazard |
| 3.8 | 41 | Public-facility impacts by kabupaten/kota |
| 3.9 | 42 | Events by month × hazard |
| 3.10 | 44 | Human impacts by month |

The recapitulation appendix begins around PDF page 90 and the incident-history appendix begins around page 92. The final history grand total appears on PDF page 146.

## M53 targets confirmed from raw bytes

The raw PDF confirms the M53 province total of **1,021 events**.

Table 3.2 confirms:

| Hazard | Events |
|---|---:|
| Abrasi pantai | 5 |
| Angin kencang | 674 |
| Banjir | 123 |
| Banjir bandang | 5 |
| Gempa bumi | 2 |
| Kebakaran hutan dan lahan | 92 |
| Longsor | 120 |
| **Total** | **1,021** |

Table 3.9 confirms the monthly totals:

`89, 84, 81, 92, 85, 97, 65, 110, 97, 100, 102, 19`

for January through December, again totaling **1,021**.

Human-impact totals are also confirmed:

- deaths: `28`;
- injured/sick: `456`;
- evacuated: `26,265`.

## Source-internal disagreements confirmed

### Missing persons

The earlier M53 disagreement is real in the raw artifact:

- Table 3.3: missing persons shown as `-` in the total row;
- Table 3.4: missing persons total `4`.

Table 3.10 also reports `4` missing persons, all in February.

No normalization is authorized. The table-specific values remain source-native facts.

### District event counts

The raw PDF confirms the seven M53 district discrepancies between the general event tables and Table 3.4. Both table families nevertheless total 1,021 events.

This means the differences are not a cached-index rendering artifact.

## New disagreement discovered from the raw PDF

Raw verification reveals a second monetary total that could not be safely diagnosed from the indexed copy alone.

On PDF page 36, the Chapter III narrative and Table 3.1 report total estimated loss of:

**Rp1,136,849,587,336**

The recapitulation/history appendices report:

**Rp1,136,849,586,796**

Difference:

**Rp540**

The appendix value is the one M53 had frozen as its clearly rendered indexed verification target. M56 does not replace it with the Table 3.1 value. Both are retained with page-level provenance until the arithmetic/source lineage is reconciled.

## Promotion decision

M56 upgrades the artifact state:

- raw official DIBI 2022 artifact: **acquired**;
- checksum and page count: **frozen**;
- source-native table verification: **authorized**.

M56 still does **not** authorize public catalog promotion or dashboard materialization. Raw possession is not the same as a deterministic row-level dataset.

The next milestone must extract Tables 3.1–3.10 into machine-readable source-native datasets, preserve the missing-person and district-count disagreements, retain both loss totals, attach PDF-page provenance, and validate totals before promotion.

## Relation to the separate LKj 2022 product

Nothing in M56 resolves the M54 disagreement between:

- DIBI 2022: `1,021` events;
- LKj BPBD 2022: `1,047` events.

They remain different official products with different taxonomy/reporting semantics. M56 recovers the DIBI raw source; it does not make the LKj product interchangeable with it.
