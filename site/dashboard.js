const DASHBOARD_OVERVIEW_URL = "data/overview.json";

const DASHBOARD_STATUS = {
  supported: { label: "Didukung data", className: "badge-supported" },
  supported_post_v0_1: { label: "Data baru", className: "badge-supported_post_v0_1" },
  negative_result: { label: "Gagal uji", className: "badge-negative_result" },
  context: { label: "Konteks", className: "badge-context" },
  not_supported: { label: "Belum bisa disimpulkan", className: "badge-not_supported" },
};

const KEY_STORY_IDS = [
  "unemployment-trajectory",
  "labor-force-participation",
  "rice-yield",
  "forecast-failure",
];

function dashboardEscape(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function activateView(viewName, updateHash = true) {
  const views = [...document.querySelectorAll("[data-view]")];
  const tabs = [...document.querySelectorAll("[data-view-target]")];
  const target = views.find((view) => view.dataset.view === viewName) || views[0];
  if (!target) return;

  views.forEach((view) => {
    const active = view === target;
    view.hidden = !active;
    view.classList.toggle("is-active", active);
  });

  tabs.forEach((tab) => {
    const active = tab.dataset.viewTarget === target.dataset.view;
    tab.classList.toggle("is-active", active);
    if (tab.matches("button")) {
      tab.setAttribute("aria-pressed", active ? "true" : "false");
      if (active) tab.setAttribute("aria-current", "page");
      else tab.removeAttribute("aria-current");
    }
  });

  if (updateHash) {
    history.replaceState({}, "", `#${target.dataset.view}`);
  }
}

function renderKeyStories(stories) {
  const root = document.querySelector("#key-stories");
  if (!root) return;

  const byId = new Map(stories.map((story) => [story.id, story]));
  const selected = KEY_STORY_IDS.map((id) => byId.get(id)).filter(Boolean);

  root.innerHTML = selected.map((story) => {
    const status = DASHBOARD_STATUS[story.evidence_state] || DASHBOARD_STATUS.context;
    return `
      <article class="key-story-card">
        <div class="story-topline">
          <span class="story-category">${dashboardEscape(story.category)}</span>
          <span class="badge ${status.className}">${dashboardEscape(status.label)}</span>
        </div>
        <h3>${dashboardEscape(story.title)}</h3>
        <p class="story-copy">${dashboardEscape(story.plain_language)}</p>
        <p class="story-caveat"><strong>Batas:</strong> ${dashboardEscape(story.caveat)}</p>
      </article>
    `;
  }).join("");
}

async function initDashboard() {
  document.addEventListener("click", (event) => {
    const trigger = event.target.closest("[data-view-target]");
    if (!trigger) return;
    event.preventDefault();
    activateView(trigger.dataset.viewTarget);
  });

  const requested = window.location.hash.replace("#", "");
  const allowed = new Set([...document.querySelectorAll("[data-view]")].map((view) => view.dataset.view));
  activateView(allowed.has(requested) ? requested : "ringkasan", false);

  window.addEventListener("hashchange", () => {
    const next = window.location.hash.replace("#", "");
    if (allowed.has(next)) activateView(next, false);
  });

  try {
    const response = await fetch(DASHBOARD_OVERVIEW_URL, { cache: "no-store" });
    if (!response.ok) throw new Error(`dashboard overview fetch failed: ${response.status}`);
    const payload = await response.json();
    renderKeyStories(payload.stories || []);
  } catch (error) {
    console.error(error);
    const root = document.querySelector("#key-stories");
    if (root) {
      root.setAttribute("role", "alert");
      root.textContent = "Temuan utama gagal dimuat. Data lain tetap dapat dibuka melalui tab Daerah, Data, dan Riset.";
    }
  }
}

document.addEventListener("DOMContentLoaded", initDashboard);
