# Sumbar construction qualification pre/post-update acquisition boundary

## Why this matters

The current construction-revision mechanism candidate is operationally plausible because BPS confirms a nationwide construction-directory update at the end of 2005, confirms directory updating as a construction-survey sampling-frame input, and documents qualification-based expansion in the annual survey. What has remained missing is a Sumatera Barat-specific before/after view of establishment composition by qualification.

This checkpoint obtains the **pre-update published baseline** and recovers the exact official BPS OPAC locator for the **post-update Book II source**, while keeping the comparison and causal gates closed until the post-update bytes/table are actually available.

## Pre-update published baseline: Sumatera Barat 2003

`Statistik Konstruksi 2004` was released by BPS on 12 September 2005, before the nationwide end-2005 updating described by later BPS catalog evidence.

Its Table 4.3 is titled:

`JUMLAH PERUSAHAAN KONSTRUKSI MENURUT KUALIFIKASI PER KABUPATEN TAHUN 2003`

For Sumatera Barat, the published province totals are:

| qualification | establishments |
|---|---:|
| B | 0 |
| M1 | 16 |
| M2 | 134 |
| K1 | 334 |
| K2 | 1,084 |
| K3 | 1,314 |
| **Total** | **2,882** |

The 16 district/city rows are frozen in:

`data/processed/bps/historical_construction_qualification_sumbar_2003.csv`

The row totals reproduce the provincial totals exactly.

This is deliberately called a **published pre-update qualification-composition baseline**. The table itself does not say that these 2,882 establishments are the exact sampling frame used to estimate the historical value series, so the repository does not relabel it as the `old frame`.

## Post-update target: Book II outside Java 2005

BPS catalog evidence identifies:

`Profil Perusahaan Konstruksi di Luar Pulau Jawa 2005`

with publication number `05230.0610`, catalog `6507`, ISBN `979-724-565-9`, and `xxiii + 647` pages. The catalog says the profile is based on the 2005 construction-directory updating and covers characteristics of construction establishments plus indicators for 2003-2005. Sumatera Barat is inside the publication's outside-Java scope.

### Official OPAC locator recovered

A live exact-title request through the public BPS OPAC `q` search field returned exactly the target title and exposed matching routes with record ID:

`111.0614.1380`

Official routes:

- detail: `https://perpustakaan.bps.go.id/opac/details/111.0614.1380`
- read/softcopy: `https://perpustakaan.bps.go.id/opac/read/111.0614.1380.pdf`

The record ID was returned by the official exact-title search. It was **not** guessed, incremented, enumerated, or brute-forced.

## Access boundary

A second acquisition probe requested only the verified read URL. The request ended at:

`https://sso-pst.bps.go.id/login`

with HTTP 200 HTML, not PDF bytes. PDF magic and EOF checks both failed, so no candidate artifact was saved.

This establishes a transport-access boundary:

`official OPAC record recovered; softcopy SSO-gated`

It does not establish that the artifact is absent. It also does not authorize use of a mirror as byte-equivalent official evidence.

## What can and cannot be compared yet

Available now:

- pre-update Sumatera Barat 2003 qualification composition;
- post-update publication identity;
- exact official OPAC record ID;
- exact official detail/read routes;
- evidence that anonymous softcopy access is SSO-gated.

Still unavailable:

- raw Book II PDF bytes;
- exact post-update Sumatera Barat qualification table;
- table year and denominator semantics needed for a defensible comparison;
- old/new Sumatera Barat frame counts;
- a value-estimation bridge tying establishment composition to the revised 2001-2003 construction values.

Therefore no pre/post composition delta is calculated yet.

## Next gate

The next successful step is to obtain either:

1. the official Book II PDF bytes, or
2. another official BPS text surface exposing the relevant Sumatera Barat table with sufficient title/year/definition context.

Only then can the project test whether the 2003 and post-update qualification categories are comparable. Even a large composition change would initially be classified as **profile/frame evidence**, not as proof that the directory update caused the historical value revision.

All bridge, backcast, causal-attribution, and Panel v3 integration gates remain closed.
