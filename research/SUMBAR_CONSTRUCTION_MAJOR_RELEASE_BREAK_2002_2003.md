# Sumatera Barat construction financing major release break, 2002-2003

## Purpose

This checkpoint freezes a major cross-release discontinuity in BPS construction-establishment statistics before any longer 1998-2006 trajectory is allowed.

It compares the already-frozen `Statistik Konstruksi 2003` vintage against the later BPS compilation `Statistik Tahunan Perusahaan Konstruksi 2002-2006` for Sumatera Barat, using the same source-native table family:

- Table 14: value of construction completed by province;
- Table 15.1: financed by APBN / central-government budget;
- Table 15.2: financed by APBD / local-government budget;
- Table 15.3: financed by foreign loan;
- Table 15.4: financed by BUMN / state enterprises;
- Table 15.5: financed by other sources.

All values remain in the source unit `000 Rupiah`, nominal current rupiah as published.

## Source releases

### Earlier vintage: Statistik Konstruksi 2003

BPS publication number `05230.0407`, released 19 July 2004.

The publication explanation states two method facts that are material here:

1. the annual construction statistics presented are results of the **2002 Annual Construction Establishment Survey**;
2. **preliminary 2003 figures are estimates from the Quarterly Construction Survey**, using 2003-over-2002 growth.

Therefore 2002 and 2003 do not have the same evidence status inside this vintage.

### Later vintage: Statistik Tahunan Perusahaan Konstruksi 2002-2006

BPS publication number `05340.0704`, released 15 May 2007.

Its foreword states that the 2002-2006 series results from **Annual Construction Establishment Surveys**. Its estimation section explicitly identifies **2006** as the preliminary year estimated from the quarterly survey using 2006-over-2005 growth. The scope remains national construction establishments operating in Indonesia, and the construction-value definition remains work completed by contractors during the enumeration period based on contract value and realized projects.

This later release therefore provides a materially different evidence status for 2003 than the 2004 publication did.

## Major break: 2002

The 2002 values are both presented as annual-survey statistics, yet the later release is much larger:

| Measure | 2004 release | 2007 release | Delta | Delta % |
| --- | ---: | ---: | ---: | ---: |
| Total construction completed | 458,502,968 | 717,299,178 | +258,796,210 | +56.443737% |
| APBN-financed | 291,959,524 | 356,752,390 | +64,792,866 | +22.192414% |
| APBD-financed | 53,045,032 | 182,985,630 | +129,940,598 | +244.962804% |
| Foreign-loan financed | 101,860,202 | 159,353,907 | +57,493,705 | +56.443737% |
| BUMN-financed | 4,507,982 | 7,052,456 | +2,544,474 | +56.443748% |
| Other sources | 7,130,228 | 11,154,795 | +4,024,567 | +56.443735% |

Both vintages reconcile exactly: their five financing components sum to their own reported total with zero residual.

A numerical pattern is visible: total, foreign-loan, BUMN, and other-source values are scaled by approximately the same `1.564437` factor, while APBN and APBD move by different factors. This is recorded only as a descriptive pattern. The available BPS method text does **not** identify a revision formula, reweighting, frame change, coverage expansion, or rebenchmarking operation that explains the shift.

Accordingly, 2002 is classified as `major_release_break_unexplained`.

## Major break: 2003

The 2003 total rises from `469,007,986` to `844,516,928` thousand rupiah, an increase of `80.064509%`.

The financing components also change heterogeneously:

| Measure | Earlier preliminary vintage | Later annual-survey series | Delta % |
| --- | ---: | ---: | ---: |
| APBN-financed | 298,648,772 | 303,268,240 | +1.546790% |
| APBD-financed | 54,260,376 | 108,161,492 | +99.337896% |
| Foreign-loan financed | 104,193,978 | 161,858,669 | +55.343593% |
| BUMN-financed | 4,611,267 | 1,256,000 | -72.762367% |
| Other sources | 7,293,593 | 269,972,527 | +3601.502497% |

Again, both releases reconcile exactly within themselves.

Here the source gives a real status transition: the earlier 2003 value was a quarterly-growth preliminary estimate, while the later compilation describes the series as Annual Construction Establishment Survey results and reserves the explicit preliminary-estimation treatment for 2006.

That supports classification as `major_release_break_status_transition`, not as a routine numeric revision. It still does **not** provide a mechanical conversion formula between vintages.

## Hard gate

Until a source explicitly documents the 2002 release break or a defensible harmonization contract is established:

- retain both vintages;
- never silently overwrite the earlier release;
- do not splice 1998-2003 values directly into the 2002-2006 vintage;
- do not claim a single continuous 1998-2006 trajectory;
- do not map these source-of-financing categories to DJPK fiscal accounts;
- do not integrate them into Panel v3;
- do not deflate, interpolate, or use them for causal claims as if the release break were resolved.

The correct state is **release-aware and fail-closed**.

## Evidence boundary

The later 2007 publication is available from the official BPS publication page and official PDF text layer. Its tables 14 and 15.1-15.5 were verified at PDF indices 63 and 80-84 respectively. A screenshot attempt through the research tool failed because of a cache miss, so screenshot evidence is not claimed.

The repository still does not hold SHA-256 fingerprints for these national BPS publication PDFs. Official BPS text evidence is sufficient for this checkpoint's table-level comparison, but it is not treated as an artifact-SHA substitute.
