<script lang="ts">
  import type { PublicDataCatalog } from '$lib/catalog';
  import { copy, type Locale } from '$lib/i18n';

  export let data: { lang: Locale; catalog: PublicDataCatalog };
  const lang = data.lang;
  const t = copy[lang];
  const catalog = data.catalog;

  const sectors = lang === 'id'
    ? [
        ['Bencana', 'Kejadian, dampak, exposure, faktor terkait, dan risiko.'],
        ['Ekonomi', 'Pertumbuhan, produktivitas, investasi, tenaga kerja, dan gap pembangunan.'],
        ['Infrastruktur', 'Konektivitas, internet, layanan dasar, dan kapasitas wilayah.'],
        ['Penduduk', 'Perubahan penduduk dan struktur demografi lintas waktu.'],
        ['Pendidikan', 'Akses, capaian, dan human capital.'],
        ['Lingkungan', 'Curah hujan, tutupan lahan, DAS, lereng, dan tekanan lingkungan.']
      ]
    : [
        ['Disaster', 'Events, impacts, exposure, related factors, and risk.'],
        ['Economy', 'Growth, productivity, investment, labor, and development gaps.'],
        ['Infrastructure', 'Connectivity, internet, basic services, and regional capacity.'],
        ['Population', 'Population change and demographic structure over time.'],
        ['Education', 'Access, outcomes, and human capital.'],
        ['Environment', 'Rainfall, land cover, watersheds, slope, and environmental pressure.']
      ];
</script>

<svelte:head>
  <title>{lang === 'id' ? 'Ranah Observatory — Sumatera Barat dalam data' : 'Ranah Observatory — West Sumatra in data'}</title>
  <meta name="description" content={t.home.lead} />
</svelte:head>

<main class="page">
  <section class="hero">
    <div>
      <p class="eyebrow">{t.home.eyebrow}</p>
      <h1>{t.home.title}</h1>
      <p class="lead">{t.home.lead}</p>
      <div class="actions">
        <a class="button primary" href={`/${lang}/explore/disaster`}>{lang === 'id' ? 'Explore bencana' : 'Explore disasters'}</a>
        <a class="button secondary" href={`/${lang}/data`}>{t.nav.data}</a>
      </div>
    </div>
    <p class="hero-note">{t.home.note}<br /><br /><strong>{catalog.summary.dataset_count}</strong> {lang === 'id' ? 'dataset/keluarga data sudah terdaftar pada katalog publik.' : 'datasets/data families are registered in the public catalog.'}<br /><strong>{catalog.summary.materialized_count}</strong> {lang === 'id' ? 'sudah materialized.' : 'are materialized.'}</p>
  </section>

  <section class="section">
    <div class="section-head">
      <div>
        <p class="eyebrow">Explore</p>
        <h2>{t.home.exploreTitle}</h2>
      </div>
      <p>{t.home.exploreText}</p>
    </div>
    <div class="grid">
      {#each sectors as sector, index}
        {#if index === 0}
          <a class="card card-link" href={`/${lang}/explore/disaster`}>
            <span class="status ready">{lang === 'id' ? 'Vertical pertama' : 'First vertical'}</span>
            <h3>{sector[0]}</h3>
            <p>{sector[1]}</p>
          </a>
        {:else}
          <article class="card">
            <span class="status building">{lang === 'id' ? 'Berikutnya' : 'Next'}</span>
            <h3>{sector[0]}</h3>
            <p>{sector[1]}</p>
          </article>
        {/if}
      {/each}
    </div>
  </section>

  <section class="section two-col">
    <div>
      <p class="eyebrow">Investment context</p>
      <h2>{t.home.investorTitle}</h2>
      <p class="lead">{t.home.investorText}</p>
    </div>
    <div class="card">
      <h3>{lang === 'id' ? 'Prinsip tampilan investor' : 'Investor-view principle'}</h3>
      <p>{lang === 'id' ? 'Bandingkan indikator yang dapat diperiksa satu per satu: PDRB, pertumbuhan, investasi, tenaga kerja, jalan, internet, layanan dasar, dan risiko bencana.' : 'Compare inspectable indicators one by one: GRDP, growth, investment, labor, roads, internet, basic services, and disaster risk.'}</p>
      <p class="meta">{lang === 'id' ? 'Tidak ada skor investasi sintetis tanpa metodologi defensible.' : 'No synthetic investment score without a defensible methodology.'}</p>
    </div>
  </section>
</main>
