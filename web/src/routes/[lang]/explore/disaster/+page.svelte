<script lang="ts">
  import { copy, type Locale } from '$lib/i18n';
  import { repositoryUrl } from '$lib/catalog';

  export let data: { lang: Locale };
  const lang = data.lang;
  const t = copy[lang].disaster;

  let period = '2024';
  let region = 'all';
  let hazard = 'all';

  const readiness = [
    {
      title: lang === 'id' ? 'Kejadian per kabupaten/kota' : 'Events by regency/city',
      state: 'ready',
      detail: lang === 'id' ? 'Observasi kanonik BNPB 2024 tersedia untuk kejadian banjir dan longsor.' : 'Canonical 2024 BNPB observations are available for flood and landslide events.'
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
    <p class="hero-note">{lang === 'id' ? 'Filter ini sudah menjadi contract UI. Angka tidak akan diisi dengan placeholder palsu ketika source impact belum lolos materialisasi.' : 'These filters are already part of the UI contract. No fake placeholder figures will be shown while impact sources are still awaiting materialization.'}</p>
  </section>

  <section class="section">
    <div class="toolbar">
      <select bind:value={period} aria-label={lang === 'id' ? 'Periode' : 'Period'}>
        <option value="2024">2024</option>
      </select>
      <select bind:value={region} aria-label={lang === 'id' ? 'Wilayah' : 'Region'}>
        <option value="all">{lang === 'id' ? 'Semua kabupaten/kota' : 'All regencies/cities'}</option>
      </select>
      <select bind:value={hazard} aria-label={lang === 'id' ? 'Jenis bencana' : 'Hazard type'}>
        <option value="all">{lang === 'id' ? 'Semua jenis bencana' : 'All hazard types'}</option>
        <option value="flood">{lang === 'id' ? 'Banjir' : 'Flood'}</option>
        <option value="landslide">{lang === 'id' ? 'Tanah longsor' : 'Landslide'}</option>
      </select>
    </div>

    <div class="metric-grid" aria-label={lang === 'id' ? 'Metrik dampak' : 'Impact metrics'}>
      {#each [
        lang === 'id' ? 'Kejadian' : 'Events',
        lang === 'id' ? 'Korban' : 'Casualties',
        lang === 'id' ? 'Rumah rusak' : 'Housing damage',
        lang === 'id' ? 'Fasilitas rusak' : 'Facility damage',
        lang === 'id' ? 'Kerugian' : 'Losses'
      ] as label, index}
        <div class="metric">
          <span>{label}</span>
          <strong>{index === 0 ? 'BNPB' : '—'}</strong>
          <small>{index === 0 ? (lang === 'id' ? 'data tersedia; agregasi publik berikutnya' : 'data available; public aggregation next') : (lang === 'id' ? 'ditahan sampai valid' : 'held until validated')}</small>
        </div>
      {/each}
    </div>
  </section>

  <section class="section two-col">
    <div>
      <div class="section-head"><div><p class="eyebrow">MapLibre</p><h2>{t.mapTitle}</h2></div></div>
      <div class="map-shell">
        <div><strong>{lang === 'id' ? 'Public geospatial contract' : 'Public geospatial contract'}</strong><p>{t.mapPending}</p></div>
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
      <div><p class="eyebrow">{t.proofTitle}</p><h2>{lang === 'id' ? 'Dari temuan kembali ke file sumber' : 'From finding back to source file'}</h2></div>
      <p>{lang === 'id' ? 'Ini menggantikan claim ID teknis sebagai pengalaman utama. Detail riset tetap tersedia satu tingkat lebih dalam.' : 'This replaces technical claim IDs as the primary experience. Research detail remains available one level deeper.'}</p>
    </div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>{lang === 'id' ? 'Lapisan' : 'Layer'}</th><th>{lang === 'id' ? 'Status' : 'Status'}</th><th>{lang === 'id' ? 'Sumber' : 'Source'}</th><th>{lang === 'id' ? 'Bukti' : 'Evidence'}</th></tr></thead>
        <tbody>
          <tr><td>{lang === 'id' ? 'Kejadian banjir & longsor 2024' : '2024 flood & landslide events'}</td><td>{lang === 'id' ? 'Materialized' : 'Materialized'}</td><td>BNPB / DIBI</td><td><a href={repositoryUrl('data/processed/bnpb/disaster/bnpb-disaster-canonical-observations.csv')}>{lang === 'id' ? 'Lihat data →' : 'View data →'}</a></td></tr>
          <tr><td>{lang === 'id' ? 'Dampak bencana 2023–2024' : '2023–2024 disaster impacts'}</td><td>{lang === 'id' ? 'Acquisition' : 'Acquisition'}</td><td>BPBD Sumbar</td><td><a href={repositoryUrl('data/acquisition_requests/sumbarprov_priority_datasets.csv')}>{lang === 'id' ? 'Lihat antrean data →' : 'View acquisition queue →'}</a></td></tr>
          <tr><td>{lang === 'id' ? 'Curah hujan tahunan' : 'Annual rainfall'}</td><td>{lang === 'id' ? 'Materialized' : 'Materialized'}</td><td>CHIRPS v3</td><td><a href={repositoryUrl('data/processed/climate/rainfall/chirps-annual-rainfall-observations.csv')}>{lang === 'id' ? 'Lihat data →' : 'View data →'}</a></td></tr>
        </tbody>
      </table>
    </div>
  </section>
</main>
