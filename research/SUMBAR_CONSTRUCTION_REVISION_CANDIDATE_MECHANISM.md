# Sumatera Barat construction revision candidate mechanism

## Purpose

The revision event is now proven and localized by publication vintage. This checkpoint asks a narrower question: **what operational mechanism could have produced the revised historical construction series?**

The answer is not yet a causal conclusion. The evidence supports a specific candidate mechanism strongly enough to track and test, while still failing closed on attribution.

## Confirmed period evidence

### 1. Nationwide construction-directory updating at the end of 2005

The official BPS `Katalog Publikasi 2007` records `Profil Perusahaan Konstruksi 2005` (publication `05230.0609`) as the result of an Updating Direktori Perusahaan Konstruksi activity conducted simultaneously throughout Indonesia at the end of 2005.

The same catalog lists the separate `Profil Perusahaan Konstruksi di Luar Pulau Jawa 2005` (publication `05230.0610`). This is geographically relevant to Sumatera Barat. Its catalog description says the profile is based on the 2005 construction-directory updating, presents construction-activity indicators for 2003-2005, and that the presented data are results of the annual construction establishment survey.

This is a direct operational connection between the directory environment and annual-survey outputs in the exact period when the revised vintage emerges.

### 2. The 2005 updating output was used as a construction-survey sampling frame

BPS-authored `Ringkasan Metadata Kegiatan Statistik 2009` (publication `03210.0803`) records the activity `Updating Direktori Perusahaan Konstruksi` with:

- data year: 2005;
- coverage: all provinces in Indonesia;
- respondents: about 20,450 construction establishments from about 80,000 establishments;
- output: report of the construction-establishment updating activity;
- recorded use: `Sampling frame kegiatan survei konstruksi sebagai direktori awal perusahaan konstruksi`.

The publication is accessible through a mirror, but identifies BPS as manuscript author and publisher and retains `bps.go.id` page markings. A screenshot fetch was attempted and failed with a cache miss; no screenshot evidence is claimed.

This upgrades the directory-update lead from temporal coincidence to a **confirmed survey-frame role**.

### 3. BPS construction surveys use frame, qualification strata, and expansion to population

`Aktivitas BPS 2010` provides later institutional method documentation:

- construction-directory updating is required to obtain an up-to-date frame;
- annual construction survey sampling is take-all for grades 5-7 and take-some for grades 2-4;
- for the annual survey, population estimates for each characteristic use establishment qualification as the basis of the expansion factor.

This supplies a concrete estimator pathway through which a changed directory and changed qualification composition **can** change population-level estimates.

However, this is 2010 documentation. It does not prove that the identical algorithm was used when BPS revised the 2001-2003 series in the 2005/2006 publication cycle. The screenshot attempt on the mirrored report also failed with a cache miss.

### 4. The revised publication environment remains annual-survey based

The official BPS catalog describes `Statistik Konstruksi 2005` (publication `05230.0607`) as an annual construction-establishment statistical series through 2004 resulting from the Annual Construction Establishment Survey.

Thus, the large revision cannot be dismissed as a simple switch from an unrelated data source. It occurred inside an annual construction-survey publication environment.

## Candidate mechanism

The tracked candidate is:

`sampling_frame_refresh_plus_qualification_based_expansion_reestimation`

The hypothesis is that the nationwide end-2005 directory refresh changed the frame and/or qualification composition available for construction-survey estimation, creating an operational basis for re-estimating population-level historical characteristics.

This is supported by a chain of source evidence:

1. a nationwide directory update occurred at the right time;
2. BPS metadata explicitly says the 2005 update was used as a construction-survey sampling frame;
3. the outside-Java profile links the 2005 updating basis to annual-survey indicators in a publication relevant to Sumatera Barat;
4. BPS later documents qualification-based expansion factors in the annual construction survey;
5. the revised 2001-2003 series appears in the first examined yearbook vintage after that updating period.

## Why causation is still unproven

None of the acquired sources states:

> the 2001-2003 Sumatera Barat construction values were recalculated because of the 2005 directory update.

Nor do we yet have:

- a 2005/2006 survey manual explicitly replacing the prior historical-estimation frame;
- old and new Sumatera Barat frame counts by qualification stratum;
- historical weights or expansion factors;
- a revision note documenting the recomputation;
- a reproducible formula converting the old vintage to the revised vintage.

Therefore the mechanism status is:

`operationally_plausible_period_link_confirmed_causal_revision_link_unproven`

## Numerical clue, not proof

The revised/earlier ratios are:

- 2001 total: `1.564437370`;
- 2002 total: `1.564437371`.

The near-perfect common scaling is compatible with a multiplier or expansion-factor change. It does not uniquely identify one. Financing-source components do not all move by the same factor, and the 2003 revision is highly heterogeneous.

The common ratio must **not** be applied as a backcast factor.

## Hard gate

Until contemporaneous documentation or reproducible weights are recovered:

- retain all vintages;
- no silent overwrite;
- no single continuous 1998-2006 trajectory;
- no cross-vintage bridge;
- no use of the common ratio as a backcast/revision factor;
- do not attribute the revision to the 2005 directory update as fact;
- no DJPK fiscal mapping;
- no Panel v3 integration;
- no causal claim.

The next high-value evidence target is a **2005/2006 construction survey manual or revision note containing frame, stratum, weighting, or expansion-factor details**.
