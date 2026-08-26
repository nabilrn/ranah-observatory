const GLOSSARY_URL = "data/glossary.json";

function glossaryEscape(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function glossaryCard(term) {
  return `
    <article class="glossary-card">
      <div class="glossary-term-row">
        <h3>${glossaryEscape(term.term)}</h3>
        <code>${glossaryEscape(term.technical)}</code>
      </div>
      <p>${glossaryEscape(term.plain)}</p>
      <p class="glossary-not"><strong>Bukan berarti:</strong> ${glossaryEscape(term.not_mean)}</p>
    </article>
  `;
}

async function initGlossary() {
  const root = document.querySelector("#glossary-grid");
  if (!root) return;

  try {
    const response = await fetch(GLOSSARY_URL, { cache: "no-store" });
    if (!response.ok) throw new Error(`glossary fetch failed: ${response.status}`);
    const data = await response.json();
    if (data.schema !== "ranah-observatory/public-glossary/v1") {
      throw new Error(`unsupported glossary schema: ${data.schema}`);
    }

    document.querySelector("#glossary-title").textContent = data.title;
    document.querySelector("#glossary-intro").textContent = data.intro;
    root.innerHTML = data.terms.map(glossaryCard).join("");
  } catch (error) {
    console.error(error);
    root.innerHTML = '<p class="glossary-error">Glosarium gagal dimuat. Istilah teknis tetap dapat diperiksa di dokumentasi penelitian.</p>';
  }
}

initGlossary();
