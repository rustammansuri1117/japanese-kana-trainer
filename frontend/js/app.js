/**
 * app.js — shared behavior across every page: navbar rendering, dark/light
 * theme toggle (persisted to localStorage), toast notifications, small sound
 * effects (WebAudio, no external files needed), and a confetti burst used on
 * level-ups / achievements / daily-challenge completion.
 */

/* ---------------------------- Theme ------------------------------------ */
const Theme = {
  KEY: "kana_trainer_theme",
  init() {
    const saved = localStorage.getItem(this.KEY) ||
      (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    document.documentElement.setAttribute("data-theme", saved);
  },
  toggle() {
    const current = document.documentElement.getAttribute("data-theme");
    const next = current === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem(this.KEY, next);
    const btn = document.getElementById("theme-toggle-btn");
    if (btn) btn.textContent = next === "dark" ? "☀️" : "🌙";
  },
};
Theme.init();

/* ---------------------------- Navbar ------------------------------------ */
const NAV_ITEMS = [
  { href: "index.html", label: "Home" },
  { href: "hiragana.html", label: "Hiragana" },
  { href: "katakana.html", label: "Katakana" },
  { href: "flashcards.html", label: "Flashcards" },
  { href: "quiz.html", label: "Quiz" },
  { href: "progress.html", label: "Progress" },
];

function renderNavbar() {
  const mount = document.getElementById("navbar-mount");
  if (!mount) return;
  const currentPage = location.pathname.split("/").pop() || "index.html";
  const loggedIn = Auth.isLoggedIn();
  const theme = document.documentElement.getAttribute("data-theme");

  const links = NAV_ITEMS.map(item =>
    `<a href="${item.href}" class="${item.href === currentPage ? "active" : ""}">${item.label}</a>`
  ).join("");

  const authLinks = loggedIn
    ? `<a href="dashboard.html" class="${currentPage === "dashboard.html" ? "active" : ""}">Dashboard</a>
       <a href="profile.html" class="${currentPage === "profile.html" ? "active" : ""}">Profile</a>
       <button class="nav-link" id="logout-btn">Logout</button>`
    : `<a href="login.html" class="${currentPage === "login.html" ? "active" : ""}">Login</a>
       <a href="register.html" class="btn btn-seal btn-sm">Register</a>`;

  mount.innerHTML = `
    <nav class="navbar">
      <div class="container">
        <a href="index.html" class="nav-brand">
          <span class="hanko-mark">仮</span> Kana Trainer
        </a>
        <div class="nav-links desktop-only">
          ${links}
          ${authLinks}
          <button class="nav-toggle-theme" id="theme-toggle-btn" aria-label="Toggle dark mode">${theme === "dark" ? "☀️" : "🌙"}</button>
        </div>
        <button class="nav-toggle-theme nav-mobile-toggle" id="mobile-nav-btn" aria-label="Menu">☰</button>
      </div>
    </nav>
    <div id="mobile-nav-panel" class="hidden" style="position:fixed; top:64px; left:0; right:0; background:var(--paper-raised); border-bottom:1px solid var(--paper-line); z-index:99; padding:16px 24px; display:flex; flex-direction:column; gap:4px;">
      ${links}${authLinks}
    </div>
  `;

  document.getElementById("theme-toggle-btn").addEventListener("click", Theme.toggle);
  const mobileBtn = document.getElementById("mobile-nav-btn");
  const mobilePanel = document.getElementById("mobile-nav-panel");
  mobileBtn.addEventListener("click", () => mobilePanel.classList.toggle("hidden"));

  const logoutBtn = document.getElementById("logout-btn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
      try { await Api.logout(); } catch (e) { /* stateless JWT, ignore errors */ }
      Auth.clearToken();
      window.location.href = "index.html";
    });
  }
}

/* ---------------------------- Toasts ------------------------------------ */
function ensureToastWrap() {
  let wrap = document.querySelector(".toast-wrap");
  if (!wrap) {
    wrap = document.createElement("div");
    wrap.className = "toast-wrap";
    document.body.appendChild(wrap);
  }
  return wrap;
}
function showToast(message, { icon = "📌", duration = 3200 } = {}) {
  const wrap = ensureToastWrap();
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
  wrap.appendChild(toast);
  setTimeout(() => toast.remove(), duration);
}

/* ---------------------------- Sound effects (WebAudio, no files) -------- */
const Sound = {
  ctx: null,
  enabled() { return localStorage.getItem("kana_trainer_sound") !== "off"; },
  toggle() {
    const next = this.enabled() ? "off" : "on";
    localStorage.setItem("kana_trainer_sound", next);
    return next === "on";
  },
  _ensureCtx() {
    if (!this.ctx) this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    return this.ctx;
  },
  _blip(freq, duration, type = "sine", gainValue = 0.08) {
    if (!this.enabled()) return;
    try {
      const ctx = this._ensureCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = type;
      osc.frequency.value = freq;
      gain.gain.value = gainValue;
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + duration);
      osc.stop(ctx.currentTime + duration);
    } catch (e) { /* audio not available */ }
  },
  correct() { this._blip(880, 0.18, "triangle"); setTimeout(() => this._blip(1320, 0.18, "triangle"), 90); },
  wrong() { this._blip(160, 0.28, "sawtooth", 0.06); },
  click() { this._blip(600, 0.05, "square", 0.03); },
  levelUp() { [660, 880, 1100, 1320].forEach((f, i) => setTimeout(() => this._blip(f, 0.22, "triangle"), i * 100)); },
};

/* ---------------------------- Confetti ----------------------------------- */
function fireConfetti() {
  const colors = ["#BE3A34", "#1D3354", "#A9822E", "#3C6E47"];
  const container = document.createElement("div");
  container.style.cssText = "position:fixed; inset:0; pointer-events:none; z-index:400; overflow:hidden;";
  document.body.appendChild(container);
  for (let i = 0; i < 60; i++) {
    const piece = document.createElement("div");
    const size = 6 + Math.random() * 6;
    piece.style.cssText = `
      position:absolute; top:-20px; left:${Math.random() * 100}%;
      width:${size}px; height:${size * 0.5}px; background:${colors[i % colors.length]};
      opacity:${0.7 + Math.random() * 0.3};
      transform: rotate(${Math.random() * 360}deg);
      border-radius: 1px;
    `;
    container.appendChild(piece);
    const duration = 1800 + Math.random() * 1400;
    const drift = (Math.random() - 0.5) * 200;
    piece.animate(
      [
        { transform: `translate(0, 0) rotate(0deg)`, opacity: 1 },
        { transform: `translate(${drift}px, ${window.innerHeight + 40}px) rotate(${360 + Math.random() * 360}deg)`, opacity: 0.2 },
      ],
      { duration, easing: "cubic-bezier(.3,.6,.5,1)", fill: "forwards" }
    );
  }
  setTimeout(() => container.remove(), 3400);
}

/* ---------------------------- Auth guard --------------------------------- */
function requireAuth() {
  if (!Auth.isLoggedIn()) {
    window.location.href = "login.html?redirect=" + encodeURIComponent(location.pathname.split("/").pop());
  }
}

/* ---------------------------- Mastery helpers ---------------------------- */
function masteryClass(score) {
  if (score === null || score === undefined) return "";
  if (score >= 90) return "high";
  if (score >= 40) return "mid";
  if (score > 0) return "low";
  return "";
}

document.addEventListener("DOMContentLoaded", renderNavbar);

/* ---------------------------- PWA / offline shell ------------------------ */
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("sw.js").catch(() => {});
  });
}
