<script lang="ts">
  import { page } from '$app/stores';
  import { copy, type Locale } from '$lib/i18n';

  export let data: { lang: Locale };

  $: lang = data.lang;
  $: t = copy[lang];
  $: other: Locale = lang === 'id' ? 'en' : 'id';
  $: switchHref = $page.url.pathname.replace(/^\/(id|en)(?=\/|$)/, `/${other}`);
</script>

<svelte:head>
  <html lang={lang} />
</svelte:head>

<div class="shell">
  <header class="topbar">
    <a class="brand" href={`/${lang}`}>
      Ranah Observatory
      <small>{t.brandSub}</small>
    </a>
    <nav class="nav" aria-label="Primary">
      <a href={`/${lang}/explore/disaster`}>{t.nav.explore}</a>
      <a href={`/${lang}/data`}>{t.nav.data}</a>
      <a href={`/${lang}/about`}>{t.nav.about}</a>
    </nav>
    <div class="locale-switch">
      <a href={switchHref} hreflang={other}>{t.switchLanguage}</a>
    </div>
  </header>

  <slot />

  <footer class="footer">
    <span>Ranah Observatory · open evidence for West Sumatra</span>
    <a href="https://github.com/nabilrn/ranah-observatory">GitHub</a>
  </footer>
</div>
