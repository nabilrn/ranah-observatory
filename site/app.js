const OVERVIEW_URL = "data/overview.json";
const DISTRICTS_URL = "data/districts.json";

const STATUS_META = {
  supported: { label: "Didukung", className: "badge-supported" },
  supported_post_v0_1: { label: "Didukung · evidence baru", className: "badge-supported_post_v0_1" },
  negative_result: { label: "Hasil negatif", className: "badge-negative_result" },
  context: { label: "Konteks", className: "badge-context" },
  not_supported: { label: "Belum didukung", className: "badge-not_supported" },
};

const TRAJECTORY_META = {
  persistent_increase: { label: "Naik persisten", className: "trajectory-up" },
  persistent_decrease: { label: "Turun persisten", className: "trajectory-down" },
  trajectory_not_robust: { label: "Arah belum robust", className: "trajectory-held" },
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

function numberFormat(value, decimals) {
  return Number(value).toLocaleString("id-ID", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function signedFormat(value, decimals) {
  const number = Number(value);
  const prefix = number > 0 ? "+" : "";
  return `${prefix}${numberFormat(number, decimals)}`;
}

function indicatorDomains(data) {
  const domains = {};
  for (const district of data.districts) {
    for (const [indicatorId, indicator] of Object.entries(district.indicators)) {
      const domain = domains[indicatorId] || { min: Infinity, max: -Infinity };
      domain.min = Math.min(domain.min, indicator.observed_2018, indicator.observed_2025);
      domain.max = Math.max(domain.max, indicator.observed_2018, indicator.observed_2025);
      domains[indicatorId] = domain;
    }
  }
  return domains;
}

function miniTrend(indicator, domain) {
  const width = 260;
  const height = 82;
  const padX = 12;
  const padY = 14;
  const usableY = height - (padY * 2);
  const span = Math.max(domain.max - domain.min, 1e-9);
  const y = (value) => padY + ((domain.max - value) / span) * usableY;
  const yStart = y(indicator.observed_2018);
  const yEnd = y(indicator.observed_2025);
  const meta = TRAJECTORY_META[indicator.trajectory_classification] || TRAJECTORY_META.trajectory_not_robust;

  return `
    <svg class="mini-trend ${meta.className}" viewBox="0 0 ${width} ${height}" role="img" aria-label="Perubahan nilai observasi dari 2018 ke 2025">
      <line class="trend-baseline" x1="${padX}" y1="${height - 8}" x2="${width - padX}" y2="${height - 8}"></line>
      <line class="trend-line" x1="${padX + 12}" y1="${yStart.toFixed(2)}" x2="${width - padX - 12}" y2="${yEnd.toFixed(2)}"></line>
      <circle class="trend-point" cx="${padX + 12}" cy="${yStart.toFixed(2)}" r="4.5"></circle>
      <circle class="trend-point" cx="${width - padX - 12}" cy="${yEnd.toFixed(2)}" r="4.5"></circle>
      <text class="trend-year" x="${padX}" y="${height - 1}">2018</text>
      <text class="trend-year" x="${width - padX}" y="${height - 1}" text-anchor="end">2025</text>
    </svg>
  `;
}

function indicatorCard(indicatorId, indicator, domain) {
  const trajectory = TRAJECTORY_META[indicator.trajectory_classification] || TRAJECTORY_META.trajectory_not_robust;
  const decimals = indicator.decimals;
  return `
    <article class="indicator-card">
      <div class="indicator-topline">
        <span class="indicator-label">${escapeHtml(indicator.label)}</span>
        <span class="trajectory-badge ${trajectory.className}">${escapeHtml(trajectory.label)}</span>
      </div>
      <div class="endpoint-row">
        <div>
          <span>2018</span>
          <strong>${escapeHtml(numberFormat(indicator.observed_2018, decimals))}</strong>
        </div>
        <span class="endpoint-arrow" aria-hidden="true">→</span>
        <div class="endpoint-end">
          <span>2025</span>
          <strong>${escapeHtml(numberFormat(indicator.observed_2025, decimals))}</strong>
        </div>
      </div>
      ${miniTrend(indicator, domain)}
      <div class="change-row">
        <span>Perubahan observasi</span>
        <strong>${escapeHtml(signedFormat(indicator.observed_change, decimals))} ${escapeHtml(indicator.unit)}</strong>
      </div>
      <p class="indicator-meaning"><strong>Cara baca</strong>${escapeHtml(indicator.plain_favorable_semantics)}</p>
      <details class="indicator-detail">
        <summary>Batas & sumber</summary>
        <p>${escapeHtml(indicator.boundary)}</p>
        <code>${escapeHtml(indicator.source_claim_id)} · ${escapeHtml(indicatorId)}</code>
      </details>
    </article>
  `;
}

function districtSummary(district) {
  const entries = Object.values(district.indicators);
  const robust = entries.filter((indicator) => indicator.trajectory_robust).length;
  const held = entries.length - robust;
  return `${robust} dari ${entries.length} indikator memiliki arah trajectory daerah yang robust; ${held} lainnya ditahan sebagai arah belum robust. Ini ringkasan evidence, bukan skor kinerja daerah.`;
}

function renderDistrict(data, districtId, domains) {
  const district = data.districts.find((row) => row.id === districtId) || data.districts[0];
  if (!district) return;

  document.querySelector("#district-type").textContent = district.administrative_type === "kota" ? "Kota" : "Kabupaten";
  document.querySelector("#district-name").textContent = district.name;
  document.querySelector("#district-summary").textContent = districtSummary(district);
  document.querySelector("#district-boundary").textContent = data.interpretation.boundary;

  const root = document.querySelector("#district-indicators");
  root.innerHTML = Object.entries(district.indicators)
    .map(([indicatorId, indicator]) => indicatorCard(indicatorId, indicator, domains[indicatorId]))
    .join("");

  const select = document.querySelector("#district-select");
  select.value = district.id;
  const url = new URL(window.location.href);
  url.searchParams.set("daerah", district.id);
  window.history.replaceState({}, "", url);
}

function renderDistrictExplorer(data) {
  if (data.schema !== "ranah-observatory/public-district-explorer/v1") {
    throw new Error(`unsupported district explorer schema: ${data.schema}`);
  }
  if (!Array.isArray(data.districts) || data.districts.length !== 19) {
    throw new Error("district explorer must contain exactly 19 kabupaten/kota");
  }

  const select = document.querySelector("#district-select");
  select.innerHTML = data.districts.map((district) => `
    <option value="${escapeHtml(district.id)}">${escapeHtml(district.administrative_type === "kota" ? "Kota" : "Kab.")} ${escapeHtml(district.name)}</option>
  `).join("");
  select.disabled = false;

  const domains = indicatorDomains(data);
  const requested = new URL(window.location.href).searchParams.get("daerah");
  const initial = data.districts.some((row) => row.id === requested) ? requested : data.districts[0].id;
  renderDistrict(data, initial, domains);

  select.addEventListener("change", () => renderDistrict(data, select.value, domains));
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

async function fetchJson(url) {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) throw new Error(`${url} fetch failed: ${response.status}`);
  return response.json();
}

async function init() {
  try {
    const [data, districts] = await Promise.all([
      fetchJson(OVERVIEW_URL),
      fetchJson(DISTRICTS_URL),
    ]);
    if (data.schema !== "ranah-observatory/public-overview/v1") {
      throw new Error(`unsupported overview schema: ${data.schema}`);
    }

    renderHero(data);
    renderStats(data.headline_stats);
    renderStories(data.stories);
    renderDistrictExplorer(districts);
    renderBoundaries(data.boundaries);
    renderMethod(data.method);
    applyLinks(data.links);
  } catch (error) {
    showError(error);
  }
}

init();
