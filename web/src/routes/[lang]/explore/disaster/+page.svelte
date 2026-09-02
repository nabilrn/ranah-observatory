<script lang="ts">
  import { copy, type Locale } from '$lib/i18n';
  import { repositoryUrl } from '$lib/catalog';
  import DisasterMap from '$lib/components/DisasterMap.svelte';
  import RiskMitigationPanel from '$lib/components/RiskMitigationPanel.svelte';
  import MitigationPlanPanel from '$lib/components/MitigationPlanPanel.svelte';
  import {
    eventLabel,
    hazardLabel,
    impactLabel,
    type DisasterDistrictRow,
    type ImpactDistrictRow,
    type LossCoverageRow,
    type PublicDisasterSummary,
    type PublicDistrictBoundary
  } from '$lib/public-data';

  export let data: { lang: Locale; summary: PublicDisasterSummary; geography: PublicDistrictBoundary };
  const lang = data.lang;
  const t = copy[lang].disaster;
  const summary = data.summary;
  const events = summary.events;
  const impact2024 = summary.impact_2024;
  const impact2023 = summary.impact_2023;
  const context2024 = summary.context_2024;
  const months = Array.from({ length: 12 }, (_, index) => index + 1);
  const contextHazards = Object.keys(context2024.monthly_events.hazard_totals);
  const casualtyIndicators = ['deaths', 'missing_people', 'injured_or_sick_people', 'suffering_people', 'displaced_people'];

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

  $: impact2024PeriodRows = impact2024.district_rows.filter((row) => row.year === Number(period));
  $: filteredImpact2024Rows = impact2024PeriodRows.filter((row) => region === 'all' || row.geography_id === region);
  $: deaths = sumImpact2024(['deaths']);
  $: missingPeople = sumImpact2024(['missing_people']);
  $: injuredOrSick = sumImpact2024(['injured_or_sick_people']);
  $: sufferingPeople = sumImpact2024(['suffering_people']);
  $: displacedPeople = sumImpact2024(['displaced_people']);
  $: damagedHouses = sumImpact2024(['houses_heavily_damaged', 'houses_moderately_damaged', 'houses_lightly_damaged']);
  $: heavilyDamagedHouses = sumImpact2024(['houses_heavily_damaged']);
  $: moderatelyDamagedHouses = sumImpact2024(['houses_moderately_damaged']);
  $: lightlyDamagedHouses = sumImpact2024(['houses_lightly_damaged']);
  $: floodedHouses = sumImpact2024(['houses_flooded']);
  $: affectedFacilities = sumImpact2024([
    'education_facilities_affected',
    'worship_facilities_affected',
    'health_facilities_affected',
    'office_facilities_affected',
    'bridges_affected'
  ]);

  $: historicalRows = impact2023.district_rows.filter((row) => region === 'all' || row.geography_id === region);
  $: historicalCoverage = impact2023.loss_coverage.filter((row) => region === 'all' || row.geography_id === region);
  $: historicalEvents = sumHistorical(['disaster_events_reported']);
  $: historicalDeaths = sumHistorical(['deaths']);
  $: historicalInjured = sumHistorical(['injured_or_sick_people']);
  $: historicalDisplaced = sumHistorical(['displaced_people']);
  $: historicalDamagedHouses = sumHistorical(['houses_heavily_damaged', 'houses_moderately_damaged', 'houses_lightly_damaged']);
  $: historicalLoss = selectedHistoricalLoss();
  $: historicalLossCoverageText = region === 'all'
    ? `${impact2023.economic_loss.numeric_district_count}/${impact2023.economic_loss.district_count} ${lang === 'id' ? 'wilayah punya angka' : 'regions have numeric values'}`
    : historicalCoverage[0]?.loss_value_status === 'reported_numeric'
      ? (lang === 'id' ? 'angka tersedia pada sumber' : 'numeric value reported by source')
      : (lang === 'id' ? 'kosong atau tanda “-” pada sumber' : 'blank or “-” in source');

  const readiness = [
    {
      title: lang === 'id' ? 'Kejadian per kabupaten/kota' : 'Events by regency/city',
      state: 'ready',
      detail: lang === 'id' ? 'Observasi kanonik BNPB 2024 tersedia untuk 19 kabupaten/kota.' : 'Canonical BNPB 2024 observations cover all 19 regencies/cities.'
    },
    {
      title: lang === 'id' ? 'Dampak BPBD 2023–2024' : 'BPBD impacts 2023–2024',
      state: 'ready',
      detail: lang === 'id' ? 'Dampak 2023 dan 2024 sudah materialized dengan validasi total dan provenance terpisah.' : '2023 and 2024 impacts are materialized with total validation and separate provenance.'
    },
    {
      title: lang === 'id' ? 'Kerugian ekonomi 2023' : '2023 economic losses',
      state: 'ready',
      detail: lang === 'id' ? 'Rp45,287 miliar adalah jumlah nilai numerik yang tersedia pada 12/19 wilayah; tujuh wilayah tetap missing.' : 'Rp45.287 billion is the sum of numeric values available for 12/19 regions; seven regions remain missing.'
    },
    {
      title: lang === 'id' ? 'Timeline bencana BPBD 2024' : 'BPBD 2024 disaster timeline',
      state: 'ready',
      detail: lang === 'id' ? '1.175 kejadian bulanan tersedia menurut tujuh jenis bencana.' : '1,175 monthly events are available across seven hazard types.'
    },
    {
      title: lang === 'id' ? 'Inventaris sirine tsunami' : 'Tsunami siren inventory',
      state: 'ready',
      detail: lang === 'id' ? '46 sirine tercatat di enam wilayah; status kosong dipertahankan sebagai tidak diketahui.' : '46 sirens are listed across six regions; blank statuses remain unknown.'
    },
    {
      title: lang === 'id' ? 'Kerugian ekonomi 2024' : '2024 economic losses',
      state: 'building',
      detail: lang === 'id' ? 'Belum ada nilai 2024 yang lolos contract; angka 2023 tidak dipindahkan ke 2024.' : 'No 2024 value has passed the contract; 2023 figures are not carried into 2024.'
    }
  ];

  function rowTotal(row: DisasterDistrictRow) {
    return activeIndicators.reduce((total, indicator) => total + (row.values[indicator] ?? 0), 0);
  }

  function sumImpact2024(indicators: string[]): number | undefined {
    if (filteredImpact2024Rows.length === 0) return undefined;
    return filteredImpact2024Rows.reduce(
      (total, row) => total + indicators.reduce((subtotal, indicator) => subtotal + (row.values[indicator] ?? 0), 0),
      0
    );
  }

  function sumHistorical(indicators: string[]): number | undefined {
    if (historicalRows.length === 0) return undefined;
    return historicalRows.reduce(
      (total, row) => total + indicators.reduce((subtotal, indicator) => subtotal + (row.values[indicator] ?? 0), 0),
      0
    );
  }

  function selectedHistoricalLoss(): number | undefined {
    if (region === 'all') return impact2023.economic_loss.reported_total_idr;
    const row = impact2023.loss_coverage.find((item) => item.geography_id === region);
    return row?.economic_loss_estimate_idr ?? undefined;
  }

  function impactRow2024(geographyId: string) {
    return impact2024PeriodRows.find((row) => row.geography_id === geographyId);
  }

  function historicalImpactRow(geographyId: string) {
    return impact2023.district_rows.find((row) => row.geography_id === geographyId);
  }

  function historicalLossRow(geographyId: string): LossCoverageRow | undefined {
    return impact2023.loss_coverage.find((row) => row.geography_id === geographyId);
  }

  function impactRowSum(row: ImpactDistrictRow | undefined, indicators: string[]) {
    if (!row) return undefined;
    return indicators.reduce((total, indicator) => total + (row.values[indicator] ?? 0), 0);
  }

  function monthlyValue(month: number, hazardId: string) {
    return context2024.monthly_events.rows.find((row) => row.month === month && row.hazard_id === hazardId)?.value;
  }

  function monthlyReportedTotal(month: number) {
    return context2024.monthly_events.rows
      .filter((row) => row.month === month && row.value !== null)
      .reduce((total, row) => total + (row.value ?? 0), 0);
  }

  function casualtyValue(hazardId: string, indicator: string) {
    return context2024.casualties_by_hazard.rows.find(
      (row) => row.hazard_id === hazardId && row.indicator_id === indicator
    )?.value;
  }

  function sirenCount(name: string, status?: 'active' | 'inactive' | 'unknown') {
    return context2024.tsunami_sirens.rows.filter(
      (row) => row.name === name && (status === undefined || row.status === status)
    ).length;
  }

  function formatNumber(value: number | undefined) {
    return value === undefined ? '—' : value.toLocaleString(lang === 'id' ? 'id-ID' : 'en-US');
  }

  function formatRupiah(value: number | undefined) {
    if (value === undefined) return '—';
    return new Intl.NumberFormat(lang === 'id' ? 'id-ID' : 'en-US', {
      style: 'currency',
      currency: 'IDR',
      maximumFractionDigits: 0
    }).format(value);
  }

  function monthLabel(month: number) {
    if (lang === 'id') {
      return context2024.monthly_events.rows.find((row) => row.month === month)?.month_name_source ?? String(month);
    }
    return ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'][month - 1];
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
    <p class="hero-note">{lang === 'id' ? 'Peta kejadian memakai BNPB 2024. Dampak, timeline bulanan, dan inventaris mitigasi memakai BPBD/Pusdalops. Seri resmi yang berbeda tidak digabung menjadi satu angka.' : 'The event map uses BNPB 2024. Impacts, monthly timelines, and mitigation inventory use BPBD/Pusdalops. Different official series are not merged into one number.'}</p>
  </section>

  <section class="section">
    <div class="toolbar">
      <select bind:value={period} aria-label={lang === 'id' ? 'Periode peta BNPB' : 'BNPB map period'}>
        {#each events.years as year}<option value={String(year)}>{year}</option>{/each}
      </select>
      <select bind:value={region} aria-label={lang === 'id' ? 'Wilayah' : 'Region'}>
        <option value="all">{lang === 'id' ? 'Semua kabupaten/kota' : 'All regencies/cities'}</option>
        {#each districtOptions as district}
          <option value={district.geography_id}>{district.name}</option>
        {/each}
      </select>
      <select bind:value={hazard} aria-label={lang === 'id' ? 'Jenis bencana BNPB' : 'BNPB hazard type'}>
        <option value="all">{lang === 'id' ? 'Semua jenis tersedia' : 'All available hazard types'}</option>
        {#each events.indicators as indicator}
          <option value={indicator}>{eventLabel(indicator, lang)}</option>
        {/each}
      </select>
    </div>

    <div class="metric-grid" aria-label={lang === 'id' ? 'Metrik bencana dan dampak' : 'Disaster and impact metrics'}>
      <div class="metric">
        <span>{lang === 'id' ? 'Kejadian BNPB tercatat' : 'Recorded BNPB events'}</span>
        <strong>{eventTotal.toLocaleString(lang === 'id' ? 'id-ID' : 'en-US')}</strong>
        <small>{period}{region === 'all' ? '' : ` · ${selectedRegionName()}`}</small>
      </div>
      <div class="metric">
        <span>{lang === 'id' ? 'Meninggal 2024' : 'Deaths 2024'}</span>
        <strong>{formatNumber(deaths)}</strong>
        <small>{missingPeople === undefined ? '—' : `${formatNumber(missingPeople)} ${lang === 'id' ? 'hilang' : 'missing'} · ${formatNumber(injuredOrSick)} ${lang === 'id' ? 'luka/sakit' : 'injured/sick'}`}</small>
      </div>
      <div class="metric">
        <span>{lang === 'id' ? 'Mengungsi 2024' : 'Displaced 2024'}</span>
        <strong>{formatNumber(displacedPeople)}</strong>
        <small>{sufferingPeople === undefined ? '—' : `${formatNumber(sufferingPeople)} ${lang === 'id' ? 'menderita — terpisah' : 'suffering — separate'}`}</small>
      </div>
      <div class="metric">
        <span>{lang === 'id' ? 'Rumah rusak 2024' : 'Damaged houses 2024'}</span>
        <strong>{formatNumber(damagedHouses)}</strong>
        <small>{damagedHouses === undefined ? '—' : `RB ${formatNumber(heavilyDamagedHouses)} · RS ${formatNumber(moderatelyDamagedHouses)} · RR ${formatNumber(lightlyDamagedHouses)}`}</small>
      </div>
      <div class="metric">
        <span>{lang === 'id' ? 'Rumah terendam 2024' : 'Flooded houses 2024'}</span>
        <strong>{formatNumber(floodedHouses)}</strong>
        <small>{lang === 'id' ? 'tidak digabung ke rumah rusak' : 'not merged into damaged houses'}</small>
      </div>
      <div class="metric">
        <span>{lang === 'id' ? 'Fasilitas terdampak 2024' : 'Affected facilities 2024'}</span>
        <strong>{formatNumber(affectedFacilities)}</strong>
        <small>{lang === 'id' ? 'pendidikan, ibadah, kesehatan, kantor, jembatan' : 'education, worship, health, office, bridges'}</small>
      </div>
      <div class="metric">
        <span>{lang === 'id' ? 'Kerugian ekonomi 2024' : 'Economic losses 2024'}</span>
        <strong>—</strong>
        <small>{lang === 'id' ? 'belum ada sumber tervalidasi' : 'no validated source yet'}</small>
      </div>
      <div class="metric">
        <span>{lang === 'id' ? 'Kerugian dilaporkan 2023' : 'Reported losses 2023'}</span>
        <strong>{formatRupiah(historicalLoss)}</strong>
        <small>{historicalLossCoverageText}</small>
      </div>
    </div>
    <p class="hero-note" style="margin-top:14px">{events.interpretation[lang]} {impact2024.interpretation[lang]}</p>
  </section>

  <section class="section two-col">
    <div>
      <div class="section-head">
        <div><p class="eyebrow">BIG + MapLibre</p><h2>{t.mapTitle}</h2></div>
        <p>{lang === 'id' ? 'Warna menunjukkan jumlah kejadian BNPB sesuai filter. Klik wilayah untuk memakainya sebagai filter di seluruh tabel kabupaten/kota.' : 'Fill intensity shows BNPB event counts for the active filter. Click a region to use it across district-level tables.'}</p>
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

  <RiskMitigationPanel riskMitigation={summary.risk_mitigation_2024} bind:region {lang} />

  <MitigationPlanPanel plan={summary.mitigation_plan_2026} {lang} />

  <section class="section">
    <div class="section-head">
      <div><p class="eyebrow">{lang === 'id' ? 'Kejadian BNPB 2024' : 'BNPB events 2024'}</p><h2>{lang === 'id' ? 'Kejadian per kabupaten/kota' : 'Events by regency/city'}</h2></div>
      <p>{lang === 'id' ? 'Tabel mengikuti filter wilayah dan jenis bencana. Ini seri BNPB, bukan timeline BPBD di bawah.' : 'The table follows geography and hazard filters. This is the BNPB series, not the BPBD timeline below.'}</p>
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
      <div><p class="eyebrow">{lang === 'id' ? 'Dampak BPBD 2024' : 'BPBD impact 2024'}</p><h2>{lang === 'id' ? 'Korban, rumah, dan fasilitas' : 'People, housing, and facilities'}</h2></div>
      <p>{lang === 'id' ? 'Rumah rusak hanya menjumlah RB + RS + RR. Rumah terendam, menderita, dan mengungsi tetap konsep terpisah.' : 'Damaged houses only sum heavy + moderate + light damage. Flooded houses, suffering, and displacement remain separate concepts.'}</p>
    </div>
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
            {@const row = impactRow2024(eventRow.geography_id)}
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
  </section>

  <section class="section">
    <div class="section-head">
      <div><p class="eyebrow">{lang === 'id' ? 'Dampak & kerugian BPBD 2023' : 'BPBD impact & losses 2023'}</p><h2>{lang === 'id' ? 'Satu tahun sebelumnya, tetap sebagai seri terpisah' : 'The prior year, retained as a separate series'}</h2></div>
      <p>{impact2023.interpretation[lang]}</p>
    </div>
    <div class="metric-grid" style="margin-bottom:16px">
      <div class="metric"><span>{lang === 'id' ? 'Kejadian dilaporkan' : 'Reported events'}</span><strong>{formatNumber(historicalEvents)}</strong><small>BPBD/Pusdalops · 2023</small></div>
      <div class="metric"><span>{lang === 'id' ? 'Meninggal' : 'Deaths'}</span><strong>{formatNumber(historicalDeaths)}</strong><small>2023</small></div>
      <div class="metric"><span>{lang === 'id' ? 'Luka/sakit' : 'Injured/sick'}</span><strong>{formatNumber(historicalInjured)}</strong><small>2023</small></div>
      <div class="metric"><span>{lang === 'id' ? 'Mengungsi' : 'Displaced'}</span><strong>{formatNumber(historicalDisplaced)}</strong><small>2023</small></div>
      <div class="metric"><span>{lang === 'id' ? 'Rumah rusak' : 'Damaged houses'}</span><strong>{formatNumber(historicalDamagedHouses)}</strong><small>RB + RS + RR</small></div>
      <div class="metric"><span>{lang === 'id' ? 'Kerugian dilaporkan' : 'Reported losses'}</span><strong>{formatRupiah(historicalLoss)}</strong><small>{historicalLossCoverageText}</small></div>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>{lang === 'id' ? 'Kabupaten/kota' : 'Regency/city'}</th>
            <th>{lang === 'id' ? 'Kejadian' : 'Events'}</th>
            <th>{impactLabel('deaths', lang)}</th>
            <th>{impactLabel('injured_or_sick_people', lang)}</th>
            <th>{impactLabel('displaced_people', lang)}</th>
            <th>{lang === 'id' ? 'Rumah rusak' : 'Damaged houses'}</th>
            <th>{lang === 'id' ? 'Kerugian' : 'Losses'}</th>
          </tr>
        </thead>
        <tbody>
          {#each historicalCoverage as coverage}
            {@const row = historicalImpactRow(coverage.geography_id)}
            {@const loss = historicalLossRow(coverage.geography_id)}
            <tr>
              <td><strong>{coverage.name}</strong></td>
              <td>{row?.values.disaster_events_reported ?? '—'}</td>
              <td>{row?.values.deaths ?? '—'}</td>
              <td>{row?.values.injured_or_sick_people ?? '—'}</td>
              <td>{row?.values.displaced_people ?? '—'}</td>
              <td>{impactRowSum(row, ['houses_heavily_damaged', 'houses_moderately_damaged', 'houses_lightly_damaged']) ?? '—'}</td>
              <td>{loss?.economic_loss_estimate_idr === null || loss === undefined ? '—' : formatRupiah(loss.economic_loss_estimate_idr)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </section>

  <section class="section">
    <div class="section-head">
      <div><p class="eyebrow">BPBD/Pusdalops · 2024</p><h2>{lang === 'id' ? 'Kapan bencana tercatat sepanjang tahun?' : 'When were disasters recorded through the year?'}</h2></div>
      <p>{context2024.monthly_events.interpretation[lang]}</p>
    </div>
    <div class="grid" style="margin-bottom:16px">
      {#each contextHazards as hazardId}
        <article class="card" style="min-height:auto">
          <p class="eyebrow">{hazardLabel(hazardId, lang)}</p>
          <h3 style="font-size:28px;margin-bottom:6px">{formatNumber(context2024.monthly_events.hazard_totals[hazardId])}</h3>
          <p class="meta">{lang === 'id' ? 'kejadian BPBD/Pusdalops 2024' : 'BPBD/Pusdalops events in 2024'}</p>
        </article>
      {/each}
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>{lang === 'id' ? 'Bulan' : 'Month'}</th>
            {#each contextHazards as hazardId}<th>{hazardLabel(hazardId, lang)}</th>{/each}
            <th>{lang === 'id' ? 'Total dilaporkan' : 'Reported total'}</th>
          </tr>
        </thead>
        <tbody>
          {#each months as month}
            <tr>
              <td><strong>{monthLabel(month)}</strong></td>
              {#each contextHazards as hazardId}
                {@const value = monthlyValue(month, hazardId)}
                <td>{value === null || value === undefined ? '—' : value}</td>
              {/each}
              <td><strong>{monthlyReportedTotal(month)}</strong></td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    <div class="card" style="min-height:auto;margin-top:14px">
      <p class="eyebrow">{lang === 'id' ? 'Perbedaan antar-sumber resmi' : 'Difference across official sources'}</p>
      <h3>{lang === 'id' ? 'BPBD/Pusdalops dan BNPB tidak mencatat jumlah yang sama' : 'BPBD/Pusdalops and BNPB do not record the same totals'}</h3>
      <p>
        {#if context2024.monthly_events.event_source_comparison.flood}
          {lang === 'id' ? 'Banjir' : 'Flood'}: BPBD/Pusdalops <strong>{context2024.monthly_events.event_source_comparison.flood.bpbd_pusdalops_total}</strong> vs BNPB <strong>{context2024.monthly_events.event_source_comparison.flood.bnpb_canonical_total}</strong>.
        {/if}
        {#if context2024.monthly_events.event_source_comparison.landslide}
          {lang === 'id' ? 'Longsor' : 'Landslide'}: BPBD/Pusdalops <strong>{context2024.monthly_events.event_source_comparison.landslide.bpbd_pusdalops_total}</strong> vs BNPB <strong>{context2024.monthly_events.event_source_comparison.landslide.bnpb_canonical_total}</strong>.
        {/if}
      </p>
      <p class="meta">{lang === 'id' ? 'Keduanya dipertahankan sebagai seri berbeda karena sistem pelaporan/klasifikasi dapat berbeda. Angka tidak dijumlahkan dan tidak dipilih salah satu secara diam-diam.' : 'Both are retained as separate series because recording/classification systems can differ. The counts are neither added nor silently replaced by one another.'}</p>
    </div>
  </section>

  <section class="section">
    <div class="section-head">
      <div><p class="eyebrow">BPBD/Pusdalops · 2024</p><h2>{lang === 'id' ? 'Korban menurut jenis bencana' : 'Casualties by hazard type'}</h2></div>
      <p>{lang === 'id' ? 'Total tabel ini sudah direkonsiliasi dengan dampak BPBD per kabupaten/kota 2024.' : 'These totals reconcile to the validated 2024 BPBD district-impact data.'}</p>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>{lang === 'id' ? 'Jenis bencana' : 'Hazard'}</th>
            {#each casualtyIndicators as indicator}<th>{impactLabel(indicator, lang)}</th>{/each}
          </tr>
        </thead>
        <tbody>
          {#each contextHazards as hazardId}
            <tr>
              <td><strong>{hazardLabel(hazardId, lang)}</strong></td>
              {#each casualtyIndicators as indicator}<td>{casualtyValue(hazardId, indicator) ?? '—'}</td>{/each}
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </section>

  <section class="section">
    <div class="section-head">
      <div><p class="eyebrow">{lang === 'id' ? 'Kapasitas mitigasi' : 'Mitigation capacity'}</p><h2>{lang === 'id' ? 'Inventaris sirine tsunami 2024' : '2024 tsunami siren inventory'}</h2></div>
      <p>{context2024.tsunami_sirens.interpretation[lang]}</p>
    </div>
    <div class="metric-grid" style="margin-bottom:16px">
      <div class="metric"><span>{lang === 'id' ? 'Sirine tercatat' : 'Listed sirens'}</span><strong>{context2024.tsunami_sirens.count}</strong><small>{context2024.tsunami_sirens.geography_count} {lang === 'id' ? 'wilayah' : 'regions'}</small></div>
      <div class="metric"><span>{lang === 'id' ? 'Aktif' : 'Active'}</span><strong>{context2024.tsunami_sirens.status_counts.active}</strong><small>{lang === 'id' ? 'status sumber' : 'source status'}</small></div>
      <div class="metric"><span>{lang === 'id' ? 'Tidak aktif' : 'Inactive'}</span><strong>{context2024.tsunami_sirens.status_counts.inactive}</strong><small>{lang === 'id' ? 'status sumber' : 'source status'}</small></div>
      <div class="metric"><span>{lang === 'id' ? 'Status tidak diketahui' : 'Unknown status'}</span><strong>{context2024.tsunami_sirens.status_counts.unknown}</strong><small>{lang === 'id' ? 'sel status kosong pada sumber' : 'blank status cell in source'}</small></div>
    </div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>{lang === 'id' ? 'Wilayah' : 'Region'}</th><th>Total</th><th>{lang === 'id' ? 'Aktif' : 'Active'}</th><th>{lang === 'id' ? 'Tidak aktif' : 'Inactive'}</th><th>{lang === 'id' ? 'Tidak diketahui' : 'Unknown'}</th></tr></thead>
        <tbody>
          {#each [...new Set(context2024.tsunami_sirens.rows.map((row) => row.name))].sort() as name}
            <tr><td><strong>{name}</strong></td><td>{sirenCount(name)}</td><td>{sirenCount(name, 'active')}</td><td>{sirenCount(name, 'inactive')}</td><td>{sirenCount(name, 'unknown')}</td></tr>
          {/each}
        </tbody>
      </table>
    </div>
  </section>

  <section class="section">
    <div class="section-head">
      <div><p class="eyebrow">{t.proofTitle}</p><h2>{lang === 'id' ? 'Dari temuan kembali ke file sumber' : 'From finding back to source file'}</h2></div>
      <p>{lang === 'id' ? 'Setiap angka di atas ditarik dari artefak materialized yang punya checksum dan provenance.' : 'Every figure above is drawn from materialized artifacts with checksums and provenance.'}</p>
    </div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>{lang === 'id' ? 'Lapisan' : 'Layer'}</th><th>Status</th><th>{lang === 'id' ? 'Sumber' : 'Source'}</th><th>{lang === 'id' ? 'Bukti' : 'Evidence'}</th></tr></thead>
        <tbody>
          <tr><td>{lang === 'id' ? 'Kejadian BNPB 2024' : 'BNPB events 2024'}</td><td>Materialized</td><td>{events.source.organization}</td><td><a href={repositoryUrl(events.source.path)}>{lang === 'id' ? 'Lihat data →' : 'View data →'}</a></td></tr>
          <tr><td>{lang === 'id' ? 'Dampak BPBD 2024' : 'BPBD impact 2024'}</td><td>Materialized</td><td>{impact2024.source.organization}</td><td><a href={repositoryUrl(impact2024.source.path)}>{lang === 'id' ? 'Lihat data →' : 'View data →'}</a></td></tr>
          <tr><td>{lang === 'id' ? 'Dampak & kerugian BPBD 2023' : 'BPBD impact & losses 2023'}</td><td>Materialized</td><td>{impact2023.source.organization}</td><td><a href={repositoryUrl(impact2023.source.path)}>{lang === 'id' ? 'Lihat data →' : 'View data →'}</a></td></tr>
          <tr><td>{lang === 'id' ? 'Cakupan kerugian 2023' : '2023 loss coverage'}</td><td>Materialized</td><td>BPBD/Pusdalops</td><td><a href={repositoryUrl('data/processed/bpbd/disaster_impact_2023/bpbd-disaster-loss-2023-coverage.csv')}>{lang === 'id' ? 'Lihat coverage →' : 'View coverage →'}</a></td></tr>
          <tr><td>{lang === 'id' ? 'Kejadian bulanan BPBD 2024' : 'BPBD monthly events 2024'}</td><td>Materialized</td><td>{context2024.source.organization}</td><td><a href={repositoryUrl(context2024.monthly_events.path)}>{lang === 'id' ? 'Lihat data →' : 'View data →'}</a></td></tr>
          <tr><td>{lang === 'id' ? 'Korban per jenis bencana 2024' : 'Casualties by hazard 2024'}</td><td>Materialized</td><td>{context2024.source.organization}</td><td><a href={repositoryUrl(context2024.casualties_by_hazard.path)}>{lang === 'id' ? 'Lihat data →' : 'View data →'}</a></td></tr>
          <tr><td>{lang === 'id' ? 'Sirine tsunami 2024' : 'Tsunami sirens 2024'}</td><td>Materialized</td><td>{context2024.source.organization}</td><td><a href={repositoryUrl(context2024.tsunami_sirens.path)}>{lang === 'id' ? 'Lihat data →' : 'View data →'}</a></td></tr>
          <tr><td>{lang === 'id' ? 'Batas kabupaten/kota' : 'Regency/city boundaries'}</td><td>Materialized</td><td>{summary.geography.organization}</td><td><a href={repositoryUrl(summary.geography.path)}>{lang === 'id' ? 'Lihat GeoJSON →' : 'View GeoJSON →'}</a></td></tr>
          <tr><td>{lang === 'id' ? 'Curah hujan tahunan' : 'Annual rainfall'}</td><td>Materialized</td><td>CHIRPS v3</td><td><a href={repositoryUrl('data/processed/climate/rainfall/chirps-annual-rainfall-observations.csv')}>{lang === 'id' ? 'Lihat data →' : 'View data →'}</a></td></tr>
        </tbody>
      </table>
    </div>
    <p class="meta" style="margin-top:10px">BNPB SHA256: <code>{events.source.sha256}</code> · BPBD 2024 SHA256: <code>{impact2024.source.sha256}</code> · BPBD context SHA256: <code>{context2024.source.materialization_sha256}</code></p>
  </section>
</main>
