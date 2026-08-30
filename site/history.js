const HISTORY_PATH = "data/history.json";

function formatHistoryNumber(value) {
  return new Intl.NumberFormat("id-ID", { maximumFractionDigits: 3 }).format(value);
}

function historyCardShell(card) {
  const article = document.createElement("article");
  article.className = "history-card";

  const eyebrow = document.createElement("p");
  eyebrow.className = "history-eyebrow";
  eyebrow.textContent = card.eyebrow;

  const title = document.createElement("h3");
  title.textContent = card.title;

  const body = document.createElement("p");
  body.className = "history-copy";
  body.textContent = card.plain_language;

  const caveat = document.createElement("p");
  caveat.className = "history-caveat";
  caveat.textContent = card.caveat;

  article.append(eyebrow, title, body);
  return { article, caveat };
}

function renderAnnualSeries(card) {
  const { article, caveat } = historyCardShell(card);

  const list = document.createElement("div");
  list.className = "history-series";
  const maxValue = Math.max(...card.series.map((row) => row.value));

  card.series.forEach((row) => {
    const item = document.createElement("div");
    item.className = "history-series-row";

    const year = document.createElement("strong");
    year.textContent = String(row.year);

    const meter = document.createElement("div");
    meter.className = "history-meter";
    const fill = document.createElement("span");
    fill.style.width = `${(row.value / maxValue) * 100}%`;
    meter.append(fill);

    const value = document.createElement("span");
    value.textContent = formatHistoryNumber(row.value);
    item.append(year, meter, value);
    list.append(item);
  });

  const key = document.createElement("p");
  key.className = "history-key-fact";
  key.textContent = `${card.key_fact.label}: ${formatHistoryNumber(card.key_fact.value)} perusahaan (${formatHistoryNumber(card.key_fact.percent)}%).`;

  article.append(list, key, caveat);
  return article;
}

function comparisonMetric(label, value) {
  const item = document.createElement("div");
  item.className = "history-metric";
  const number = document.createElement("strong");
  number.textContent = formatHistoryNumber(value);
  const caption = document.createElement("span");
  caption.textContent = label;
  item.append(number, caption);
  return item;
}

function renderSameYear(card) {
  const { article, caveat } = historyCardShell(card);
  const metrics = document.createElement("div");
  metrics.className = "history-metrics";
  metrics.append(
    comparisonMetric("Survei tahunan", card.comparison.annual_survey),
    comparisonMetric("SE06 full listing", card.comparison.se06_full_listing),
    comparisonMetric("Dengan status hukum", card.comparison.se06_legal),
    comparisonMetric("Tanpa status hukum", card.comparison.se06_nonlegal),
  );

  const ratio = document.createElement("p");
  ratio.className = "history-key-fact";
  ratio.textContent = `Angka survei tahunan = ${formatHistoryNumber(card.comparison.annual_percent_of_listing)}% dari full listing SE06, tetapi rasio ini bukan sampling fraction yang teridentifikasi.`;

  article.append(metrics, ratio, caveat);
  return article;
}

function renderQualification(card) {
  const { article, caveat } = historyCardShell(card);
  const details = document.createElement("div");
  details.className = "history-qualification";

  const source = document.createElement("p");
  source.innerHTML = `<strong>2003 source-native:</strong> B ${formatHistoryNumber(card.qualification_2003.B)} · M1 ${formatHistoryNumber(card.qualification_2003.M1)} · M2 ${formatHistoryNumber(card.qualification_2003.M2)} · K1 ${formatHistoryNumber(card.qualification_2003.K1)} · K2 ${formatHistoryNumber(card.qualification_2003.K2)} · K3 ${formatHistoryNumber(card.qualification_2003.K3)}.`;

  const candidate = document.createElement("p");
  candidate.innerHTML = `<strong>Kandidat aritmetika 2003:</strong> Kecil ${formatHistoryNumber(card.arithmetic_candidate_2003.Kecil)} · Menengah ${formatHistoryNumber(card.arithmetic_candidate_2003.Menengah)} · Besar ${formatHistoryNumber(card.arithmetic_candidate_2003.Besar)}.`;

  const target = document.createElement("p");
  target.innerHTML = `<strong>2005:</strong> total ${formatHistoryNumber(card.total_2005)}; komponen belum recovered; semantic mapping belum verified.`;

  details.append(source, candidate, target);
  article.append(details, caveat);
  return article;
}

function renderHistory(payload) {
  const intro = document.getElementById("history-intro");
  const grid = document.getElementById("history-grid");
  const boundary = document.getElementById("history-boundary");
  if (!intro || !grid || !boundary) return;

  intro.textContent = payload.scope;
  boundary.textContent = payload.global_boundary;
  grid.replaceChildren();

  payload.cards.forEach((card) => {
    if (card.id === "construction-annual-2002-2006") {
      grid.append(renderAnnualSeries(card));
    } else if (card.id === "construction-se06-2006") {
      grid.append(renderSameYear(card));
    } else if (card.id === "construction-qualification-bridge") {
      grid.append(renderQualification(card));
    }
  });
}

async function loadHistory() {
  const grid = document.getElementById("history-grid");
  try {
    const response = await fetch(HISTORY_PATH, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    renderHistory(payload);
  } catch (error) {
    if (grid) {
      grid.textContent = "Jejak historis gagal dimuat. Evidence canonical tetap tersedia di repository.";
    }
    console.error("Failed to load public history", error);
  }
}

document.addEventListener("DOMContentLoaded", loadHistory);
