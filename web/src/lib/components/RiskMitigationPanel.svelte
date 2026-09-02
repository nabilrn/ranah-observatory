<script lang="ts">
  import type { Locale } from '$lib/i18n';
  import type { PublicDisasterSummary } from '$lib/public-data';

  export let riskMitigation: PublicDisasterSummary['risk_mitigation_2024'];
  export let region = 'all';
  export let lang: Locale;

  const riskHazards = riskMitigation.risk.hazard_ids;
  let riskHazard = riskHazards[0] ?? '';

  $: districtOptions = Array.from(
    new Map(
      riskMitigation.risk.rows.map((row) => [row.geography_id, { geography_id: row.geography_id, name: row.geography_name }])
    ).values()
  ).sort((a, b) => a.name.localeCompare(b.name, lang === 'id' ? 'id-ID' : 'en-US'));
  $: selectedHazardRows = riskMitigation.risk.rows.filter((row) => row.irbi_hazard_id === riskHazard);
  $: selectedRisk = region === 'all'
    ? undefined
    : selectedHazardRows.find((row) => row.geography_id === region);
  $: selectedKrbHazard = selectedHazardRows[0]?.krb_hazard_id ?? riskHazard;
  $: actions = riskMitigation.recommendations.rows.filter((row) => row.krb_hazard_id === selectedKrbHazard);
  $: classCounts = selectedHazardRows.reduce<Record<string, number>>((counts, row) => {
    counts[row.risk_class] = (counts[row.risk_class] ?? 0) + 1;
    return counts;
  }, {});

  function riskLabel(hazardId: string) {
    const row = riskMitigation.risk.rows.find((item) => item.irbi_hazard_id === hazardId);
    return row?.irbi_source_hazard_label ?? hazardId.replaceAll('_', ' ');
  }

  function formatScore(value: number) {
    return new Intl.NumberFormat(lang === 'id' ? 'id-ID' : 'en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value);
  }

  function classLabel(value: string) {
    const labels: Record<string, { id: string; en: string }> = {
      rendah: { id: 'Rendah', en: 'Low' },
      sedang: { id: 'Sedang', en: 'Medium' },
      tinggi: { id: 'Tinggi', en: 'High' }
    };
    return labels[value]?.[lang] ?? value;
  }
</script>

<section class="section risk-panel">
  <div class="section-head">
    <div>
      <p class="eyebrow">BNPB · IRBI 2024 + KRB 2022–2026</p>
      <h2>{lang === 'id' ? 'Risiko dan langkah pengurangan risiko' : 'Risk and risk-reduction actions'}</h2>
    </div>
    <p>{lang === 'id'
      ? 'Pilih wilayah dan jenis ancaman. Skor risiko berasal dari IRBI 2024; langkah mitigasi berasal dari KRB Sumatera Barat 2022–2026.'
      : 'Choose a region and hazard. Risk scores come from IRBI 2024; mitigation actions come from the West Sumatra 2022–2026 KRB.'}</p>
  </div>

  <div class="toolbar">
    <select bind:value={region} aria-label={lang === 'id' ? 'Wilayah risiko' : 'Risk region'}>
      <option value="all">{lang === 'id' ? 'Semua kabupaten/kota' : 'All regencies/cities'}</option>
      {#each districtOptions as district}
        <option value={district.geography_id}>{district.name}</option>
      {/each}
    </select>
    <select bind:value={riskHazard} aria-label={lang === 'id' ? 'Jenis ancaman IRBI' : 'IRBI hazard'}>
      {#each riskHazards as hazardId}
        <option value={hazardId}>{riskLabel(hazardId)}</option>
      {/each}
    </select>
  </div>

  <div class="metric-grid risk-metrics">
    {#if region === 'all'}
      <div class="metric">
        <span>{lang === 'id' ? 'Wilayah dengan baris IRBI' : 'Regions with IRBI rows'}</span>
        <strong>{selectedHazardRows.length}</strong>
        <small>{lang === 'id' ? 'kombinasi yang tidak ada di sumber tidak dianggap nol' : 'source-absent combinations are not treated as zero'}</small>
      </div>
      <div class="metric">
        <span>{lang === 'id' ? 'Kelas risiko pada baris tersedia' : 'Risk classes in available rows'}</span>
        <strong>{Object.entries(classCounts).map(([key, value]) => `${classLabel(key)} ${value}`).join(' · ') || '—'}</strong>
        <small>IRBI 2024</small>
      </div>
    {:else if selectedRisk}
      <div class="metric">
        <span>{lang === 'id' ? 'Skor risiko IRBI' : 'IRBI risk score'}</span>
        <strong>{formatScore(selectedRisk.risk_score)}</strong>
        <small>{selectedRisk.geography_name} · {riskLabel(riskHazard)} · 2024</small>
      </div>
      <div class="metric">
        <span>{lang === 'id' ? 'Kelas risiko' : 'Risk class'}</span>
        <strong>{classLabel(selectedRisk.risk_class)}</strong>
        <small>{lang === 'id' ? 'indeks risiko, bukan peluang kejadian' : 'risk index, not event probability'}</small>
      </div>
    {:else}
      <div class="metric missing-risk">
        <span>{lang === 'id' ? 'Baris IRBI 2024' : 'IRBI 2024 row'}</span>
        <strong>—</strong>
        <small>{lang === 'id'
          ? 'Kombinasi wilayah–ancaman ini tidak muncul pada tabel sumber. Ini bukan berarti risikonya nol.'
          : 'This district–hazard combination is absent from the source table. This does not mean zero risk.'}</small>
      </div>
    {/if}
    <div class="metric">
      <span>{lang === 'id' ? 'Rekomendasi resmi tersedia' : 'Official recommendations available'}</span>
      <strong>{actions.length}</strong>
      <small>KRB Sumatera Barat 2022–2026</small>
    </div>
  </div>

  <p class="hero-note risk-note">{riskMitigation.interpretation[lang]}</p>

  <div class="risk-layout">
    <div>
      <div class="section-head compact-head">
        <div><p class="eyebrow">IRBI 2024</p><h3>{lang === 'id' ? 'Skor wilayah yang tersedia' : 'Available district scores'}</h3></div>
        <p>{selectedHazardRows.length}/{riskMitigation.risk.geography_union_count} {lang === 'id' ? 'wilayah memiliki baris untuk ancaman ini.' : 'regions have a row for this hazard.'}</p>
      </div>
      <div class="table-wrap compact-table">
        <table>
          <thead>
            <tr>
              <th>{lang === 'id' ? 'Kabupaten/kota' : 'Regency/city'}</th>
              <th>{lang === 'id' ? 'Skor' : 'Score'}</th>
              <th>{lang === 'id' ? 'Kelas' : 'Class'}</th>
            </tr>
          </thead>
          <tbody>
            {#each selectedHazardRows as row}
              <tr class:selected-row={region === row.geography_id}>
                <td><strong>{row.geography_name}</strong></td>
                <td>{formatScore(row.risk_score)}</td>
                <td>{classLabel(row.risk_class)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>

    <div>
      <div class="section-head compact-head">
        <div><p class="eyebrow">KRB 2022–2026</p><h3>{lang === 'id' ? 'Langkah yang direkomendasikan' : 'Recommended actions'}</h3></div>
        <p>{lang === 'id' ? 'Urutan mengikuti dokumen sumber, bukan peringkat efektivitas.' : 'Order follows the source document and is not an effectiveness ranking.'}</p>
      </div>
      <div class="action-list">
        {#each actions as action}
          <article class="card action-card">
            <p class="eyebrow">{lang === 'id' ? `Rekomendasi ${action.action_order}` : `Recommendation ${action.action_order}`}</p>
            <p>{action.action_text_source_native}</p>
            <p class="meta">PDF {action.start_pdf_page}{action.end_pdf_page === action.start_pdf_page ? '' : `–${action.end_pdf_page}`}</p>
          </article>
        {/each}
      </div>
    </div>
  </div>
</section>

<style>
  .risk-panel {
    scroll-margin-top: 72px;
  }

  .risk-metrics {
    margin-top: 16px;
  }

  .risk-note {
    margin: 14px 0 0;
  }

  .risk-layout {
    display: grid;
    grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
    gap: 18px;
    margin-top: 22px;
    align-items: start;
  }

  .compact-head {
    margin-bottom: 10px;
  }

  .compact-head h3 {
    margin: 0;
    font-size: 20px;
  }

  .compact-table {
    max-height: 560px;
    overflow: auto;
  }

  .selected-row td {
    font-weight: 700;
    background: rgba(127, 127, 127, 0.08);
  }

  .action-list {
    display: grid;
    gap: 10px;
  }

  .action-card {
    min-height: auto;
  }

  .action-card p:not(.eyebrow):not(.meta) {
    margin: 6px 0 8px;
    line-height: 1.55;
  }

  .missing-risk {
    grid-column: span 2;
  }

  @media (max-width: 900px) {
    .risk-layout {
      grid-template-columns: 1fr;
    }

    .missing-risk {
      grid-column: auto;
    }
  }
</style>
