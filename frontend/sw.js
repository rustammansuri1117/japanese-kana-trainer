/**
 * sw.js — minimal service worker that caches the static app shell so the
 * site's pages, styles, and scripts load offline. API calls to the backend
 * are NOT cached (learning data needs to be fresh / requires auth).
 */
const CACHE_NAME = "kana-trainer-shell-v1";
const SHELL_FILES = [
  "index.html", "login.html", "register.html", "dashboard.html",
  "hiragana.html", "katakana.html", "flashcards.html", "quiz.html",
  "progress.html", "profile.html",
  "css/styles.css", "css/pages.css",
  "js/api.js", "js/app.js", "js/library.js", "js/flashcards.js",
  "js/quiz.js", "js/progress.js", "js/dashboard.js", "js/profile.js",
  "manifest.json",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_FILES)).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  // Never intercept API calls — always go to network so data stays fresh.
  if (url.port === "8000" || url.pathname.startsWith("/auth") || url.pathname.startsWith("/quiz")) {
    return;
  }
  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request).catch(() => cached))
  );
});
