# Official BPS Population-Growth Lane

## Objective

This micro-milestone answers one narrow question:

> Does BPS provide an official, programmatically discoverable source for population growth by kabupaten/kota in Sumatera Barat, so the observatory can avoid inventing a custom growth series from incompletely qualified census/SUPAS anchor pairs?

No `population_growth` observation is promoted by this phase.

## Official evidence that the statistic exists

BPS Provinsi Sumatera Barat publishes the statistical table:

`Penduduk, Laju Pertumbuhan Penduduk, Distribusi Persentase Penduduk, Kepadatan Penduduk, Rasio Jenis Kelamin Penduduk Menurut Kabupaten/Kota di Provinsi Sumatera Barat`

Website source:

https://sumbar.bps.go.id/id/statistics-table/3/V1ZSbFRUY3lTbFpEYTNsVWNGcDZjek53YkhsNFFUMDkjMw%3D%3D/jumlah-penduduk--laju-pertumbuhan-penduduk--distribusi-persentase-penduduk--kepadatan-penduduk--rasio-jenis-kelamin-penduduk-menurut-kabupaten-kota-di-provinsi-sumatera-barat--2020.html?year=2020

The official SP2020 Sumatera Barat booklet also states that SP2020 outputs are presented down to kabupaten/kota and include derived parameters such as population growth:

https://sumbar.bps.go.id/id/publication/2021/03/10/4914ff7966b08fa15826aa57/potret-sensus-penduduk-2020-provinsi-sumatera-barat-menuju-satu-data-kependudukan-indonesia.html

At province level, the official SP2020 release reports annual population growth for 2010–2020 of **1.29 percent**, down from **1.34 percent** for 2000–2010:

https://sumbar.bps.go.id/id/pressrelease/2021/01/21/950/hasil-sensus-penduduk-2020-provinsi-sumatera-barat.html

The province-level number confirms the official statistic family but is not substituted for kabupaten/kota values.

## Machine-readable route

Official BPS WebAPI documentation exposes Static Table services in JSON:

- list/search: `https://webapi.bps.go.id/v1/api/list/` with `model=statictable`, `domain`, optional `year`, and optional `keyword`;
- detail: `https://webapi.bps.go.id/v1/view` with `model=statictable`, `domain`, and static-table `id`;
- detail responses can expose table metadata, HTML table content, and an Excel locator.

Documentation:

https://webapi.bps.go.id/documentation/

The repository probe uses domain `1300` and searches only for titles containing both:

- `laju pertumbuhan penduduk`;
- `kabupaten/kota`.

The live CI artifact records candidate IDs and official detail responses for review.

## Evidence-class rule

The canonical indicator registry currently defines `population_growth` as a **derived** indicator. An official BPS-published growth rate is therefore not to be relabelled `observed` merely because BPS publishes it.

If this lane is later promoted, the intended semantics are:

- `indicator_id=population_growth`;
- `claim_type=derived`;
- provenance explicitly states that the value is an **official BPS-derived statistic**, not a Ranah Observatory calculation;
- the exact source period label and geography definition must be retained.

This preserves the distinction between a direct population count and a rate calculated from population anchors.

## Promotion gate

Discovery is not ingestion.

A later phase may promote values only after confirming:

1. an official BPS static-table candidate is machine-readable or has a stable official file locator;
2. the table actually exposes the target 2010–2020 growth statistic at kabupaten/kota level;
3. all geography labels/codes can be mapped without inference;
4. the unit is percent per year or its exact BPS equivalent;
5. the period is explicitly 2010–2020, not a projection period or another interval;
6. no projected population series is silently mixed with SP2010/SP2020 census growth;
7. the table/source artifact receives durable provenance and checksum handling.

## Deliberately not included

This phase does not:

- calculate `(P2020/P2010)^(1/t)-1` itself;
- infer kabupaten/kota values from the province-level 1.29 percent figure;
- scrape the website iframe;
- treat projections as census growth;
- alter the frozen SP2020 population counts;
- promote any `population_growth` rows.
