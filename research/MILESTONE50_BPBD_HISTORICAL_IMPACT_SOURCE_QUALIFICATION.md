# M50 — BPBD/Pusdalops Historical Impact-Source Qualification

## Why this gate exists

M49 established that the BPBD/Pusdalops 2015 operational incident universe is broader than the M42 BNPB/DIBI disaster-event universe. M50 asks a narrower question: **does the local Pusdalops report family contain victim and physical-impact information that is traceable enough to acquire as its own source-native layer?**

The answer is **yes for source-family capability, no for ingestion yet**.

## 2015 official report: useful, but internally imperfect

A government-hosted PDF is indexed at:

`https://www.sumbarprov.go.id/images/1456451857-Laporan%20Kegiatan%20Pusdalops%20PB%20BPBD%20Sumbar%20Th%202015.pdf`

The indexed text describes the local database procedure:

- a repeated report of the same event on the same date is counted once;
- detailed administrative area, impact and loss information is accumulated for that event;
- inputs come from official BPBD district/city reports and periodic recaps;
- data volume depends on how much the kabupaten/kota supply.

The report also says the 2015 recap had **not yet been fully collected as of January 2016** and should be revised after missing district/city records arrive. Therefore the 2015 local layer is a revision-prone operational snapshot, not a finished incidence census.

### Internal year-label inconsistency

One narrative sentence says that 686 incidents occurred in **2014**. However the stronger local context immediately around it is explicit:

- Table 4.1 is titled as covering **Tahun 2015** and totals 686;
- the following graph is labelled **Tahun 2015**;
- the following narrative says 2015 and describes the same 686-event distribution.

M50 therefore retains M49's assignment of **686 to the 2015 report-year table**, while preserving the isolated `2014` sentence as a source-quality flag. The contradiction is not silently corrected or deleted.

Direct raw retrieval of the PDF returned HTTP 503 during this review session, so M50 still does not freeze a raw-file checksum.

## 2017: impact-capable schema found, official raw still missing

The official Sumatera Barat PPID download audit lists record **8604**:

> Laporan Tahunan Data Kebencanaan Pusdalops PB Sumatera Barat Tahun 2017 — Badan Penanggulangan Bencana Daerah.

A separately indexed copy of the report exposes the chapter structure and fields. It contains sections for:

- event counts by district/city;
- event counts by disaster type;
- human impacts;
- housing/public-facility impacts;
- recorded monetary loss.

The indexed human-impact table uses `Meninggal`, `Hilang`, `Mengungsi`, and `Luka/sakit`. The indexed copy reports 725 events, 40 deaths, 8 missing, 9,387 displaced, 17 injured/sick, and Rp20,647,693,425 recorded loss.

Those numbers are **not canonical data in M50**. They are frozen only as expected values to verify against the official raw artifact once acquired.

## Decision

M50 establishes that the BPBD/Pusdalops annual-report family is **impact-capable** and worth acquiring as a separate local operational layer. It does **not** establish that:

- local BPBD values are independent from DIBI inputs;
- local and BNPB/DIBI taxonomies are equivalent;
- victim categories use identical counting/deduplication semantics;
- local annual totals can be substituted for M42 or the modern BNPB panel.

Therefore no BPBD value is promoted into the canonical BNPB/DIBI panel.

## Next: M51

M51 should obtain the official raw 2017 report, freeze its bytes/checksum/page locators, then extract the impact tables source-natively. Any mismatch against the indexed expected values must be recorded rather than normalized away.
