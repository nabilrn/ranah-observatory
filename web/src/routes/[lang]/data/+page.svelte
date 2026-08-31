<script lang="ts">
  import { categoryLabels, datasets, repositoryUrl } from '$lib/catalog';
  import { copy, type Locale } from '$lib/i18n';

  export let data: { lang: Locale };
  const lang = data.lang;
  const t = copy[lang].catalog;
  const categories = [...new Set(datasets.map((row) => row.category))];

  let query = '';
  let category = 'all';

  $: normalized = query.trim().toLocaleLowerCase(lang === 'id' ? 'id-ID' : 'en-US');
  $: filtered = datasets.filter((row) => {
    const categoryOk = category === 'all' || row.category === category;
    const haystack = `${row.title[lang]} ${row.description[lang]} ${row.source} ${row.period} ${row.geography}`.toLocaleLowerCase(lang === 'id' ? 'id-ID' : 'en-US');
    return categoryOk && (!normalized || haystack.includes(normalized));
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
    <p class="hero-note"><strong>{datasets.filter((row) => row.status === 'materialized').length}</strong> {lang === 'id' ? 'dataset/keluarga data sudah materialized di adapter awal.' : 'datasets/data families are materialized in the initial adapter.'}<br /><strong>{datasets.filter((row) => row.status === 'building').length}</strong> {lang === 'id' ? 'masih dalam acquisition/normalization.' : 'are still in acquisition/normalization.'}</p>
  </section>

  <section class="section">
    <div class="toolbar">
      <input bind:value={query} type="search" placeholder={t.search} aria-label={t.search} />
      <select bind:value={category} aria-label={lang === 'id' ? 'Sektor' : 'Sector'}>
        <option value="all">{t.all}</option>
        {#each categories as item}
          <option value={item}>{categoryLabels[lang][item]}</option>
        {/each}
      </select>
      <select aria-label={lang === 'id' ? 'Status dataset' : 'Dataset status'} disabled>
        <option>{lang === 'id' ? 'Semua status' : 'All statuses'}</option>
      </select>
    </div>

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
            <div><small>{t.period}</small><strong>{row.period}</strong></div>
            <div><a class="button secondary" href={repositoryUrl(row.sourcePath)}>{lang === 'id' ? 'Lihat bukti' : 'View evidence'}</a></div>
          </article>
        {/each}
      </div>
    {:else}
      <p>{t.empty}</p>
    {/if}
  </section>
</main>
