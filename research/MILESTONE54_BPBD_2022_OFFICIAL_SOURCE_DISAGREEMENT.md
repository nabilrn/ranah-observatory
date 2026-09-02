# M54 — BPBD 2022 Official Source Disagreement

## Why this milestone exists

Ranah Observatory should never present a clean-looking disaster total by silently mixing official publications that count different event universes.

During M53, **Buku DIBI Tahun 2022** was qualified as the preferred detailed BPBD/Pusdalops source family for district, hazard, impact, loss and monthly proof data. Its indexed verification target is **1,021 events**.

A second official BPBD publication is now confirmed: **Laporan Kinerja Badan Penanggulangan Bencana Daerah Tahun 2022**. Its Table 3.4.7 reports a **Grand Total of 1,047 events** for 2022.

The 26-event gap is real source disagreement, not a rounding issue.

## Official LKj source

Official BPBD PDF:

`https://bpbd.sumbarprov.go.id/images/2023/05/file/LKJ_BPBD_TAHUN_2022.pdf`

The current BPBD digital library also lists the 2022 performance report under Laporan Kinerja.

Table locator:

- **Tabel 3.4.7**
- **PDF pages 59–60**
- title: **Jumlah Peristiwa Kab/Kota per Jenis Bencana di Provinsi Sumatera Barat Tahun 2022**

The table reports:

| LKj hazard label | Events |
|---|---:|
| Angin Kencang | 108 |
| Abrasi | 1 |
| Abrasi Pantai | 4 |
| Banjir | 122 |
| Banjir Bandang | 6 |
| Erosi Sungai | 3 |
| Gempa Bumi | 6 |
| Karhutla | 87 |
| Kekeringan | 2 |
| Longsor | 131 |
| Pohon Tumbang | 549 |
| Puting Beliung | 27 |
| Tanah Bergerak | 1 |
| **Grand Total** | **1,047** |

## Comparison with Buku DIBI 2022

M53 records the DIBI verification target:

| DIBI hazard label | Events |
|---|---:|
| Abrasi Pantai | 5 |
| Angin Kencang | 674 |
| Banjir | 123 |
| Banjir Bandang | 5 |
| Gempa Bumi | 2 |
| Kebakaran Hutan dan Lahan | 92 |
| Longsor | 120 |
| **Total** | **1,021** |

The DIBI source has 7 top-level hazard categories in this table; LKj has 13.

## A simple taxonomy bridge does not eliminate the disagreement

Some labels can be bridged conservatively without pretending event-level identity:

- LKj `Abrasi + Abrasi Pantai` = 5, matching DIBI `Abrasi Pantai = 5`.
- LKj `Angin Kencang + Pohon Tumbang + Puting Beliung` = 684, while DIBI `Angin Kencang = 674`.
- LKj `Banjir = 122`, while DIBI has 123.
- LKj `Banjir Bandang = 6`, while DIBI has 5.
- LKj `Gempa Bumi = 6`, while DIBI has 2.
- LKj `Karhutla = 87`, while DIBI has 92.
- LKj `Longsor = 131`, while DIBI has 120.

LKj also contains three categories without an obvious DIBI Table 3.2 counterpart:

- Erosi Sungai: 3
- Kekeringan: 2
- Tanah Bergerak: 1

The mapped category differences plus those six unmatched events reproduce the overall **+26 LKj versus DIBI gap**. This is useful as an accounting identity, but it does **not** prove that individual records can be mapped one-to-one.

## What this means for the product

The public dashboard must retain source lineage. A user should never see `2022 = 1,0xx kejadian` without knowing which BPBD data product generated that number.

The product contract is therefore:

1. **Buku DIBI 2022 remains the preferred detailed operational source** once its official raw bytes are recovered and verified.
2. **LKj 2022 is a cross-publication validation/disagreement source**, not a drop-in replacement for DIBI.
3. Native hazard labels remain preserved in proof data.
4. No averaging of 1,021 and 1,047.
5. No concatenation of the two event tables.
6. No cross-year unified series that silently switches source families.
7. Any future reconciliation must be event-level or supported by an explicit documented taxonomy/cutoff rule.

## Acquisition state

The LKj official PDF URL is live and was readable as a 77-page PDF during the 2026-09-02 review. Its bytes and SHA256 are not yet frozen in the repository, so M54 does not authorize canonical materialization from the LKj table.

A P1 acquisition request `bpbd_lkj_2022` has been added to `data/acquisition_requests/bpbd_publications.csv`.

Buku DIBI 2022 remains separately blocked on recovery of the official raw PDF bytes.

## Decision

M54 confirms a **material official cross-publication disagreement** for BPBD Sumatera Barat disaster-event counts in 2022.

The disagreement is now a first-class evidence constraint rather than something the dashboard or analytical layer may normalize away.
