# Milestone 36 — Historical Station Rainfall Validation

## Status

**Complete — bounded independent validation evidence.**

Milestone 36 tested whether the previously frozen CHIRPS finding that **1998 was wetter than 1997 across all 19 current-boundary Sumatera Barat kabupaten/kota** is directionally consistent with an independent historical station record.

The result is **directionally supportive**, not a full validation of CHIRPS and not a causal climate finding.

## Result in plain language

The historical Tabing station record also shows substantially more recorded precipitation in 1998 than in 1997.

| Year | Valid precipitation days | Coverage | Longest gap without valid precipitation | Qualified annual total |
| --- | ---: | ---: | ---: | ---: |
| 1997 | 345 / 365 | 94.5% | 4 days | 774.192 mm |
| 1998 | 340 / 365 | 93.2% | 4 days | 2,730.500 mm |

Both years pass the pre-locked completeness rule of at least 90% valid precipitation days and no missing streak longer than 31 days.

The automated classification is:

`station_overlap_directionally_supportive`

This means only that the independent station series and the CHIRPS regional series agree on the **direction** of the 1997→1998 change: both indicate a wetter 1998.

## Why the station identity needed special handling

Traditional station identifier `96163` cannot safely be treated as one location-homogeneous record across all years.

Repository evidence records:

- historical BMKG identity: **PADANG/TABING**, approximately 00°53′S, 100°21′E;
- current BMKG WIS2 identity: **PADANG PARIAMAN/MINANGKABAU**.

For that reason M36 does not concatenate historical Tabing observations with modern Minangkabau observations.

The accepted historical archive representation is NOAA/NCEI GSOD station `96163099999`, identified as `TABING, ID` at approximately `-0.874989, 100.351881`, which is consistent with the historical BMKG Tabing location guard.

## Locked source-selection sequence

The candidate order was fixed before precipitation values were inspected:

1. NCEI Daily Summaries / GHCN `IDM00096163`;
2. NCEI GSOD `96163099999`.

The GHCN/Daily Summaries candidate did not expose qualifying 1997–1998 coverage and remains a negative result. The pre-specified GSOD fallback qualified historical Tabing identity and coverage for both target years.

There was no post-hoc search for a station whose rainfall result happened to match CHIRPS.

## Frozen evidence

Canonical evidence is stored under:

`data/validation/climate/station/m36/`

It contains:

- exact NCEI GSOD source snapshots for 1997 and 1998;
- annual completeness summary;
- Stage 0 source/identity qualification;
- Stage 1 overlap result;
- manifest with SHA-256 hashes.

The final CI gate is read-only and rebuilds the Stage 1 result from the frozen NCEI source snapshots without requiring live NCEI or BMKG access.

## What this result does support

M36 supports the bounded statement:

> An independent historical Tabing station record is directionally consistent with the frozen CHIRPS result that 1998 was wetter than 1997 in Sumatera Barat.

## What this result does **not** support

M36 does not authorize any of the following:

- relabelling CHIRPS gridded estimates as station observations;
- claiming one station validates all 19 district/city CHIRPS magnitudes;
- combining Tabing and Minangkabau into a single homogeneous station series;
- treating missing precipitation as zero;
- attributing the 1997–1998 difference to ENSO, climate change, or another cause;
- upgrading rainfall–unemployment associations to causal effects;
- creating a disaster-risk score from this result;
- estimating monetary wasted potential;
- ranking policy interventions.

## Research implication

The important upgrade is evidentiary rather than causal: the 1997–1998 regional CHIRPS signal is no longer supported only by the gridded product. It now has one independent, historically matched station overlap pointing in the same direction.

This closes the remaining Milestone 23 Tier-B station/daily climate validation priority for the current research scope. Further station expansion may improve robustness in a future research cycle, but it is no longer a blocker for moving the project toward public-facing productization.
