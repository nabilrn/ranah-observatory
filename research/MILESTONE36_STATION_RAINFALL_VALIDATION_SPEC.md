# Milestone 36 — Independent Station Rainfall Validation

## Purpose

Milestone 36 closes the remaining Tier-B priority from the Milestone 23 data-value audit: independent station/daily climate validation of the frozen CHIRPS annual-rainfall evidence.

This milestone is an **evidence-validation** lane. It does not replace CHIRPS, does not convert CHIRPS from `model_estimate` to `observed`, and does not authorize any causal climate or socioeconomic claim.

## Why the design is staged

A previous repository experiment (closed PR #20) qualified the official BMKG WIS2 DayCLI metadata surface and WIGOS station identity `0-20000-0-96163`, but the live DayCLI observation collection returned no usable historical observations for the tested years. M36 therefore does not repeat that transport probe as if it were new evidence.

M36 instead evaluates whether an independent public archive can provide a reproducible observed-station overlap for WMO/traditional station identifier `96163`.

## Station-history guard

Station identifier reuse is a blocking comparability issue.

- BMKG Regulation No. 20/2014 lists station `96163` as **PADANG/TABING**, approximately `00°53′S, 100°21′E`.
- The current BMKG WIS2 station record for WIGOS `0-20000-0-96163` identifies **PADANG PARIAMAN/MINANGKABAU**.

M36 therefore MUST NOT concatenate all records carrying `96163` into one homogeneous physical-station time series without a separately qualified station-history bridge.

The first numerical overlap target is deliberately restricted to **1997–1998**, a historical period for which the target identity must resolve to Padang/Tabing. Modern Minangkabau observations are not used to infer historical Tabing values.

## Stage 0 — source representation and identity qualification

Before inspecting or aggregating target precipitation values:

1. retain the BMKG WIS2/DayCLI negative transport result as prior repository evidence;
2. re-check the current BMKG WIS2 station identity only as a diagnostic station-history guard, allowing the prior qualified repository result to remain authoritative if the live host blocks hosted runners;
3. probe NOAA/NCEI public archive representations without choosing a representation based on rainfall magnitude;
4. test candidate identifier representations in this locked order:
   - GHCN/NCEI: `IDM00096163`;
   - GSOD/ISH representation candidate: `96163099999`;
5. require evidence tying the accepted historical representation to WMO `96163` and Padang/Tabing, with coordinates consistent with the BMKG historical station entry;
6. require 1997–1998 temporal coverage before Stage 1 may inspect precipitation values.

A failed candidate is retained as a negative transport/coverage result. No post-hoc station shopping is permitted in M36.

### Stage 0 result

The live read-only Stage 0 qualification completed before any target precipitation aggregation.

- Daily Summaries / GHCN candidate `IDM00096163` did not provide qualifying 1997–1998 coverage through the locked probe.
- GSOD candidate `96163099999` exposed both 1997 and 1998 files with station name `TABING, ID` and coordinates approximately `-0.874989, 100.351881`, within the pre-tightened historical-coordinate guard around BMKG Padang/Tabing.
- The GSOD representation is therefore the **locked Stage 1 representation**. This is a fallback determined by the preregistered candidate order and identity/coverage criteria, not by precipitation magnitude.
- The BMKG WIS2 current-station recheck returned HTTP 403 from the hosted runner; this does not erase the already-qualified current Minangkabau identity from closed PR #20 and is retained as a transport diagnostic.

## Stage 1 — bounded 1997–1998 precipitation overlap

Stage 1 may execute only after Stage 0 qualifies a historical Padang/Tabing representation. Stage 0 has authorized the fixed GSOD representation `96163099999`.

The numerical inputs are exactly the NCEI GSOD CSVs for station `96163099999` for calendar years 1997 and 1998. No alternate station or year may be substituted after numerical values are inspected.

### Locked completeness rules

These rules are frozen **before the first Stage 1 numerical run**:

1. A calendar year is numerically comparable only if at least **90% of its calendar days** have source-valid `PRCP` values. Both target years are non-leap years, so the minimum is `ceil(0.90 × 365) = 329` valid precipitation days.
2. A comparable year must not contain a run of more than **31 consecutive calendar days** without a source-valid precipitation value.
3. Blank/non-numeric precipitation and source missing sentinels are missing. Missing precipitation is never converted to zero.
4. GSOD `PRCP=99.99` (and values in the reserved missing-sentinel range `>=99.0` inches) are treated as missing, never as rainfall. The raw source value remains auditable in the frozen source file.
5. Valid non-missing GSOD `PRCP` is interpreted in source units of inches; millimetres are reported using the exact conversion `1 inch = 25.4 mm`.
6. Duplicate dates, wrong years, wrong station identifiers, non-Tabing aliases, or coordinates outside the locked historical guard invalidate the affected source file rather than being silently repaired.
7. Source-row absence and present-row/missing-PRCP are reported separately.
8. Completeness is evaluated before annual totals are admitted to the comparison.

NCEI documents GSOD precipitation as a daily total derived from synoptic/hourly observations, with precipitation totals appearing only when reports are sufficient. Non-U.S. GSOD daily summaries are UTC-based and may include a portion of the previous local day; M36 therefore treats annual totals as an independent directional overlap check, not exact local-calendar equivalence.

### Locked comparison rule

If **both** years pass the completeness rules:

- compute the sum of valid daily GSOD precipitation for each year;
- compute `delta = total_1998 - total_1997`;
- compare only the **sign** of that delta with the frozen CHIRPS regional finding that all 19 current-boundary geographies are wetter in 1998 than 1997.

Magnitude equality is not a target because a point station and polygon-mean gridded estimates are different estimands.

The classification is exactly one of:

- `station_overlap_directionally_supportive` if both years pass and `total_1998 > total_1997`;
- `station_overlap_directionally_discordant` if both years pass and `total_1998 <= total_1997`;
- `station_overlap_incomplete_or_noncomparable` if either year fails completeness or source-identity validation.

No threshold or source may be changed after the first numerical run because of the observed classification.

Even a supportive result does not set global CHIRPS station validation to complete from one station.

## Existing CHIRPS object being checked

The frozen 1981–2025 CHIRPS baseline remains unchanged. The existing sanity result records that all 19 current-boundary Sumatera Barat geographies are wetter in 1998 than 1997, with increases ranging approximately 43.05%–162.90%.

M36 tests whether one independent historical station overlap is directionally consistent with that regional gridded signal. It does not test district-level point equivalence.

## Prohibited inference

M36 does not authorize:

- rewriting or recalibrating the 855-row CHIRPS baseline;
- labelling CHIRPS as direct station observations;
- treating station `96163` as location-homogeneous through a site transition;
- filling missing station days with zero;
- ENSO or anthropogenic climate-change attribution;
- rainfall → disaster causality;
- rainfall → unemployment causality;
- any causal upgrade to M14/M15;
- a disaster-risk composite;
- a monetary wasted-potential estimate;
- a policy ranking.

## Sources used to lock the design

- BMKG WIS2 OGC API station/DayCLI surfaces: `https://wis2node.bmkg.go.id/oapi`
- BMKG Regulation No. 20/2014 Data Policy station list: `https://iklim.bmkg.go.id/publikasi-klimat/ftp/regulasi-brosur/Perka_20.2014_Data_Policy.pdf`
- NOAA/NCEI Access Data Service documentation: `https://www.ncei.noaa.gov/access/search/documentation/data-service/`
- NOAA/NCEI Access Search Service documentation: `https://www.ncei.noaa.gov/access/search/documentation/search-service/`
- NOAA/NCEI Daily Summaries / GHCN-Daily dataset.
- NOAA/NCEI Global Surface Summary of the Day dataset and GSOD readme.

## Closure rule

M36 is complete only when the repository contains a deterministic record of:

1. the station-history break guard;
2. Stage 0 archive representation/coverage results;
3. Stage 1 1997–1998 precipitation completeness and directional comparison, or a frozen held result;
4. all failed/held paths;
5. raw source-file hashes for any numerical result;
6. an offline reproducibility check over the frozen source evidence used for any numerical result.

No publication package is modified by M36.