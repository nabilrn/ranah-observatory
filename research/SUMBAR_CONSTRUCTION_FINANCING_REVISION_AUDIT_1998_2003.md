# Sumbar construction-financing revision audit, 1998–2003

## Purpose

This checkpoint converts the BPS construction-financing evidence into a **release-aware historical series** rather than a single mutable value per year.

Two annual BPS publications overlap for 1999–2002:

- `Statistik Konstruksi 2002` — released 2003-09-15, covering 1998–2002;
- `Statistik Konstruksi 2003` — released 2004-07-19, covering 1999–2003.

Both carry `Angka Sementara/Preliminary Figures`. The later publication visibly marks 1999–2001 year headers with `R`; its meaning is not inferred here without an explicit source definition.

## Storage rule

Ranah Observatory retains **both release-specific values**. A later publication does not silently overwrite the earlier record.

For each measure/year the revision delta is:

`Statistik Konstruksi 2003 value − Statistik Konstruksi 2002 value`

All values are in `000 Rupiah` and remain nominal source values.

## Release-to-release revisions

### 1999

Only APBN changes:

- APBN: `137,521,571 → 137,521,568` (`−3` thousand rupiah);
- reported total: unchanged at `341,872,541`.

This three-thousand-rupiah revision removes the exact three-thousand-rupiah excess that existed when the five 1999 financing components from the earlier release were summed against the reported total.

### 2000

All six measures are identical across both publications:

- total: `345,371,439`;
- APBN: `207,997,331`;
- APBD: `39,956,642`;
- foreign loan: `76,727,103`;
- BUMN: `1,229,691`;
- other sources: `19,460,672`.

The five components reconcile exactly to the total in both releases. This makes 2000 the strongest currently reviewed year in this table family.

### 2001

No release-to-release value changes are observed in the six measures. However, the five financing components sum to **one thousand rupiah less** than the independently reported total in both releases.

The residual is preserved exactly as published. Ranah Observatory does not manufacture a one-thousand-rupiah adjustment to force balance.

### 2002

The later publication revises:

- total: `−11`;
- APBN: `−6`;
- APBD: `−1`;
- foreign loan: `−2`;
- BUMN: `−1`;
- other sources: `0`.

In the earlier publication the component sum is one thousand rupiah below the reported total. After the later revisions, the five components reconcile exactly to the revised total of `458,502,968` thousand rupiah.

### Boundary years

1998 is available only in the earlier publication window used here. 2003 is available only in the later publication window. They are retained as single-release observations rather than being falsely labelled cross-validated.

## Within-release reconciliation

Component-sum minus reported-total residuals (`000 Rupiah`):

| Release | 1998 | 1999 | 2000 | 2001 | 2002 | 2003 |
|---|---:|---:|---:|---:|---:|---:|
| Statistik Konstruksi 2002 | 0 | +3 | 0 | -1 | -1 | — |
| Statistik Konstruksi 2003 | — | 0 | 0 | -1 | 0 | 0 |

These residuals are evidence about publication consistency. They are not corrected by inference.

## Semantic boundary

The series remains construction-establishment output classified by financing source. It is not converted to:

- fiscal realization;
- APBD/APBN expenditure composition;
- DJPK capital expenditure;
- public investment;
- construction-sector GRDP;
- real/constant-price construction value.

No Panel v3 bridge, deflation, interpolation, or causal analysis is authorized by this checkpoint.

## Analytical implication

The key research lesson is methodological: **historical official statistics must be versioned by release**. Even tiny revisions can change arithmetic reconciliation and therefore provenance. A longitudinal pipeline that keeps only the most recent visible number would destroy evidence about revision behavior.

This checkpoint therefore authorizes release-aware descriptive trajectory work only. It does not authorize choosing a preferred release for model input without a separate rule.

## Next gate

Extend the same release-aware audit to subsequent annual construction publications and determine whether:

1. historical revisions converge after one or more releases;
2. table definitions remain stable;
3. unit and financing categories remain comparable;
4. an explicit final/preliminary status can be recovered from source documentation.
