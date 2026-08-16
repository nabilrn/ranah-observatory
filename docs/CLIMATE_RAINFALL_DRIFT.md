# CHIRPS Rainfall Baseline Drift Validation

## Objective

The repository now contains a frozen 1981–2025 CHIRPS v3 Final annual-rainfall baseline. Freezing the baseline creates a new responsibility: later changes in upstream CHIRPS objects or the BIG geometry service must become explicit review events rather than silently changing historical evidence.

This phase adds a **read-only drift validator**. It never rewrites observations, provenance, source contracts, or geometry.

## Baseline authority

The validator starts by running the frozen repository validator against:

`data/processed/climate/rainfall/`

Network drift checks are attempted only after the local baseline still passes its own schema, geography, hash, source-contract, evidence-class, and provenance constraints.

## CHIRPS source identity

The frozen source contract contains 540 monthly CHIRPS identities for January 1981 through December 2025.

Each identity records:

- exact upstream URL;
- ETag;
- Last-Modified value;
- reported full object length;
- SHA-256 of bytes 0–16383;
- explicit digest scope `sha256_first_16384_bytes_not_full_file_checksum`.

The drift validator requests the same 16,384-byte range and compares the current response with all frozen identity fields above.

A mismatch is a **drift signal**, not permission to regenerate the baseline automatically.

## BIG geometry identity

The frozen BIG source-contract item contains the exact Sumatera Barat query URL and full GeoJSON response SHA-256.

The drift validator fetches the complete response and compares:

- HTTP success;
- response byte length;
- full SHA-256.

A changed response is a review event because the June 2026 geometry snapshot is part of the rainfall methodology contract.

## Check modes

### `annual-anchors`

This is the default pull-request mode.

It checks:

- January for every year 1981–2025: 45 CHIRPS objects;
- December 2025 as the frozen end-of-series object;
- the one BIG geometry response.

Total network identities checked: 47.

This mode is deliberately lightweight. Passing it means the sampled frozen identities are stable; it does **not** prove that all 540 monthly CHIRPS objects are unchanged.

### `full`

This mode is available through `workflow_dispatch`.

It checks:

- all 540 frozen CHIRPS monthly identities;
- the BIG full-response identity.

This is the appropriate mode before a deliberate baseline requalification, source migration, or methodology revision.

It remains read-only.

## Result classes

Each upstream item receives one of three statuses:

- `stable` — all checked frozen identity fields still match;
- `drift` — upstream is reachable but one or more frozen identity fields changed;
- `transport_error` — the validator could not obtain the required upstream response.

Transport failure is kept separate from content drift. A temporary outage is not evidence that the historical dataset changed.

Both drift and unresolved transport failure make the strict workflow fail because either condition prevents the current run from positively confirming source stability.

## No silent replacement

The report always states:

`safe_to_silently_replace_baseline = false`

If drift is detected, the next action is investigation:

1. identify which source identity changed;
2. determine whether the change is metadata-only, object-content change, source reprocessing, or service replacement;
3. compare the resulting rainfall transformation if material;
4. decide whether a new methodology/source version is required;
5. preserve the old baseline rather than rewriting history in place.

## Relationship to BMKG validation

This drift validator answers a reproducibility question:

> Are the qualified upstream source identities still the same as those used for the frozen baseline?

It does not answer the independent-validity question:

> How closely do CHIRPS estimates represent station rainfall in Sumatera Barat?

`independent_station_validation=pending` therefore remains unchanged. BMKG station overlap is a separate research milestone.

## CI behavior

Pull requests affecting the drift checker, frozen rainfall baseline, or its validator run `annual-anchors` mode.

A full 540-object sweep is intentionally explicit through manual workflow dispatch so normal PR validation does not repeatedly impose the full upstream request load.

The workflow has read-only repository permission and uploads its JSON drift report even when the strict network comparison fails.
