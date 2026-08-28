# BPBD 2017 PPID migration forensics

## Purpose

Milestone 51 converted the missing 2017 BPBD/Pusdalops annual report into an explicit acquisition gate. This checkpoint tests whether the known legacy PPID record or the current PPID inventory can recover a semantically valid official transport for that report.

The result is a bounded negative finding. It does **not** establish that the report has been deleted or that no official copy exists elsewhere.

## Target identity

The frozen historical PPID evidence identifies:

- legacy record ID: `8604`;
- title: `Laporan Tahunan Data Kebencanaan Pusdalops PB Sumatera Barat Tahun 2017`;
- OPD: `Badan Penanggulangan Bencana Daerah`;
- historical download count: `24`.

These facts continue to support the historical existence of the PPID record. They do not imply that a current route with the same numeric identifier still represents the same object after migration.

## Legacy-route finding: semantic collision

Three bounded legacy URL variants were queried on the official PPID host:

1. the known numeric ID plus the exact historical title slug and `.html` suffix;
2. the same slug without `.html`;
3. the bare numeric detail route.

All three resolved with HTTP 200 to the same current UUID:

`e46ef762-5314-4f25-8a70-53de147147da`

A route-level match is not an identity match. The destination page identifies itself as **`SPO Cervical RPO`**, not the 2017 Pusdalops report. Neither the exact target title nor the combined identity tokens `pusdalops`, `kebencanaan`, and `2017` are present. Its current download route returns the visible message:

`File tidak ditemukan atau tidak dapat diakses.`

The correct classification is therefore:

`legacy_numeric_redirect_semantic_collision_not_valid_mapping`

The UUID is recorded only to prevent future researchers from mistaking the same stale/colliding redirect for a recovered migration mapping.

## Current inventory finding: exact-title no-hit

The active PPID inventory at `/home/dip` exposes a public search form protected by a session-specific CSRF field. A live read-only probe established a fresh cookie session, obtained the CSRF value, and submitted the exact historical title through the site's own POST form.

The response was HTTP 200 but returned:

- no exact title match;
- no combined Pusdalops/kebencanaan/2017 identity-token match;
- no `/home/information/<uuid>` result for inspection.

This is classified as:

`active_inventory_exact_title_no_hit`

This finding means only that the current inventory did not return the exact title under this official query contract on 2026-08-28. It does not prove archival deletion, depublication, or absence from other official government storage.

## What remains valid from M51

The following M51 boundaries remain unchanged:

- the historical PPID record still documents that the 2017 report existed in the official archive;
- the 2017 LAKIP and 2015-2016 BPBD materials remain companion evidence only;
- mirror values remain verification targets, not canonical observations;
- raw official annual-report bytes are still required before source-native 2017 extraction;
- the BPBD layer must remain separate from BNPB/DIBI until taxonomy, lineage, and metric semantics qualify.

## M52 gate

M52 is **not triggered**.

Specifically:

- `record_8604_to_current_uuid_mapping_recovered = false`;
- `current_detail_or_download_url_for_2017_recovered = false`;
- `raw_official_pdf_recovered = false`;
- `raw_checksum_frozen = false`;
- `source_native_2017_extraction_authorized = false`;
- `canonical_historical_impact_promotion_authorized = false`.

## Next search boundary

Further work may search other official Sumatera Barat government or BPBD/Pusdalops archival surfaces and may inspect PPID migration metadata where semantic identity can be verified.

It must not:

- brute-force UUIDs;
- relabel the unrelated `e46ef762-...` destination as the 2017 report;
- use the Scribd mirror as the missing raw official artifact;
- promote companion-source values as replacements for annual-report bytes.

The next successful checkpoint requires actual official 2017 bytes, not another plausible locator.
