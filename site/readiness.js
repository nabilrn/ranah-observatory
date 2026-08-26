const READINESS_URL = "data/readiness.json";

const READINESS_META = {
  bounded_answer: { label: "Jawaban terbatas", className: "readiness-answer" },
  bounded_partial: { label: "Terjawab sebagian", className: "readiness-partial" },
  not_action_ready: { label: "Belum siap untuk aksi", className: "readiness-blocked" },
};

function readinessEscape(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function readinessCard(question) {
  const meta = READINESS_META[question.readiness_state] || READINESS_META.bounded_partial;
  return `
    <article class="readiness-card">
      <div class="readiness-topline">
        <span class="readiness-id">${readinessEscape(question.id)}</span>
        <span class="readiness-badge ${meta.className}">${readinessEscape(meta.label)}</span>
      </div>
      <h3>${readinessEscape(question.title)}</h3>
      <p class="readiness-answer-copy">${readinessEscape(question.current_answer)}</p>
      <div class="readiness-boundary">
        <strong>Yang belum terjawab</strong>
        <p>${readinessEscape(question.limitation)}</p>
      </div>
      <div class="readiness-next">
        <strong>Evidence berikutnya</strong>
        <p>${readinessEscape(question.next_evidence)}</p>
      </div>
      <p class="readiness-source">Evidence basis: ${readinessEscape(question.evidence_basis)}</p>
    </article>
  `;
}

function renderReadinessSummary(summary) {
  const root = document.querySelector("#readiness-summary");
  root.innerHTML = `
    <div><strong>${readinessEscape(summary.question_count)}</strong><span>pertanyaan utama</span></div>
    <div><strong>${readinessEscape(summary.fully_resolved_count)}</strong><span>fully resolved</span></div>
    <div><strong>${readinessEscape(summary.not_action_ready_count)}</strong><span>belum siap untuk aksi</span></div>
  `;
}

async function initReadiness() {
  const root = document.querySelector("#readiness-grid");
  if (!root) return;

  try {
    const response = await fetch(READINESS_URL, { cache: "no-store" });
    if (!response.ok) throw new Error(`readiness fetch failed: ${response.status}`);
    const data = await response.json();
    if (data.schema !== "ranah-observatory/public-research-readiness/v1") {
      throw new Error(`unsupported readiness schema: ${data.schema}`);
    }

    document.querySelector("#readiness-title").textContent = data.title;
    document.querySelector("#readiness-intro").textContent = data.intro;
    renderReadinessSummary(data.summary);
    root.innerHTML = data.questions.map(readinessCard).join("");
  } catch (error) {
    console.error(error);
    root.innerHTML = '<p class="readiness-error">Status pertanyaan riset gagal dimuat. Lihat sintesis M18 di repository untuk audit trail.</p>';
  }
}

initReadiness();
