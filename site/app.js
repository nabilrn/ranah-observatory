const OVERVIEW_URL = "data/overview.json";

const STATUS_META = {
  supported: { label: "Didukung", className: "badge-supported" },
  supported_post_v0_1: { label: "Didukung · evidence baru", className: "badge-supported_post_v0_1" },
  negative_result: { label: "Hasil negatif", className: "badge-negative_result" },
  context: { label: "Konteks", className: "badge-context" },
  not_supported: { label: "Belum didukung", className: "badge-not_supported" },
};

const escapeHtml = (value = "") => String(value)
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#039;");

function sourceText(item) {
  const claims = item.source_claim_ids || [];
  const paths = item.source_paths || [];
  if (claims.length) return `Claim: ${claims.join(" · ")}`;
  if (paths.length) return `Evidence: ${paths.join(" · ")}`;
  return "";
}

function renderStats(stats) {
  const root = document.querySelector("#headline-stats");
  root.innerHTML = stats.map((stat) => `
    <article class="stat-card">
      <div class="stat-value">${escapeHtml(stat.value)}</div>
      <p class="stat-label">${escapeHtml(stat.label)}</p>
      <p class="stat-detail">${escapeHtml(stat.detail)}</p>
    </article>
  `).join("");
}

function storyCard(story) {
  const status = STATUS_META[story.evidence_state] || STATUS_META.context;
  return `
    <article class="story-card" data-category="${escapeHtml(story.category)}">
      <div class="story-topline">
        <span class="story-category">${escapeHtml(story.category)}</span>
        <span class="badge ${status.className}">${escapeHtml(status.label)}</span>
      </div>
      <h3>${escapeHtml(story.title)}</h3>
      <p class="story-copy">${escapeHtml(story.plain_language)}</p>
      <p class="story-why"><strong>Mengapa penting?</strong>${escapeHtml(story.why_it_matters)}</p>
      <p class="story-caveat"><strong>Batas interpretasi</strong>${escapeHtml(story.caveat)}</p>
      <p class="story-source">${escapeHtml(sourceText(story))}</p>
    </article>
  `;
}

function renderStories(stories) {
  const root = document.querySelector("#stories");
  const filters = document.querySelector("#story-filters");
  const categories = ["Semua", ...new Set(stories.map((story) => story.category))];

  root.innerHTML = stories.map(storyCard).join("");
  filters.innerHTML = categories.map((category, index) => `
    <button
      type="button"
      class="filter-button"
      data-filter="${escapeHtml(category)}"
      aria-pressed="${index === 0 ? "true" : "false"}"
    >${escapeHtml(category)}</button>
  `).join("");

  filters.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-filter]");
    if (!button) return;
    const selected = button.dataset.filter;

    filters.querySelectorAll("button[data-filter]").forEach((candidate) => {
      candidate.setAttribute("aria-pressed", candidate === button ? "true" : "false");
    });

    root.querySelectorAll(".story-card").forEach((card) => {
      const visible = selected === "Semua" || card.dataset.category === selected;
      card.hidden = !visible;
    });
  });
}

function renderBoundaries(boundaries) {
  const root = document.querySelector("#boundaries");
  root.innerHTML = boundaries.map((boundary) => `
    <article class="boundary-card">
      <span class="boundary-id">${escapeHtml(boundary.claim_id)}</span>
      <h3>${escapeHtml(boundary.title)}</h3>
      <p>${escapeHtml(boundary.reason)}</p>
    </article>
  `).join("");
}

function renderMethod(method) {
  const title = document.querySelector("#method-title");
  const root = document.querySelector("#method-steps");
  if (method.title) title.dataset.shortTitle = method.title;
  root.innerHTML = method.steps.map((step) => `
    <li class="method-card">
      <span class="method-number">${escapeHtml(step.number)}</span>
      <h3>${escapeHtml(step.title)}</h3>
      <p>${escapeHtml(step.text)}</p>
    </li>
  `).join("");
}

function renderHero(data) {
  document.querySelector("#hero-eyebrow").textContent = data.hero.eyebrow;
  document.querySelector("#hero-title").textContent = data.hero.headline;
  document.querySelector("#hero-summary").textContent = data.hero.summary;
  document.querySelector("#hero-boundary").textContent = data.hero.boundary;
  document.querySelector("#footer-version").textContent = `Public product v${data.version}`;
}

function applyLinks(links = {}) {
  const repo = links.repository || "https://github.com/nabilrn/ranah-observatory";
  const preprint = links.preprint_url || `${repo}/blob/main/publication/v0.1/distribution/Ranah_Observatory_v0.1_Preprint_Nabil_Rizki_Navisa.pdf`;
  const ledger = links.claim_ledger_url || `${repo}/blob/main/publication/v0.1/claim-ledger.csv`;
  document.querySelector("#repo-link").href = repo;
  document.querySelector("#preprint-link").href = preprint;
  document.querySelector("#ledger-link").href = ledger;
}

function showError(error) {
  console.error(error);
  const main = document.querySelector("#main");
  const notice = document.createElement("div");
  notice.className = "loading-error";
  notice.setAttribute("role", "alert");
  notice.textContent = "Data ringkasan publik gagal dimuat. Buka repository untuk melihat evidence dan laporan teknis secara langsung.";
  main.prepend(notice);
}

async function init() {
  try {
    const response = await fetch(OVERVIEW_URL, { cache: "no-store" });
    if (!response.ok) throw new Error(`overview fetch failed: ${response.status}`);
    const data = await response.json();
    if (data.schema !== "ranah-observatory/public-overview/v1") {
      throw new Error(`unsupported overview schema: ${data.schema}`);
    }

    renderHero(data);
    renderStats(data.headline_stats);
    renderStories(data.stories);
    renderBoundaries(data.boundaries);
    renderMethod(data.method);
    applyLinks(data.links);
  } catch (error) {
    showError(error);
  }
}

init();
