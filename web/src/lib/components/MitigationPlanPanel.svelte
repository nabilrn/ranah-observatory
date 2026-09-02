<script lang="ts">
  import type { Locale } from '$lib/i18n';
  import type { PublicDisasterSummary } from '$lib/public-data';

  export let plan: PublicDisasterSummary['mitigation_plan_2026'];
  export let lang: Locale;

  let theme = 'all';
  $: themes = Object.keys(plan.gaps.theme_counts).sort();
  $: filteredGaps = plan.gaps.rows.filter((row) => theme === 'all' || row.theme === theme);

  function unitLabel(unit: string) {
    const labels: Record<string, { id: string; en: string }> = {
      percent: { id: '%', en: '%' },
      people: { id: 'orang', en: 'people' },
      document: { id: 'dokumen', en: 'document' },
      areas: { id: 'kawasan', en: 'areas' },
      activity: { id: 'kegiatan', en: 'activity' },
      families: { id: 'keluarga', en: 'families' }
    };
    return labels[unit]?.[lang] ?? unit;
  }

  function themeLabel(value: string) {
    const labels: Record<string, { id: string; en: string }> = {
      planning: { id: 'Perencanaan', en: 'Planning' },
      data_information: { id: 'Data & informasi', en: 'Data & information' },
      public_information: { id: 'Informasi publik', en: 'Public information' },
      response_capacity: { id: 'Kapasitas respons', en: 'Response capacity' },
      risk_reduction_governance: { id: 'Tata kelola PRB', en: 'Risk-reduction governance' },
      community_resilience: { id: 'Ketangguhan masyarakat', en: 'Community resilience' },
      operations: { id: 'Operasional', en: 'Operations' },
      preparedness: { id: 'Kesiapsiagaan', en: 'Preparedness' },
      evacuation_infrastructure: { id: 'Evakuasi', en: 'Evacuation infrastructure' },
      early_warning: { id: 'Peringatan dini', en: 'Early warning' },
      logistics: { id: 'Logistik', en: 'Logistics' },
      recovery_capacity: { id: 'Pemulihan', en: 'Recovery capacity' },
      emergency_response: { id: 'Tanggap darurat', en: 'Emergency response' },
      post_disaster_assessment: { id: 'Kajian pascabencana', en: 'Post-disaster assessment' }
    };
    return labels[value]?.[lang] ?? value.replaceAll('_', ' ');
  }
</script>

<section class="section planning-panel">
  <div class="section-head">
    <div>
      <p class="eyebrow">BPBD Sumatera Barat · Renja 2026</p>
      <h2>{lang === 'id' ? 'Apa yang ditargetkan dan apa yang masih menjadi kendala?' : 'What is planned and what remains constrained?'}</h2>
    </div>
    <p>{plan.interpretation[lang]}</p>
  </div>

  <div class="metric-grid plan-metrics">
    <div class="metric">
      <span>{lang === 'id' ? 'Target rencana kerja' : 'Work-plan targets'}</span>
      <strong>{plan.targets.count}</strong>
      <small>{lang === 'id' ? 'target 2026 — bukan capaian aktual' : '2026 targets — not actual achievements'}</small>
    </div>
    <div class="metric">
      <span>{lang === 'id' ? 'Kendala yang dicatat BPBD' : 'Constraints recorded by BPBD'}</span>
      <strong>{plan.gaps.count}</strong>
      <small>{lang === 'id' ? 'diagnosis kualitatif agregat' : 'aggregate qualitative diagnostics'}</small>
    </div>
    <div class="metric">
      <span>{lang === 'id' ? 'Tema kendala' : 'Constraint themes'}</span>
      <strong>{themes.length}</strong>
      <small>{lang === 'id' ? 'tidak dijadikan skor kapasitas' : 'not converted into a capacity score'}</small>
    </div>
  </div>

  <div class="plan-layout">
    <div>
      <div class="section-head compact-head">
        <div>
          <p class="eyebrow">{lang === 'id' ? 'Target 2026' : '2026 targets'}</p>
          <h3>{lang === 'id' ? 'Target kerja yang tercantum di Renja' : 'Work-plan targets in the source'}</h3>
        </div>
        <p>{lang === 'id' ? 'Angka di bawah adalah target rencana, bukan bukti bahwa target sudah tercapai.' : 'The figures below are planning targets, not evidence that they have been achieved.'}</p>
      </div>
      <div class="table-wrap target-table">
        <table>
          <thead>
            <tr>
              <th>{lang === 'id' ? 'Program/kegiatan' : 'Program/activity'}</th>
              <th>{lang === 'id' ? 'Indikator' : 'Indicator'}</th>
              <th>{lang === 'id' ? 'Target' : 'Target'}</th>
            </tr>
          </thead>
          <tbody>
            {#each plan.targets.rows as row}
              <tr>
                <td><strong>{row.program_or_activity}</strong></td>
                <td>{row.indicator}</td>
                <td><strong>{row.target_value.toLocaleString(lang === 'id' ? 'id-ID' : 'en-US')} {unitLabel(row.target_unit)}</strong></td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>

    <div>
      <div class="section-head compact-head gap-head">
        <div>
          <p class="eyebrow">{lang === 'id' ? 'Kendala resmi' : 'Official constraints'}</p>
          <h3>{lang === 'id' ? 'Hal yang menurut Renja masih perlu dibenahi' : 'Items the work plan says still need improvement'}</h3>
        </div>
        <select bind:value={theme} aria-label={lang === 'id' ? 'Filter tema kendala' : 'Filter constraint theme'}>
          <option value="all">{lang === 'id' ? 'Semua tema' : 'All themes'}</option>
          {#each themes as item}
            <option value={item}>{themeLabel(item)} ({plan.gaps.theme_counts[item]})</option>
          {/each}
        </select>
      </div>

      <div class="gap-list">
        {#each filteredGaps as gap}
          <article class="card gap-card">
            <p class="eyebrow">{themeLabel(gap.theme)}</p>
            <h4>{gap.gap_label}</h4>
            <p class="meta">{lang === 'id' ? 'Cakupan sumber: agregat provinsi/kabupaten-kota; tidak menunjuk wilayah tertentu.' : 'Source scope: province/aggregate districts; no specific municipality identified.'}</p>
          </article>
        {/each}
      </div>
    </div>
  </div>

  <p class="hero-note boundary-note">{lang === 'id'
    ? 'Jangan baca bagian ini sebagai skor kinerja daerah atau ramalan bencana. Sumber hanya menyatakan target rencana dan kendala kualitatif.'
    : 'Do not read this section as a regional performance score or disaster forecast. The source states planning targets and qualitative constraints only.'}</p>
</section>

<style>
  .planning-panel {
    scroll-margin-top: 72px;
  }

  .plan-metrics {
    margin-top: 16px;
  }

  .plan-layout {
    display: grid;
    grid-template-columns: minmax(0, 1.1fr) minmax(0, 0.9fr);
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

  .target-table {
    max-height: 620px;
    overflow: auto;
  }

  .gap-head {
    align-items: end;
  }

  .gap-head select {
    min-width: 200px;
  }

  .gap-list {
    display: grid;
    gap: 10px;
    max-height: 620px;
    overflow: auto;
    padding-right: 2px;
  }

  .gap-card {
    min-height: auto;
  }

  .gap-card h4 {
    margin: 6px 0 8px;
    font-size: 16px;
    line-height: 1.45;
  }

  .boundary-note {
    margin-top: 16px;
  }

  @media (max-width: 900px) {
    .plan-layout {
      grid-template-columns: 1fr;
    }

    .gap-head {
      align-items: start;
    }
  }
</style>
