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
2. re-check the current BMKG WIS2 station identity only as a station-history guard;
3. probe NOAA/NCEI public archive representations without choosing a representation based on rainfall magnitude;
4. test candidate identifier representations in this locked order:
   - GHCN/NCEI: `IDM00096163`;
   - GSOD/ISH representation candidate: `96163099999`;
5. require evidence tying the accepted historical representation to WMO `96163` and Padang/Tabing, with coordinates consistent with the BMKG historical station entry;
6. require 1997–1998 temporal coverage before Stage 1 may inspect precipitation values.

A failed candidate is retained as a negative transport/coverage result. No post-hoc station shopping is permitted in M36.

## Stage 1 — bounded 1997–1998 precipitation overlap

Stage 1 may execute only after Stage 0 qualifies a historical Padang/Tabing representation.

Preferred numerical source: NCEI Daily Summaries / GHCN-Daily precipitation (`PRCP`). A source-native annual product may be used as a preregistered cross-check, not as a replacement selected because its result is more convenient.

Rules:

- missing precipitation is never converted to zero;
- trace/missing flags retain source semantics;
- yearly totals require an explicit completeness audit;
- if coverage is insufficient for an annual comparison, the result is held rather than imputed;
- point-station totals are not expected to equal CHIRPS polygon means;
- the primary validation object is the **direction of the 1997→1998 annual change**, not magnitude equality.

Possible classifications are exactly:

- `station_overlap_directionally_supportive`;
- `station_overlap_directionally_discordant`;
- `station_overlap_incomplete_or_noncomparable`.

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

## Sources used to lock Stage 0

- BMKG WIS2 OGC API station/DayCLI surfaces: `https://wis2node.bmkg.go.id/oapi`
- BMKG Regulation No. 20/2014 Data Policy station list: `https://iklim.bmkg.go.id/publikasi-klimat/ftp/regulasi-brosur/Perka_20.2014_Data_Policy.pdf`
- NOAA/NCEI Access Data Service documentation: `https://www.ncei.noaa.gov/access/search/documentation/data-service/`
- NOAA/NCEI Access Search Service documentation: `https://www.ncei.noaa.gov/access/search/documentation/search-service/`
- NOAA/NCEI Daily Summaries / GHCN-Daily dataset.
- NOAA/NCEI Global Surface Summary of the Day dataset.

## Closure rule

M36 is complete only when the repository contains a deterministic record of:

1. the station-history break guard;
2. Stage 0 archive representation/coverage results;
3. if qualified, Stage 1 1997–1998 precipitation completeness and directional comparison;
4. all failed/held paths;
5. an offline reproducibility check over the frozen source evidence used for any numerical result.

No publication package is modified by M36.