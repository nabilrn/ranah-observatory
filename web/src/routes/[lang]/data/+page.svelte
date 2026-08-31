<script lang="ts">
  import { categoryLabels, repositoryUrl, type DatasetCategory, type PublicDataCatalog } from '$lib/catalog';
  import { copy, type Locale } from '$lib/i18n';

  export let data: { lang: Locale; catalog: PublicDataCatalog };
  const lang = data.lang;
  const t = copy[lang].catalog;
  const catalog = data.catalog;

  let query = '';
  let category: 'all' | DatasetCategory = 'all';
  let status: 'all' | 'materialized' | 'building' = 'all';

  $: normalized = query.trim().toLocaleLowerCase(lang === 'id' ? 'id-ID' : 'en-US');
  $: filtered = catalog.datasets.filter((row) => {
    const categoryOk = category === 'all' || row.category === category;
    const statusOk = status === 'all' || row.status === status;
    const haystack = `${row.title[lang]} ${row.description[lang]} ${row.source} ${row.period} ${row.geography}`.toLocaleLowerCase(lang === 'id' ? 'id-ID' : 'en-US');
    return categoryOk && statusOk && (!normalized || haystack.includes(normalized));
  });
</script>

<svelte:head>
  <title>{t.title} — Ranah Observatory</title>
  <meta name="description" content={t.lead} />
</svelte:head>

<main class="page">
  <section class="hero">
    <div>
      <p class="eyebrow">{t.eyebrow}</p>
      <h1>{t.title}</h1>
      <p class="lead">{t.lead}</p>
    </div>
    <p class="hero-note"><strong>{catalog.summary.materialized_count}</strong> {lang === 'id' ? 'dataset/keluarga data siap digunakan.' : 'datasets/data families are ready to use.'}<br /><strong>{catalog.summary.building_count}</strong> {lang === 'id' ? 'masih dalam acquisition/normalization.' : 'are still in acquisition/normalization.'}<br /><strong>{catalog.summary.category_count}</strong> {lang === 'id' ? 'kategori sudah terwakili.' : 'categories are represented.'}</p>
  </section>

  <section class="section">
    <div class="toolbar">
      <input bind:value={query} type="search" placeholder={t.search} aria-label={t.search} />
      <select bind:value={category} aria-label={lang === 'id' ? 'Sektor' : 'Sector'}>
        <option value="all">{t.all}</option>
        {#each catalog.categories as item}
          <option value={item}>{categoryLabels[lang][item]}</option>
        {/each}
      </select>
      <select bind:value={status} aria-label={lang === 'id' ? 'Status dataset' : 'Dataset status'}>
        <option value="all">{lang === 'id' ? 'Semua status' : 'All statuses'}</option>
        <option value="materialized">{t.materialized}</option>
        <option value="building">{t.building}</option>
      </select>
    </div>

    <p class="meta">{filtered.length} {lang === 'id' ? 'dataset ditampilkan' : 'datasets shown'} · {lang === 'id' ? 'registry' : 'registry'}: <code>{catalog.source.path}</code></p>

    {#if filtered.length}
      <div aria-live="polite">
        {#each filtered as row}
          <article class="catalog-row">
            <div>
              <span class={`status ${row.status === 'materialized' ? 'ready' : 'building'}`}>{row.status === 'materialized' ? t.materialized : t.building}</span>
              <strong>{row.title[lang]}</strong>
              <small>{row.description[lang]}</small>
              <div class="pill-list">
                <span class="pill">{categoryLabels[lang][row.category]}</span>
                {#each row.formats as format}<span class="pill">{format}</span>{/each}
              </div>
            </div>
            <div><small>{t.source}</small><strong>{row.source}</strong></div>
            <div><small>{t.period}</small><strong>{row.period}</strong><small>{row.geography}</small></div>
            <div><a class="button secondary" href={repositoryUrl(row.source_path)}>{lang === 'id' ? 'Lihat bukti' : 'View evidence'}</a></div>
          </article>
        {/each}
      </div>
    {:else}
      <p>{t.empty}</p>
    {/if}
  </section>
</main>
