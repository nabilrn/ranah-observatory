# Milestone 55 — BPBD Current-Library Historical Media Migration Audit

## Purpose

M55 tests whether the current BPBD Sumatera Barat library can recover the official raw 2022 companion artifact identified in M54 and whether the same current surface exposes Buku DIBI Tahun 2022.

This milestone is a transport and provenance audit. It does not upgrade indexed text, cached search results, or live metadata into raw source evidence.

## Current library route

The current BPBD site exposes a single-page application with a `/web-api` backend. The `laporan-kinerja` library page maps to:

`https://bpbd.sumbarprov.go.id/web-api/api/category/laporan-kinerja-instansi-pemerintah/2696`

The API returned five records during the 2026-09-02 audit. The 2022 record is still explicitly published:

- title: `Laporan Kinerja Badan Penanggulangan Bencana Daerah Tahun 2022`;
- slug: `laporan-kinerja-badan-penanggulangan-bencana-daerah-tahun-2022-332`;
- created by: `Admin BPBD`;
- created at: `16 Februari 2023 16:15:8`;
- media pointer: `/api/files/badan-penanggulangan-bencana-daerah/2023/02/LKJ_BPBD_TAHUN_2022.pdf`.

The frontend's `/web-api` prefix resolves that pointer to:

`https://bpbd.sumbarprov.go.id/web-api/api/files/badan-penanggulangan-bencana-daerah/2023/02/LKJ_BPBD_TAHUN_2022.pdf`

## Transport result

The current file route does **not** return the 2022 PDF. It returns HTTP `500`, JSON content, and:

`Minio S3Error: The specified key does not exist.`

The response body is 60 bytes and hashes to:

`1fb247e83188a06958c4d3a532ed0cd44be4a3bd3a7d6b93487f25183eadc12a`

The previously indexed legacy URL also no longer returns raw PDF bytes. It returns the current BPBD SPA shell:

- HTTP `200`;
- `text/html`;
- 1,194 bytes;
- SHA256 `7e0ebbde81104e10d61008e405636958da368f05d5fd9b859da88007e74d9b7f`.

Therefore both common false positives are rejected:

1. HTTP 200 from the legacy URL is not artifact recovery;
2. a published metadata row in the current API is not proof that its backing object still exists.

## Vintage comparison

The same current file route was tested against all five rows returned by the LKj category API.

| Library record | Storage vintage | Result |
|---|---|---|
| Laporan Kinerja Instansi Pemerintah Tahun 2025 | 2026/05 | PDF recovered, HTTP 200 |
| Laporan Kinerja Instansi Pemerintah Tahun 2024 | 2026/03 | PDF recovered, HTTP 200 |
| LKJ 2023 | 2024/05 | HTTP 500, MinIO key missing |
| Laporan Kinerja BPBD Tahun 2022 | 2023/02 | HTTP 500, MinIO key missing |
| Laporan Kinerja BPBD | 2016/03 | HTTP 500, MinIO key missing |

The two working files demonstrate that the current MinIO-backed transport itself is functional. The failures are therefore consistent with a historical-media migration/storage gap rather than a general inability to retrieve files from the new site.

The two successful objects were frozen only as transport controls:

- 2025 row: 2,043,904 bytes; SHA256 `c3a45bb8c9e7dfe2ee8daf39b2702b969e1c13911a31c81681bf20e8059f3bd7`;
- 2024 row: 2,043,904 bytes; SHA256 `7c5ddeee330c38649caae42d8a0f28d89d2af959b0ccdd78778dfcfee314d64b`.

They are not promoted into the disaster evidence panel by M55.

## DIBI search on the current BPBD library

M55 queried the returned payloads for the reviewed current library categories:

- download;
- laporan kinerja;
- infografis;
- edukasi bencana;
- rencana strategis;
- rencana kerja;
- perjanjian kinerja;
- rencana kinerja tahunan;
- SOP;
- indikator kinerja individu;
- renaksi;
- SKP;
- IKU.

Twelve category endpoints returned payloads; `renaksi` returned HTTP 404. No returned row contained the literal `DIBI`.

This is a bounded result. It means the reviewed current BPBD library API did not yield Buku DIBI Tahun 2022; it does not establish that no other official Sumatera Barat government archive retains the file.

## Consequence for M53/M54

M53 and M54 remain unchanged in their scientific interpretation:

- DIBI 2022 remains the preferred operational-disaster product for the 1,021-event source-native series **after** raw verification;
- LKj 2022 remains an official cross-publication disagreement source with 1,047 events and a different taxonomy;
- neither raw 2022 artifact is acquired through the current BPBD library in M55;
- no unified 2022 disaster series is authorized.

The M54 Table 3.4.7 values remain verification targets supported by the indexed official document context, but M55 does not convert them into canonical source-native observations.

## Next acquisition lane

The highest-value next step is now narrower:

1. search the current PPID inventory and UUID download routes for Buku DIBI Tahun 2022;
2. search other official `sumbarprov.go.id` archive/storage surfaces for the exact DIBI title and historical filename;
3. if raw bytes are recovered, freeze SHA256, byte size, page count, and acquisition timestamp;
4. verify source-native tables before materialization;
5. preserve the DIBI/LKj disagreement rather than reconciling it implicitly.
