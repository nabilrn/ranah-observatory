<script lang="ts">
  import { copy, type Locale } from '$lib/i18n';
  import { repositoryUrl } from '$lib/catalog';
  import { eventLabel, type DisasterDistrictRow, type PublicDisasterSummary } from '$lib/public-data';

  export let data: { lang: Locale; summary: PublicDisasterSummary };
  const lang = data.lang;
  const t = copy[lang].disaster;
  const summary = data.summary;

  let period = String(summary.years.at(-1) ?? 2024);
  let region = 'all';
  let hazard = 'all';

  $: periodRows = summary.district_rows.filter((row) => row.year === Number(period));
  $: districtOptions = [...periodRows].sort((a, b) => a.name.localeCompare(b.name, lang === 'id' ? 'id-ID' : 'en-US'));
  $: if (region !== 'all' && !districtOptions.some((row) => row.geography_id === region)) region = 'all';
  $: filteredRows = periodRows.filter((row) => region === 'all' || row.geography_id === region);
  $: activeIndicators = hazard === 'all' ? summary.indicators : [hazard];
  $: eventTotal = filteredRows.reduce(
    (total, row) => total + activeIndicators.reduce((subtotal, indicator) => subtotal + (row.values[indicator] ?? 0), 0),
    0
  );

  const readiness = [
    {
      title: lang === 'id' ? 'Kejadian per kabupaten/kota' : 'Events by regency/city',
      state: 'ready',
      detail: lang === 'id' ? 'Observasi kanonik BNPB tersedia dan sekarang menjadi public artifact saat build.' : 'Canonical BNPB observations are available and now become a public artifact at build time.'
    },
    {
      title: lang === 'id' ? 'Korban dan masyarakat terdampak' : 'Casualties and affected population',
      state: 'building',
      detail: lang === 'id' ? 'Resource BPBD Sumbar 2023–2024 sudah masuk acquisition queue.' : '2023–2024 West Sumatra BPBD resources are already in the acquisition queue.'
    },
    {
      title: lang === 'id' ? 'Rumah dan fasilitas umum' : 'Housing and public facilities',
      state: 'building',
      detail: lang === 'id' ? 'Dataset kabupaten/kota sudah ditemukan; materialisasi dan validasi masih berjalan.' : 'Regency/city datasets have been identified; materialization and validation are still in progress.'
    },
    {
      title: lang === 'id' ? 'Kerugian ekonomi' : 'Economic losses',
      state: 'building',
      detail: lang === 'id' ? 'Dataset kerugian 2023 ditemukan, tetapi angka belum dipromosikan ke produk publik.' : 'A 2023 loss dataset has been found, but figures have not yet been promoted to the public product.'
    },
    {
      title: lang === 'id' ? 'Curah hujan' : 'Rainfall',
      state: 'ready',
      detail: lang === 'id' ? 'CHIRPS memberi baseline jangka panjang; observasi stasiun BMKG tetap diperlakukan terpisah.' : 'CHIRPS provides a long-run baseline; BMKG station observations remain a separate evidence class.'
    }
  ];

  function rowTotal(row: DisasterDistrictRow) {
    return activeIndicators.reduce((total, indicator) => total + (row.values[indicator] ?? 0), 0);
  }
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
    <p class="hero-note">{lang === 'id' ? 'Angka kejadian di bawah berasal dari canonical BNPB dan dihitung ulang saat public build. Angka korban, kerusakan, dan kerugian tetap ditahan sampai sumber impact lolos validasi.' : 'Event counts below come from canonical BNPB data and are rebuilt during the public build. Casualty, damage, and loss figures remain held until impact sources pass validation.'}</p>
  </section>

  <section class="section">
    <div class="toolbar">
      <select bind:value={period} aria-label={lang === 'id' ? 'Periode' : 'Period'}>
        {#each summary.years as year}<option value={String(year)}>{year}</option>{/each}
      </select>
      <select bind:value={region} aria-label={lang === 'id' ? 'Wilayah' : 'Region'}>
        <option value="all">{lang === 'id' ? 'Semua kabupaten/kota' : 'All regencies/cities'}</option>
        {#each districtOptions as district}
          <option value={district.geography_id}>{district.name}</option>
        {/each}
      </select>
      <select bind:value={hazard} aria-label={lang === 'id' ? 'Jenis bencana' : 'Hazard type'}>
        <option value="all">{lang === 'id' ? 'Semua jenis tersedia' : 'All available hazard types'}</option>
        {#each summary.indicators as indicator}
          <option value={indicator}>{eventLabel(indicator, lang)}</option>
        {/each}
      </select>
    </div>

    <div class="metric-grid" aria-label={lang === 'id' ? 'Metrik dampak' : 'Impact metrics'}>
      <div class="metric">
        <span>{lang === 'id' ? 'Kejadian tercatat' : 'Recorded events'}</span>
        <strong>{eventTotal.toLocaleString(lang === 'id' ? 'id-ID' : 'en-US')}</strong>
        <small>{period}{region === 'all' ? '' : ` · ${districtOptions.find((row) => row.geography_id === region)?.name ?? region}`}</small>
      </div>
      {#each [
        lang === 'id' ? 'Korban' : 'Casualties',
        lang === 'id' ? 'Rumah rusak' : 'Housing damage',
        lang === 'id' ? 'Fasilitas rusak' : 'Facility damage',
        lang === 'id' ? 'Kerugian' : 'Losses'
      ] as label}
        <div class="metric">
          <span>{label}</span>
          <strong>—</strong>
          <small>{lang === 'id' ? 'ditahan sampai sumber impact tervalidasi' : 'held until impact source is validated'}</small>
        </div>
      {/each}
    </div>
    <p class="hero-note" style="margin-top:14px">{summary.interpretation[lang]}</p>
  </section>

  <section class="section two-col">
    <div>
      <div class="section-head"><div><p class="eyebrow">MapLibre</p><h2>{t.mapTitle}</h2></div></div>
      <div class="map-shell">
        <div><strong>Public geospatial contract</strong><p>{t.mapPending}</p></div>
      </div>
    </div>
    <aside>
      <p class="eyebrow">Status</p>
      <h2>{t.contextTitle}</h2>
      {#each readiness as item}
        <article class="card" style="min-height:auto;margin-bottom:10px">
          <span class={`status ${item.state}`}>{item.state === 'ready' ? (lang === 'id' ? 'Siap' : 'Ready') : (lang === 'id' ? 'Dilengkapi' : 'Building')}</span>
          <h3>{item.title}</h3>
          <p>{item.detail}</p>
        </article>
      {/each}
    </aside>
  </section>

  <section class="section">
    <div class="section-head">
      <div><p class="eyebrow">{lang === 'id' ? 'Tabel sumber' : 'Source table'}</p><h2>{lang === 'id' ? 'Kejadian per kabupaten/kota' : 'Events by regency/city'}</h2></div>
      <p>{lang === 'id' ? 'Tabel mengikuti filter periode, wilayah, dan jenis bencana di atas. Tidak ada angka kosong yang diubah menjadi nol oleh frontend.' : 'The table follows the period, geography, and hazard filters above. The frontend never converts missing values into zero.'}</p>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>{lang === 'id' ? 'Kabupaten/kota' : 'Regency/city'}</th>
            {#each summary.indicators as indicator}<th>{eventLabel(indicator, lang)}</th>{/each}
            <th>{lang === 'id' ? 'Total terfilter' : 'Filtered total'}</th>
          </tr>
        </thead>
        <tbody>
          {#each filteredRows as row}
            <tr>
              <td><strong>{row.name}</strong></td>
              {#each summary.indicators as indicator}<td>{row.values[indicator] ?? '—'}</td>{/each}
              <td><strong>{rowTotal(row)}</strong></td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </section>

  <section class="section">
    <div class="section-head">
      <div><p class="eyebrow">{t.proofTitle}</p><h2>{lang === 'id' ? 'Dari temuan kembali ke file sumber' : 'From finding back to source file'}</h2></div>
      <p>{lang === 'id' ? 'Public artifact menyimpan path dan checksum sumber. Detail riset tetap tersedia satu tingkat lebih dalam.' : 'The public artifact retains the source path and checksum. Research detail remains available one level deeper.'}</p>
    </div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>{lang === 'id' ? 'Lapisan' : 'Layer'}</th><th>{lang === 'id' ? 'Status' : 'Status'}</th><th>{lang === 'id' ? 'Sumber' : 'Source'}</th><th>{lang === 'id' ? 'Bukti' : 'Evidence'}</th></tr></thead>
        <tbody>
          <tr><td>{lang === 'id' ? 'Kejadian bencana' : 'Disaster events'}</td><td>Materialized</td><td>{summary.source.organization}</td><td><a href={repositoryUrl(summary.source.path)}>{lang === 'id' ? 'Lihat data →' : 'View data →'}</a></td></tr>
          <tr><td>{lang === 'id' ? 'Dampak bencana 2023–2024' : '2023–2024 disaster impacts'}</td><td>Acquisition</td><td>BPBD Sumbar</td><td><a href={repositoryUrl('data/acquisition_requests/sumbarprov_priority_datasets.csv')}>{lang === 'id' ? 'Lihat antrean data →' : 'View acquisition queue →'}</a></td></tr>
          <tr><td>{lang === 'id' ? 'Curah hujan tahunan' : 'Annual rainfall'}</td><td>Materialized</td><td>CHIRPS v3</td><td><a href={repositoryUrl('data/processed/climate/rainfall/chirps-annual-rainfall-observations.csv')}>{lang === 'id' ? 'Lihat data →' : 'View data →'}</a></td></tr>
        </tbody>
      </table>
    </div>
    <p class="meta" style="margin-top:10px">SHA256: <code>{summary.source.sha256}</code> · {summary.source.row_count_used} {lang === 'id' ? 'baris sumber dipakai' : 'source rows used'}</p>
  </section>
</main>
