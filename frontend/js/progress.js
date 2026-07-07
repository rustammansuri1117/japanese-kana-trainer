/**
 * progress.js — renders the Progress dashboard: stat tiles, a 7-day bar
 * chart (built with plain divs, no charting library needed), and the
 * mistake-review lists split by script.
 */

function renderDailyChart(dailyPractice) {
  const days = Object.keys(dailyPractice).sort();
  const maxAnswered = Math.max(1, ...days.map(d => dailyPractice[d].answered));
  const mount = document.getElementById("daily-chart");
  mount.innerHTML = `
    <div class="chart-bars">
      ${days.map(d => {
        const entry = dailyPractice[d];
        const heightPct = (entry.answered / maxAnswered) * 100;
        const label = new Date(d + "T00:00:00").toLocaleDateString(undefined, { weekday: "short" });
        return `
          <div class="chart-bar-col">
            <div class="mono" style="font-size:0.7rem; color:var(--ink-soft);">${entry.answered || ""}</div>
            <div class="chart-bar" style="height:${heightPct}%;"></div>
            <div class="chart-bar-label">${label}</div>
          </div>
        `;
      }).join("")}
    </div>
  `;
}

function renderStatTiles(progress) {
  const tiles = [
    { label: "Accuracy", value: `${progress.accuracy}%` },
    { label: "Current streak", value: `${progress.current_streak}🔥` },
    { label: "Longest streak", value: progress.longest_streak },
    { label: "Characters learned", value: `${progress.characters_learned}/92` },
    { label: "Characters mastered", value: `${progress.characters_mastered}/92` },
    { label: "Avg response time", value: `${(progress.average_response_time_ms / 1000).toFixed(1)}s` },
    { label: "Correct answers", value: progress.total_correct },
    { label: "XP · Level", value: `${progress.xp} · L${progress.level}` },
  ];
  document.getElementById("stat-tiles").innerHTML = tiles.map(t => `
    <div class="card stat-tile">
      <div class="stat-value">${t.value}</div>
      <div class="stat-label">${t.label}</div>
    </div>
  `).join("");
}

async function renderMistakes(script, mountId) {
  const mount = document.getElementById(mountId);
  try {
    const mistakes = await Api.getMistakes(script);
    if (mistakes.length === 0) {
      mount.innerHTML = `<p class="text-muted">No outstanding mistakes in ${script} — nice work!</p>`;
      return;
    }
    mount.innerHTML = `
      <div class="char-grid">
        ${mistakes.map(m => `
          <div class="char-tile" data-cid="${m.character_id}">
            <span class="char-big">${m.character}</span>
            <span class="char-romaji">${m.romaji} · ${m.mistake_count}×</span>
          </div>
        `).join("")}
      </div>
    `;
  } catch (err) {
    mount.innerHTML = `<p class="text-muted">Couldn't load mistakes.</p>`;
  }
}

async function initProgressPage() {
  try {
    const progress = await Api.getProgress();
    renderStatTiles(progress);
    renderDailyChart(progress.daily_practice);
  } catch (err) {
    showToast("Couldn't load progress — is the backend running?", { icon: "⚠️" });
  }
  renderMistakes("hiragana", "mistakes-hiragana");
  renderMistakes("katakana", "mistakes-katakana");
}

async function exportProgressFile() {
  try {
    const data = await Api.exportProgress();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `kana-progress-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showToast("Progress exported!", { icon: "📤" });
  } catch (err) {
    showToast(err.message, { icon: "⚠️" });
  }
}

function importProgressFile(fileInput) {
  const file = fileInput.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = async () => {
    try {
      const data = JSON.parse(reader.result);
      const res = await Api.importProgress(data);
      showToast(res.message, { icon: "📥" });
      initProgressPage();
    } catch (err) {
      showToast("Couldn't import that file — is it a valid export?", { icon: "⚠️" });
    }
  };
  reader.readAsText(file);
}
