/**
 * dashboard.js — combined "home base" view for logged-in users: XP/level,
 * streak, daily challenge, recent mistakes, and unlocked achievements.
 */
async function initDashboard() {
  let data;
  try {
    data = await Api.getDashboard();
  } catch (err) {
    showToast("Couldn't load dashboard — is the backend running?", { icon: "⚠️" });
    return;
  }

  const { user, progress, recent_mistakes, achievements, daily_challenge } = data;

  document.getElementById("welcome-name").textContent = user.display_name || user.username;
  document.getElementById("dash-level").textContent = `Level ${user.level}`;
  document.getElementById("dash-streak").textContent = `${user.current_streak} day streak 🔥`;

  const xpIntoLevel = user.xp % 200;
  document.getElementById("xp-bar-fill").style.width = `${(xpIntoLevel / 200) * 100}%`;
  document.getElementById("xp-label").textContent = `${xpIntoLevel} / 200 XP to level ${user.level + 1}`;

  document.getElementById("dash-accuracy").textContent = `${progress.accuracy}%`;
  document.getElementById("dash-mastered").textContent = `${progress.characters_mastered} / 92`;
  document.getElementById("dash-learned").textContent = `${progress.characters_learned} / 92`;

  document.getElementById("daily-challenge-desc").textContent =
    `Today's challenge: ${daily_challenge.character_count} ${daily_challenge.script} characters. Earn ${daily_challenge.reward_xp} bonus XP.`;
  document.getElementById("daily-challenge-link").href = `quiz.html?script=${daily_challenge.script}`;

  const mistakesMount = document.getElementById("dash-mistakes");
  mistakesMount.innerHTML = recent_mistakes.length
    ? recent_mistakes.map(m => `<span class="pill pill-seal">${m.character} (${m.romaji})</span>`).join(" ")
    : `<p class="text-muted">No recent mistakes — great job!</p>`;

  const achMount = document.getElementById("dash-achievements");
  achMount.innerHTML = achievements.length
    ? achievements.map(a => `
        <div class="achievement-tile">
          <div class="icon">${a.icon}</div>
          <div><strong>${a.title}</strong><br><span class="text-muted" style="font-size:0.85rem;">${a.description}</span></div>
        </div>
      `).join("")
    : `<p class="text-muted">Complete a quiz to start unlocking achievements.</p>`;
}
