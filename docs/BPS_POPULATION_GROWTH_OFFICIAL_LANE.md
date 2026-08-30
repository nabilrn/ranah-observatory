# Official BPS Population-Growth Lane

## Objective

This micro-milestone asks one narrow question:

> Does the legacy BPS WebAPI Static Table index expose the official Sumatera Barat kabupaten/kota population-growth table in a machine-readable route?

No `population_growth` observation is promoted by this phase.

## Official evidence that the statistic exists

BPS Provinsi Sumatera Barat publishes the statistical table:

`Penduduk, Laju Pertumbuhan Penduduk, Distribusi Persentase Penduduk, Kepadatan Penduduk, Rasio Jenis Kelamin Penduduk Menurut Kabupaten/Kota di Provinsi Sumatera Barat`

Website source:

https://sumbar.bps.go.id/id/statistics-table/3/V1ZSbFRUY3lTbFpEYTNsVWNGcDZjek53YkhsNFFUMDkjMw%3D%3D/jumlah-penduduk--laju-pertumbuhan-penduduk--distribusi-persentase-penduduk--kepadatan-penduduk--rasio-jenis-kelamin-penduduk-menurut-kabupaten-kota-di-provinsi-sumatera-barat--2020.html?year=2020

The official SP2020 Sumatera Barat booklet states that SP2020 outputs are presented down to kabupaten/kota and include derived parameters such as population growth:

https://sumbar.bps.go.id/id/publication/2021/03/10/4914ff7966b08fa15826aa57/potret-sensus-penduduk-2020-provinsi-sumatera-barat-menuju-satu-data-kependudukan-indonesia.html

At province level, the official SP2020 release reports annual population growth for 2010–2020 of **1.29 percent**, down from **1.34 percent** for 2000–2010:

https://sumbar.bps.go.id/id/pressrelease/2021/01/21/950/hasil-sensus-penduduk-2020-provinsi-sumatera-barat.html

The province-level number confirms the official statistic family but is not substituted for kabupaten/kota values.

## Legacy BPS WebAPI route tested

Official BPS WebAPI documentation exposes Static Table services in JSON:

- list/search: `https://webapi.bps.go.id/v1/api/list/` with `model=statictable`, `domain`, optional `year`, and optional `keyword`;
- detail: `https://webapi.bps.go.id/v1/view` with `model=statictable`, `domain`, and static-table `id`;
- detail responses can expose table metadata, HTML table content, and an Excel locator.

Documentation:

https://webapi.bps.go.id/documentation/

The repository used a credentialed CI probe against domain `1300` with three bounded discovery routes:

1. keyword `laju pertumbuhan penduduk`;
2. keyword `pertumbuhan penduduk`;
3. full Static Table enumeration restricted to `year=2020` (up to 100 API pages).

## Live result: qualified negative finding

GitHub Actions run `31934235211` completed the probe successfully. The BPS API credential was valid and the API requests themselves succeeded.

The result was:

| Probe | API rows returned | Relevant candidates |
|---|---:|---:|
| keyword `laju pertumbuhan penduduk` | 0 | 0 |
| keyword `pertumbuhan penduduk` | 0 | 0 |
| Static Table `year=2020` enumeration | 0 | 0 |

Final classification:

`official_web_table_known_but_legacy_webapi_static_table_index_does_not_expose_candidate`

This is not evidence that the BPS website table does not exist. It means the **legacy WebAPI Static Table index is not a usable machine-readable discovery lane for this known modern website table as of the probe**.

The negative finding is useful because it prevents repeated attempts against the same legacy endpoint and distinguishes API-index coverage from website publication coverage.

## Evidence-class rule

The canonical indicator registry defines `population_growth` as **derived**. An official BPS-published growth rate is therefore not relabelled `observed` merely because BPS publishes it.

If an official row-level source is later promoted, intended semantics are:

- `indicator_id=population_growth`;
- `claim_type=derived`;
- provenance states that the value is an **official BPS-derived statistic**, not a Ranah Observatory calculation;
- the exact BPS period label, geography definition, and unit are retained.

## Next source lane

Because the legacy Static Table WebAPI lane is now qualified negative, the next bounded task should investigate the **modern statistics-table delivery path** used by the current BPS website or another official stable artifact attached to the SP2020 publication.

That task must remain read-only until it identifies a stable official row/file source. It should not fall back to iframe scraping or custom population-growth calculation because the legacy API is incomplete.

## Promotion gate

A later phase may promote values only after confirming:

1. a stable official BPS row/file source for the target table;
2. the target **2010–2020** growth statistic at kabupaten/kota level;
3. geography labels/codes without inference;
4. exact unit (percent per year or BPS equivalent);
5. census-derived rather than projection semantics;
6. durable provenance/checksum handling.

## Deliberately not included

This phase does not:

- calculate `(P2020/P2010)^(1/t)-1` itself;
- infer kabupaten/kota values from the province-level 1.29 percent figure;
- scrape the website iframe;
- treat projections as census growth;
- alter frozen SP2020 population counts;
- promote any `population_growth` rows.
