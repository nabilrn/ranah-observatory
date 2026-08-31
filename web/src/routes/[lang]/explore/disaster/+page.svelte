<script lang="ts">
  import { copy, type Locale } from '$lib/i18n';
  import { repositoryUrl } from '$lib/catalog';
  import DisasterMap from '$lib/components/DisasterMap.svelte';
  import {
    eventLabel,
    impactLabel,
    type DisasterDistrictRow,
    type ImpactDistrictRow,
    type PublicDisasterSummary,
    type PublicDistrictBoundary
  } from '$lib/public-data';

  export let data: { lang: Locale; summary: PublicDisasterSummary; geography: PublicDistrictBoundary };
  const lang = data.lang;
  const t = copy[lang].disaster;
  const summary = data.summary;
  const events = summary.events;
  const impact = summary.impact;

  let period = String(events.years.at(-1) ?? 2024);
  let region = 'all';
  let hazard = 'all';

  $: periodRows = events.district_rows.filter((row) => row.year === Number(period));
  $: districtOptions = [...periodRows].sort((a, b) => a.name.localeCompare(b.name, lang === 'id' ? 'id-ID' : 'en-US'));
  $: if (region !== 'all' && !districtOptions.some((row) => row.geography_id === region)) region = 'all';
  $: filteredRows = periodRows.filter((row) => region === 'all' || row.geography_id === region);
  $: activeIndicators = hazard === 'all' ? events.indicators : [hazard];
  $: eventTotal = filteredRows.reduce(
    (total, row) => total + activeIndicators.reduce((subtotal, indicator) => subtotal + (row.values[indicator] ?? 0), 0),
    0
  );

  $: impactPeriodRows = impact.district_rows.filter((row) => row.year === Number(period));
  $: filteredImpactRows = impactPeriodRows.filter((row) => region === 'all' || row.geography_id === region);
  $: deaths = sumImpact(['deaths']);
  $: missingPeople = sumImpact(['missing_people']);
  $: injuredOrSick = sumImpact(['injured_or_sick_people']);
  $: sufferingPeople = sumImpact(['suffering_people']);
  $: displacedPeople = sumImpact(['displaced_people']);
  $: damagedHouses = sumImpact(['houses_heavily_damaged', 'houses_moderately_damaged', 'houses_lightly_damaged']);
  $: heavilyDamagedHouses = sumImpact(['houses_heavily_damaged']);
  $: moderatelyDamagedHouses = sumImpact(['houses_moderately_damaged']);
  $: lightlyDamagedHouses = sumImpact(['houses_lightly_damaged']);
  $: floodedHouses = sumImpact(['houses_flooded']);
  $: affectedFacilities = sumImpact([
    'education_facilities_affected',
    'worship_facilities_affected',
    'health_facilities_affected',
    'office_facilities_affected',
    'bridges_affected'
  ]);

  const readiness = [
    {
      title: lang === 'id' ? 'Kejadian per kabupaten/kota' : 'Events by regency/city',
      state: 'ready',
      detail: lang === 'id' ? 'Observasi kanonik BNPB menjadi public artifact saat build.' : 'Canonical BNPB observations become a public artifact at build time.'
    },
    {
      title: lang === 'id' ? 'Korban dan masyarakat terdampak' : 'Casualties and affected population',
      state: 'ready',
      detail: lang === 'id' ? 'Tabel BPBD/Pusdalops 2024 sudah tervalidasi terhadap baris TOTAL sumber.' : 'The 2024 BPBD/Pusdalops table is validated against its published TOTAL row.'
    },
    {
      title: lang === 'id' ? 'Rumah dan fasilitas umum' : 'Housing and public facilities',
      state: 'ready',
      detail: lang === 'id' ? 'Kategori rumah dan fasilitas dipertahankan sesuai kolom sumber, tanpa zero-fill.' : 'Housing and facility categories retain the source columns without zero-filling.'
    },
    {
      title: lang === 'id' ? 'Batas 19 kabupaten/kota' : '19 regency/city boundaries',
      state: 'ready',
      detail: lang === 'id' ? 'Polygon BIG resmi sudah dipromosikan ke GeoJSON publik dan dipetakan ke geography_id.' : 'Official BIG polygons are promoted to public GeoJSON and mapped to geography_id.'
    },
    {
      title: lang === 'id' ? 'Kerugian ekonomi 2024' : '2024 economic losses',
      state: 'building',
      detail: lang === 'id' ? 'Belum ada angka 2024 yang lolos contract ini; data 2023 tidak dicampur ke kartu 2024.' : 'No 2024 value has passed this contract; 2023 loss data is not mixed into the 2024 card.'
    }
  ];

  function rowTotal(row: DisasterDistrictRow) {
    return activeIndicators.reduce((total, indicator) => total + (row.values[indicator] ?? 0), 0);
  }

  function sumImpact(indicators: string[]): number | undefined {
    if (filteredImpactRows.length === 0) return undefined;
    return filteredImpactRows.reduce(
      (total, row) => total + indicators.reduce((subtotal, indicator) => subtotal + (row.values[indicator] ?? 0), 0),
      0
    );
  }

  function impactRow(geographyId: string) {
    return impactPeriodRows.find((row) => row.geography_id === geographyId);
  }

  function impactRowSum(row: ImpactDistrictRow | undefined, indicators: string[]) {
    if (!row) return undefined;
    return indicators.reduce((total, indicator) => total + (row.values[indicator] ?? 0), 0);
  }

  function formatNumber(value: number | undefined) {
    return value === undefined ? '—' : value.toLocaleString(lang === 'id' ? 'id-ID' : 'en-US');
  }

  function selectedRegionName() {
    return region === 'all' ? '' : (districtOptions.find((row) => row.geography_id === region)?.name ?? region);
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
    <p class="hero-note">{lang === 'id' ? 'Kejadian berasal dari observasi kanonik BNPB. Dampak 2024 berasal dari tabel BPBD/Pusdalops Satu Data Sumbar yang sudah lolos validasi TOTAL. Kedua sumber tetap dipisahkan di provenance.' : 'Events come from canonical BNPB observations. 2024 impacts come from BPBD/Pusdalops West Sumatra Open Data tables that passed TOTAL validation. Both sources remain separate in provenance.'}</p>
  </section>

  <section class="section">
    <div class="toolbar">
      <select bind:value={period} aria-label={lang === 'id' ? 'Periode' : 'Period'}>
        {#each events.years as year}<option value={String(year)}>{year}</option>{/each}
      </select>
      <select bind:value={region} aria-label={lang === 'id' ? 'Wilayah' : 'Region'}>
        <option value="all">{lang === 'id' ? 'Semua kabupaten/kota' : 'All regencies/cities'}</option>
        {#each districtOptions as district}
          <option value={district.geography_id}>{district.name}</option>
        {/each}
      </select>
      <select bind:value={hazard} aria-label={lang === 'id' ? 'Jenis bencana' : 'Hazard type'}>
        <option value="all">{lang === 'id' ? 'Semua jenis tersedia' : 'All available hazard types'}</option>
        {#each events.indicators as indicator}
          <option value={indicator}>{eventLabel(indicator, lang)}</option>
        {/each}
      </select>
    </div>

    <div class="metric-grid" aria-label={lang === 'id' ? 'Metrik bencana dan dampak' : 'Disaster and impact metrics'}>
      <div class="metric">
        <span>{lang === 'id' ? 'Kejadian tercatat' : 'Recorded events'}</span>
        <strong>{eventTotal.toLocaleString(lang === 'id' ? 'id-ID' : 'en-US')}</strong>
        <small>{period}{region === 'all' ? '' : ` · ${selectedRegionName()}`}</small>
      </div>
      <div class="metric">
        <span>{lang === 'id' ? 'Meninggal' : 'Deaths'}</span>
        <strong>{formatNumber(deaths)}</strong>
        <small>{missingPeople === undefined ? (lang === 'id' ? 'impact belum tersedia untuk periode ini' : 'impact unavailable for this period') : `${formatNumber(missingPeople)} ${lang === 'id' ? 'hilang' : 'missing'} · ${formatNumber(injuredOrSick)} ${lang === 'id' ? 'luka/sakit' : 'injured/sick'}`}</small>
      </div>
      <div class="metric">
        <span>{lang === 'id' ? 'Mengungsi' : 'Displaced'}</span>
        <strong>{formatNumber(displacedPeople)}</strong>
        <small>{sufferingPeople === undefined ? (lang === 'id' ? 'impact belum tersedia untuk periode ini' : 'impact unavailable for this period') : `${formatNumber(sufferingPeople)} ${lang === 'id' ? 'menderita — dicatat terpisah' : 'suffering — kept separate'}`}</small>
      </div>
      <div class="metric">
        <span>{lang === 'id' ? 'Rumah rusak' : 'Damaged houses'}</span>
        <strong>{formatNumber(damagedHouses)}</strong>
        <small>{damagedHouses === undefined ? (lang === 'id' ? 'impact belum tersedia untuk periode ini' : 'impact unavailable for this period') : `RB ${formatNumber(heavilyDamagedHouses)} · RS ${formatNumber(moderatelyDamagedHouses)} · RR ${formatNumber(lightlyDamagedHouses)}`}</small>
      </div>
      <div class="metric">
        <span>{lang === 'id' ? 'Rumah terendam' : 'Flooded houses'}</span>
        <strong>{formatNumber(floodedHouses)}</strong>
        <small>{lang === 'id' ? 'tidak digabung ke rumah rusak' : 'not merged into damaged houses'}</small>
      </div>
      <div class="metric">
        <span>{lang === 'id' ? 'Fasilitas terdampak' : 'Affected facilities'}</span>
        <strong>{formatNumber(affectedFacilities)}</strong>
        <small>{lang === 'id' ? 'pendidikan, ibadah, kesehatan, kantor, jembatan' : 'education, worship, health, office, bridges'}</small>
      </div>
      <div class="metric">
        <span>{lang === 'id' ? 'Kerugian ekonomi' : 'Economic losses'}</span>
        <strong>—</strong>
        <small>{lang === 'id' ? 'belum ada sumber 2024 tervalidasi' : 'no validated 2024 source yet'}</small>
      </div>
    </div>
    <p class="hero-note" style="margin-top:14px">{events.interpretation[lang]} {impact.interpretation[lang]}</p>
  </section>

  <section class="section two-col">
    <div>
      <div class="section-head">
        <div><p class="eyebrow">BIG + MapLibre</p><h2>{t.mapTitle}</h2></div>
        <p>{lang === 'id' ? 'Warna menunjukkan jumlah kejadian BNPB sesuai filter jenis bencana. Klik wilayah untuk memakainya sebagai filter.' : 'Fill intensity shows BNPB event counts for the active hazard filter. Click a region to use it as the geography filter.'}</p>
      </div>
      <DisasterMap
        geography={data.geography}
        rows={periodRows}
        indicators={activeIndicators}
        selectedGeographyId={region}
        selectGeography={(geographyId) => (region = geographyId)}
        {lang}
      />
      <p class="meta" style="margin-top:10px">{summary.geography.organization} · {summary.geography.feature_count} {lang === 'id' ? 'kabupaten/kota' : 'regencies/cities'} · {summary.geography.anomaly_note}</p>
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
      <div><p class="eyebrow">{lang === 'id' ? 'Kejadian' : 'Events'}</p><h2>{lang === 'id' ? 'Kejadian per kabupaten/kota' : 'Events by regency/city'}</h2></div>
      <p>{lang === 'id' ? 'Tabel mengikuti filter periode, wilayah, dan jenis bencana. Nilai berasal dari seri BNPB.' : 'The table follows period, geography, and hazard filters. Values come from the BNPB series.'}</p>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>{lang === 'id' ? 'Kabupaten/kota' : 'Regency/city'}</th>
            {#each events.indicators as indicator}<th>{eventLabel(indicator, lang)}</th>{/each}
            <th>{lang === 'id' ? 'Total terfilter' : 'Filtered total'}</th>
          </tr>
        </thead>
        <tbody>
          {#each filteredRows as row}
            <tr>
              <td><strong>{row.name}</strong></td>
              {#each events.indicators as indicator}<td>{row.values[indicator] ?? '—'}</td>{/each}
              <td><strong>{rowTotal(row)}</strong></td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </section>

  <section class="section">
    <div class="section-head">
      <div><p class="eyebrow">{lang === 'id' ? 'Dampak 2024' : '2024 impact'}</p><h2>{lang === 'id' ? 'Korban, rumah, dan fasilitas' : 'People, housing, and facilities'}</h2></div>
      <p>{lang === 'id' ? 'Agregat “rumah rusak” hanya menjumlah RB + RS + RR. “Rumah terendam” tetap kolom terpisah. Menderita dan mengungsi juga tidak digabung.' : 'The “damaged houses” aggregate only sums heavy + moderate + light damage. Flooded houses remain separate. Suffering and displacement are also kept separate.'}</p>
    </div>
    {#if impactPeriodRows.length > 0}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>{lang === 'id' ? 'Kabupaten/kota' : 'Regency/city'}</th>
              <th>{impactLabel('deaths', lang)}</th>
              <th>{impactLabel('missing_people', lang)}</th>
              <th>{impactLabel('injured_or_sick_people', lang)}</th>
              <th>{impactLabel('displaced_people', lang)}</th>
              <th>{lang === 'id' ? 'Rumah rusak' : 'Damaged houses'}</th>
              <th>{impactLabel('houses_flooded', lang)}</th>
              <th>{lang === 'id' ? 'Fasilitas terdampak' : 'Affected facilities'}</th>
            </tr>
          </thead>
          <tbody>
            {#each filteredRows as eventRow}
              {@const row = impactRow(eventRow.geography_id)}
              <tr>
                <td><strong>{eventRow.name}</strong></td>
                <td>{row?.values.deaths ?? '—'}</td>
                <td>{row?.values.missing_people ?? '—'}</td>
                <td>{row?.values.injured_or_sick_people ?? '—'}</td>
                <td>{row?.values.displaced_people ?? '—'}</td>
                <td>{impactRowSum(row, ['houses_heavily_damaged', 'houses_moderately_damaged', 'houses_lightly_damaged']) ?? '—'}</td>
                <td>{row?.values.houses_flooded ?? '—'}</td>
                <td>{impactRowSum(row, ['education_facilities_affected', 'worship_facilities_affected', 'health_facilities_affected', 'office_facilities_affected', 'bridges_affected']) ?? '—'}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {:else}
      <div class="card"><p>{lang === 'id' ? 'Dampak tervalidasi belum tersedia untuk periode yang dipilih.' : 'Validated impact data is not available for the selected period.'}</p></div>
    {/if}
  </section>

  <section class="section">
    <div class="section-head">
      <div><p class="eyebrow">{t.proofTitle}</p><h2>{lang === 'id' ? 'Dari temuan kembali ke file sumber' : 'From finding back to source file'}</h2></div>
      <p>{lang === 'id' ? 'Public artifact menyimpan path dan checksum sumber. Setiap lapisan bisa ditelusuri ke artefak repository.' : 'The public artifact retains source paths and checksums. Each layer can be traced to a repository artifact.'}</p>
    </div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>{lang === 'id' ? 'Lapisan' : 'Layer'}</th><th>{lang === 'id' ? 'Status' : 'Status'}</th><th>{lang === 'id' ? 'Sumber' : 'Source'}</th><th>{lang === 'id' ? 'Bukti' : 'Evidence'}</th></tr></thead>
        <tbody>
          <tr><td>{lang === 'id' ? 'Kejadian bencana' : 'Disaster events'}</td><td>Materialized</td><td>{events.source.organization}</td><td><a href={repositoryUrl(events.source.path)}>{lang === 'id' ? 'Lihat data →' : 'View data →'}</a></td></tr>
          <tr><td>{lang === 'id' ? 'Dampak bencana 2024' : '2024 disaster impacts'}</td><td>Materialized</td><td>{impact.source.organization}</td><td><a href={repositoryUrl(impact.source.path)}>{lang === 'id' ? 'Lihat data →' : 'View data →'}</a></td></tr>
          <tr><td>{lang === 'id' ? 'Batas kabupaten/kota' : 'Regency/city boundaries'}</td><td>Materialized</td><td>{summary.geography.organization}</td><td><a href={repositoryUrl(summary.geography.path)}>{lang === 'id' ? 'Lihat GeoJSON →' : 'View GeoJSON →'}</a></td></tr>
          <tr><td>{lang === 'id' ? 'Curah hujan tahunan' : 'Annual rainfall'}</td><td>Materialized</td><td>CHIRPS v3</td><td><a href={repositoryUrl('data/processed/climate/rainfall/chirps-annual-rainfall-observations.csv')}>{lang === 'id' ? 'Lihat data →' : 'View data →'}</a></td></tr>
        </tbody>
      </table>
    </div>
    <p class="meta" style="margin-top:10px">BNPB SHA256: <code>{events.source.sha256}</code> · BPBD SHA256: <code>{impact.source.sha256}</code></p>
  </section>
</main>
