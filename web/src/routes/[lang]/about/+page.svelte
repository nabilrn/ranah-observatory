<script lang="ts">
  import { copy, type Locale } from '$lib/i18n';

  export let data: { lang: Locale };
  const lang = data.lang;
  const t = copy[lang].about;
</script>

<svelte:head><title>{t.title} — Ranah Observatory</title></svelte:head>

<main class="page">
  <section class="hero">
    <div>
      <p class="eyebrow">{t.eyebrow}</p>
      <h1>{t.title}</h1>
      <p class="lead">{t.lead}</p>
    </div>
    <p class="hero-note">{lang === 'id' ? 'Metodologi bukan penghalang untuk membaca data, tetapi selalu tersedia ketika pembaca ingin memeriksa bagaimana sebuah angka dibentuk.' : 'Methodology should not block access to the data, but it remains available whenever a reader wants to inspect how a figure was produced.'}</p>
  </section>

  <section class="section">
    <div class="grid">
      {#each t.principles as principle, index}
        <article class="card">
          <span class="meta">0{index + 1}</span>
          <h3>{principle}</h3>
        </article>
      {/each}
    </div>
  </section>

  <section class="section two-col">
    <div>
      <p class="eyebrow">Traceability</p>
      <h2>{lang === 'id' ? 'Dua lapisan, satu fondasi data' : 'Two layers, one evidence base'}</h2>
      <p class="lead">{lang === 'id' ? 'Frontend publik hanya menerima artefak yang memang disiapkan untuk publik. File raw, audit, model, dan evidence registry tetap berada di research pipeline.' : 'The public frontend only consumes artifacts explicitly prepared for publication. Raw files, audits, models, and evidence registries remain in the research pipeline.'}</p>
    </div>
    <div class="card">
      <strong>raw → processed → canonical → public build → web</strong>
      <p>{lang === 'id' ? 'Pemisahan ini mencegah frontend tergantung langsung pada struktur milestone internal.' : 'This separation prevents the frontend from depending directly on internal milestone structures.'}</p>
    </div>
  </section>
</main>
