/**
 * library.js — powers the Hiragana / Katakana character-table pages.
 * Set window.KANA_SCRIPT to "hiragana" or "katakana" before this script runs.
 */

let ALL_CHARS = [];

function speak(text) {
  if (!("speechSynthesis" in window)) {
    showToast("Speech synthesis isn't supported in this browser.", { icon: "🔇" });
    return;
  }
  const utter = new SpeechSynthesisUtterance(text);
  utter.lang = "ja-JP";
  utter.rate = 0.8;
  speechSynthesis.cancel();
  speechSynthesis.speak(utter);
}

function groupByRow(chars) {
  const groups = {};
  chars.forEach(c => {
    if (!groups[c.row]) groups[c.row] = [];
    groups[c.row].push(c);
  });
  return groups;
}

function renderTiles(chars) {
  const mount = document.getElementById("char-table-mount");
  if (chars.length === 0) {
    mount.innerHTML = `<p class="text-muted text-center">No characters match your search.</p>`;
    return;
  }
  const groups = groupByRow(chars);
  mount.innerHTML = Object.entries(groups).map(([row, list]) => `
    <div class="row-heading">${row}-row</div>
    <div class="char-grid">
      ${list.map(c => `
        <div class="char-tile" data-id="${c.id}" tabindex="0" role="button" aria-label="Open lesson for ${c.character}">
          <span class="char-big">${c.character}</span>
          <span class="char-romaji">${c.romaji}</span>
          <span class="mastery-dot ${masteryClass(c.mastery_score)}"></span>
        </div>
      `).join("")}
    </div>
  `).join("");

  mount.querySelectorAll(".char-tile").forEach(tile => {
    tile.addEventListener("click", () => openLessonModal(tile.dataset.id));
    tile.addEventListener("keypress", (e) => { if (e.key === "Enter") openLessonModal(tile.dataset.id); });
  });
}

function openLessonModal(id) {
  const char = ALL_CHARS.find(c => c.id === id);
  if (!char) return;
  Sound.click();

  const overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  overlay.innerHTML = `
    <div class="modal-card">
      <button class="modal-close" aria-label="Close">✕</button>
      <div class="lesson-header">
        <div class="lesson-char-display genkou-cell">${char.character}</div>
        <div>
          <h2 style="margin-bottom:4px;">${char.romaji}</h2>
          <p class="text-muted" style="margin:0;">${char.script === "hiragana" ? "Hiragana" : "Katakana"} · ${char.row}-row · ${char.stroke_count} strokes</p>
          <div class="flex gap-8 mt-8">
            <button class="audio-btn" id="lesson-audio-btn" aria-label="Play pronunciation">🔊</button>
            ${Auth.isLoggedIn() ? `
              <button class="audio-btn" id="lesson-fav-btn" aria-label="Toggle favorite">${char.is_favorite ? "★" : "☆"}</button>
              <button class="audio-btn" id="lesson-bookmark-btn" aria-label="Toggle bookmark">${char.is_bookmarked ? "🔖" : "📑"}</button>
            ` : ""}
          </div>
        </div>
      </div>

      <div class="lesson-meta-grid">
        <div class="lesson-meta-item"><div class="label">Example word</div><div class="value">${char.example_word} <span class="mono text-muted" style="font-size:0.85rem;">(${char.example_reading})</span></div></div>
        <div class="lesson-meta-item"><div class="label">Meaning</div><div class="value">${char.meaning}</div></div>
        <div class="lesson-meta-item"><div class="label">Stroke count</div><div class="value">${char.stroke_count}</div></div>
        <div class="lesson-meta-item"><div class="label">Mastery</div><div class="value">${char.mastery_score != null ? Math.round(char.mastery_score) + "%" : "—"}</div></div>
      </div>

      <h3>Writing tip</h3>
      <p>${char.writing_tip}</p>

      <h3>Memory tip</h3>
      <p>${char.memory_tip}</p>

      <h3>Practice grid</h3>
      <div class="writing-grid-mini">
        <div class="genkou-cell">${char.character}</div>
        <div class="genkou-cell" style="opacity:0.15;">${char.character}</div>
        <div class="genkou-cell" style="opacity:0.15;">${char.character}</div>
        <div class="genkou-cell" style="opacity:0.15;">${char.character}</div>
      </div>
      <p class="text-muted" style="font-size:0.85rem;">Trace the character in each cell of the genkouyoushi grid, following the writing tip above.</p>
    </div>
  `;
  document.body.appendChild(overlay);

  overlay.querySelector(".modal-close").addEventListener("click", () => overlay.remove());
  overlay.addEventListener("click", (e) => { if (e.target === overlay) overlay.remove(); });
  overlay.querySelector("#lesson-audio-btn").addEventListener("click", () => speak(char.character));

  const favBtn = overlay.querySelector("#lesson-fav-btn");
  if (favBtn) favBtn.addEventListener("click", async () => {
    const res = await Api.toggleFavorite(char.id);
    char.is_favorite = res.is_favorite;
    favBtn.textContent = char.is_favorite ? "★" : "☆";
  });
  const bmBtn = overlay.querySelector("#lesson-bookmark-btn");
  if (bmBtn) bmBtn.addEventListener("click", async () => {
    const res = await Api.toggleBookmark(char.id);
    char.is_bookmarked = res.is_bookmarked;
    bmBtn.textContent = char.is_bookmarked ? "🔖" : "📑";
  });
}

async function initLibraryPage(script) {
  const mount = document.getElementById("char-table-mount");
  mount.innerHTML = `<p class="text-muted text-center">Loading ${script}…</p>`;
  try {
    ALL_CHARS = script === "hiragana" ? await Api.listHiragana() : await Api.listKatakana();
    renderTiles(ALL_CHARS);

    // If arriving via #hiragana_001 style hash, auto-open that lesson
    const hash = location.hash.replace("#", "");
    if (hash) {
      const target = ALL_CHARS.find(c => c.id === hash);
      if (target) openLessonModal(hash);
    }
  } catch (err) {
    mount.innerHTML = `<p class="text-muted text-center">Couldn't load characters — make sure the backend server is running.</p>`;
  }

  document.getElementById("search-input").addEventListener("input", (e) => {
    const q = e.target.value.trim().toLowerCase();
    if (!q) { renderTiles(ALL_CHARS); return; }
    const filtered = ALL_CHARS.filter(c =>
      c.character.toLowerCase().includes(q) ||
      c.romaji.toLowerCase().includes(q) ||
      c.example_word.toLowerCase().includes(q) ||
      c.meaning.toLowerCase().includes(q)
    );
    renderTiles(filtered);
  });
}
