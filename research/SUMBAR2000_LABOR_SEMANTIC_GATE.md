# Sumbar 2000 Labor Semantic Gate

## Purpose

The complete official *Sumatera Barat Dalam Angka Tahun 2000* artifact is now source-qualified, but artifact completeness does not authorize blanket numeric promotion. This checkpoint screens the two Panel v3 labor outcomes—`labor_force_participation` and `unemployment_rate`—before any historical value is allowed into the canonical longitudinal panel.

## Evidence reviewed

The gate is bound to the exact official artifact SHA-256:

`689318d0760f99ff82a54866295b580a0159ed0e39051b4342b8b7e9d13648cf`

The bounded structural index exposes labor-related material in the 2000 yearbook. Two signals are especially important:

- PDF page 92 describes employment shares using a population-age-10-plus frame.
- PDF page 103 indexes a 1999–2000 work-by-main-industry table using the same age-10-plus frame.

These are semantic-warning signals, not substitutes for the exact TPAK/TPT table. They establish that historical labor material in this artifact cannot be assumed to share the modern panel's measurement contract merely because the indicator labels look familiar.

The modern canonical labor families are separately qualified in `docs/BPS_NORMALIZED_PANEL.md` as BPS August-Sakernas observations. Their qualification already preserves unresolved weighting-regime comparability rather than assuming a homogeneous time series.

## Decision

Historical 2000 TPAK/TPT remains fail-closed.

- No source-native TPAK/TPT numeric extraction is authorized yet.
- No canonical promotion is authorized.
- No Panel v3 backfill is authorized.
- No interpolation between 2000 and the modern panel is authorized.

The blocker is table-level identity, not source availability. Before a number can move forward, the exact 2000 table must establish its table number, pages, value, unit, reference period, source line, population universe, and methodological notes.

## Promotion boundary

A historical labor value may enter the current canonical indicator only after a deliberate comparison of the historical measurement contract with the qualified modern August-Sakernas contract. If equivalence cannot be demonstrated, the correct outcome is a separate source-native historical series with explicit methodology metadata—not a forced extension of Panel v3.

This follows the same evidence rule used elsewhere in Ranah Observatory: a complete official artifact can support discovery and bounded extraction, but semantic continuity must be proven independently.

## Adjacent candidate screened

The 2000 yearbook also contains rice harvested-area, yield, and production tables. Those tables are useful historical evidence, but the current `rice_yield` Panel v3 family is explicitly KSA-qualified. A pre-KSA 2000 yield must therefore undergo its own methodology gate before any longitudinal bridge is attempted; it is not bundled into this labor checkpoint.

## Next gate

1. Locate the exact 2000 TPAK and/or TPT table inside the SHA-bound official artifact.
2. Freeze the exact table identity, value, unit, reference period, source line, population universe, and footnotes.
3. Compare that contract against the qualified modern August-Sakernas family.
4. Promote only if equivalence is defensible; otherwise preserve a distinct historical source-native series.
5. Keep the 2000-to-modern gap missing rather than interpolated.
