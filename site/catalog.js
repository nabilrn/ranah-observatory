const INDICATOR_CATALOG_URL = "data/indicators.json";

const CLAIM_TYPE_LABELS = {
  observed: "Observasi",
  derived: "Turunan",
  model_estimate: "Estimasi model",
  observed_source_published: "Observasi sumber",
  backcast_estimate: "Estimasi backcast",
  observed_census_anchor: "Anchor sensus",
  model_estimate_projection: "Proyeksi model",
};

const catalogEscape = (value = "") => String(value)
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#039;");

function catalogPercent(rate) {
  return `${(Number(rate) * 100).toLocaleString("id-ID", { maximumFractionDigits: 1 })}%`;
}

function claimBadge(type) {
  const label = CLAIM_TYPE_LABELS[type] || type.replaceAll("_", " ");
  return `<span class="catalog-type">${catalogEscape(label)}</span>`;
}

function catalogCard(row) {
  const coverage = row.coverage;
  const years = coverage.first_year === coverage.last_year
    ? `${coverage.first_year}`
    : `${coverage.first_year}–${coverage.last_year}`;
  const source = row.source_priority.join(" · ");
  const types = row.present_claim_types.map(claimBadge).join("");

  return `
    <article class="catalog-card" data-domain="${catalogEscape(row.domain_label)}" data-search="${catalogEscape([
      row.public_name,
      row.source_name,
      row.id,
      row.domain_label,
      source,
    ].join(" ").toLocaleLowerCase("id-ID"))}">
      <div class="catalog-topline">
        <span class="catalog-domain">${catalogEscape(row.domain_label)}</span>
        <span class="catalog-coverage">${catalogEscape(catalogPercent(coverage.rate))} coverage</span>
      </div>
      <h3>${catalogEscape(row.public_name)}</h3>
      <p class="catalog-source-name">${catalogEscape(row.source_name)} · <code>${catalogEscape(row.id)}</code></p>
      <div class="catalog-facts">
        <div><span>Periode tersedia</span><strong>${catalogEscape(years)}</strong></div>
        <div><span>Tahun lengkap 19 daerah</span><strong>${catalogEscape(coverage.exact_19_geography_year_count)}</strong></div>
        <div><span>Unit</span><strong>${catalogEscape(row.unit_label)}</strong></div>
        <div><span>Sumber prioritas</span><strong>${catalogEscape(source)}</strong></div>
      </div>
      <div class="catalog-types" aria-label="Tipe angka">${types}</div>
      <details class="catalog-detail">
        <summary>Definisi & batas teknis</summary>
        <p><strong>Definisi sumber:</strong> ${catalogEscape(row.definition)}</p>
        <p><strong>Caveat:</strong> ${catalogEscape(row.semantic_caution)}</p>
        <p><strong>Artefak:</strong> <code>${catalogEscape(row.source_artifact)}</code></p>
        <p><strong>Registry unit:</strong> <code>${catalogEscape(row.registry_unit)}</code></p>
      </details>
    </article>
  `;
}

function renderCatalogSummary(data) {
  const root = document.querySelector("#catalog-summary");
  const summary = data.summary;
  root.innerHTML = `
    <div><strong>${catalogEscape(summary.indicator_count)}</strong><span>indikator</span></div>
    <div><strong>${catalogEscape(summary.domain_count)}</strong><span>domain</span></div>
    <div><strong>${catalogEscape(summary.complete_2018_2025_indicator_count)}</strong><span>indikator lengkap 2018–2025</span></div>
    <div><strong>${catalogEscape(summary.geography_count)}</strong><span>kabupaten/kota</span></div>
  `;
}

function applyCatalogFilters() {
  const query = document.querySelector("#catalog-search").value.trim().toLocaleLowerCase("id-ID");
  const active = document.querySelector("#catalog-filters [aria-pressed='true']")?.dataset.domain || "Semua";
  let visible = 0;

  document.querySelectorAll("#catalog-grid .catalog-card").forEach((card) => {
    const domainOk = active === "Semua" || card.dataset.domain === active;
    const queryOk = !query || card.dataset.search.includes(query);
    card.hidden = !(domainOk && queryOk);
    if (!card.hidden) visible += 1;
  });

  document.querySelector("#catalog-result-count").textContent = `${visible} indikator ditampilkan`;
}

async function initCatalog() {
  const grid = document.querySelector("#catalog-grid");
  if (!grid) return;

  try {
    const response = await fetch(INDICATOR_CATALOG_URL, { cache: "no-store" });
    if (!response.ok) throw new Error(`indicator catalog fetch failed: ${response.status}`);
    const data = await response.json();
    if (data.schema !== "ranah-observatory/public-indicator-catalog/v1") {
      throw new Error(`unsupported indicator catalog schema: ${data.schema}`);
    }
    if (!Array.isArray(data.indicators) || data.indicators.length !== 23) {
      throw new Error("public indicator catalog must contain exactly 23 Panel v3 indicators");
    }

    document.querySelector("#catalog-title").textContent = data.title;
    document.querySelector("#catalog-intro").textContent = data.intro;
    renderCatalogSummary(data);
    grid.innerHTML = data.indicators.map(catalogCard).join("");

    const filters = document.querySelector("#catalog-filters");
    const domains = ["Semua", ...data.domains];
    filters.innerHTML = domains.map((domain, index) => `
      <button type="button" data-domain="${catalogEscape(domain)}" aria-pressed="${index === 0 ? "true" : "false"}">${catalogEscape(domain)}</button>
    `).join("");

    filters.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-domain]");
      if (!button) return;
      filters.querySelectorAll("button[data-domain]").forEach((candidate) => {
        candidate.setAttribute("aria-pressed", candidate === button ? "true" : "false");
      });
      applyCatalogFilters();
    });
    document.querySelector("#catalog-search").addEventListener("input", applyCatalogFilters);
    applyCatalogFilters();
  } catch (error) {
    console.error(error);
    grid.innerHTML = '<p class="catalog-error">Katalog indikator gagal dimuat. Metadata dan coverage canonical tetap tersedia di repository.</p>';
  }
}

initCatalog();
