# Sumatera Barat construction revision localization, 2001-2004

## Purpose

This checkpoint narrows the previously frozen construction-statistics release break by comparing two consecutive BPS Statistical Yearbook vintages.

The result changes one part of the interpretation: the large 2001-2002 level shift is no longer merely an unexplained disagreement between releases. BPS itself subsequently labels the affected historical values as **revised figures**. The revision event is therefore explicit; the revision mechanism remains undocumented in the evidence currently acquired.

## Earlier yearbook vintage

`Statistik Indonesia 2004`, BPS catalog `1101001`, publication `07330.0508`.

Current BPS metadata dates the publication to 15 May 2005. The archived publication preface itself is dated Jakarta, June 2005, so this checkpoint does not treat the metadata date as an exact physical-release timestamp.

Table 6.4.5 reports Sumatera Barat in **million rupiah**:

| Year | Value | Status |
| --- | ---: | --- |
| 2000 | 345,371 | revised |
| 2001 | 397,937 | revised |
| 2002 | 458,503 | no revision marker |
| 2003 | 469,008 | preliminary |
| 2004 | 520,179 | estimated |

For 2001-2003 these rounded yearbook values match the earlier exact construction-publication vintage already frozen in the repository: `397,936,972`, `458,502,968`, and `469,007,986` thousand rupiah.

The adjacent construction-establishment summary states that it is based on the Annual Construction Establishment Survey.

## Later yearbook vintage

`Statistik Indonesia 2005/2006`, BPS catalog `1101001`, publication `07330.0608`.

Current BPS metadata dates it to 15 May 2006, while the mirrored publication preface reads Jakarta, July 2006. Again, chronological order by publication vintage is trusted; an exact day-level revision window is not asserted.

Table 6.4.5 reports Sumatera Barat in **thousand rupiah**:

| Year | Value | Status |
| --- | ---: | --- |
| 2001 | 622,547,470 | revised |
| 2002 | 717,299,178 | revised |
| 2003 | 844,516,928 | revised |
| 2004 | 932,441,815 | preliminary |
| 2005 | 1,046,561,944 | estimated |

The table legend explicitly defines:

- `r` = `Angka yang diperbaiki / Revised figures`;
- `x` = `Angka sementara / Preliminary figures`;
- `e` = `Angka perkiraan / Estimated figures`.

The adjacent Table 6.4.3 is explicitly labeled `Based on Construction Establishment Survey` and carries the same 2001r-2005e status sequence.

## What is now proven

### 2001

The exact earlier value `397,936,972` rises to `622,547,470` thousand rupiah.

- delta: `224,610,498` thousand rupiah;
- change: `+56.443737%`;
- later / earlier ratio: `1.564437370`.

### 2002

The exact earlier value `458,502,968` rises to `717,299,178` thousand rupiah.

- delta: `258,796,210` thousand rupiah;
- change: `+56.443737%`;
- later / earlier ratio: `1.564437371`.

BPS explicitly marks the later 2002 value as revised. The prior #96 classification `major_release_break_unexplained` is therefore refined to:

`major_release_break_explicit_revision_cause_unexplained`

The two virtually identical 2001 and 2002 scaling ratios are a strong descriptive signal of a systematic series operation. They are **not** evidence sufficient to name that operation as reweighting, rebenchmarking, frame revision, coverage expansion, or reprocessing.

### 2003

The earlier `469,007,986` preliminary value becomes the `844,516,928` revised value. This strengthens the already-frozen `preliminary -> revised/annual-survey-series` status transition.

### 2004

The earlier yearbook reports only a rounded `520,179` million-rupiah estimate. The later yearbook reports `932,441,815` thousand rupiah and marks it preliminary. No exact revision ratio is promoted from the rounded earlier display.

## Revision window

Among the yearbook vintages examined:

1. `Statistik Indonesia 2004` still carries the old series;
2. `Statistik Indonesia 2005/2006` carries the new series and explicitly labels 2001-2003 revised.

Therefore the revision is localized to **after the 2004 yearbook vintage and by the 2005/2006 yearbook vintage**.

The exact calendar day is intentionally unresolved because current BPS metadata dates and the dates printed in the publication prefaces do not align.

## Remaining blocker

The revision event is now proven. The **revision mechanism** is not.

Until a BPS source explains the transformation or supplies a defensible bridge contract:

- retain all vintages;
- do not silently overwrite earlier releases;
- do not splice a single continuous 1998-2006 trajectory;
- do not infer the common 2001-2002 scale factor backward or forward;
- do not map these construction-financing values to DJPK fiscal accounts;
- do not integrate the unresolved cross-vintage series into Panel v3;
- do not attach a causal label to the revision mechanism.

This narrows the research question from **whether a major break exists** to **why BPS revised the series and how the revised vintage was constructed**.
