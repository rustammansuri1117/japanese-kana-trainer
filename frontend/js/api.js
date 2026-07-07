/**
 * api.js — thin wrapper around the Fetch API for talking to the FastAPI backend.
 * Handles the JWT token (stored in localStorage), JSON encoding/decoding, and
 * consistent error surfacing.
 */
const API_BASE_URL = window.KANA_API_BASE_URL || "http://localhost:8000";

const TOKEN_KEY = "kana_trainer_token";

const Auth = {
  getToken() { return localStorage.getItem(TOKEN_KEY); },
  setToken(token) { localStorage.setItem(TOKEN_KEY, token); },
  clearToken() { localStorage.removeItem(TOKEN_KEY); },
  isLoggedIn() { return !!localStorage.getItem(TOKEN_KEY); },
};

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function apiRequest(path, { method = "GET", body = null, auth = true, params = null } = {}) {
  let url = `${API_BASE_URL}${path}`;
  if (params) {
    const query = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== null)
    ).toString();
    if (query) url += `?${query}`;
  }

  const headers = { "Content-Type": "application/json" };
  if (auth && Auth.getToken()) {
    headers["Authorization"] = `Bearer ${Auth.getToken()}`;
  }

  let response;
  try {
    response = await fetch(url, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (err) {
    throw new ApiError("Could not reach the server. Is the backend running?", 0);
  }

  if (response.status === 401) {
    Auth.clearToken();
    if (!location.pathname.endsWith("login.html") && !location.pathname.endsWith("index.html") && location.pathname !== "/") {
      window.location.href = "login.html?expired=1";
    }
  }

  let data = null;
  const text = await response.text();
  if (text) {
    try { data = JSON.parse(text); } catch { data = text; }
  }

  if (!response.ok) {
    const message = (data && data.detail) ? (Array.isArray(data.detail) ? data.detail.map(d => d.msg).join(", ") : data.detail) : `Request failed (${response.status})`;
    throw new ApiError(message, response.status);
  }

  return data;
}

const Api = {
  register: (username, email, password, display_name) =>
    apiRequest("/auth/register", { method: "POST", body: { username, email, password, display_name }, auth: false }),
  login: (username, password) =>
    apiRequest("/auth/login", { method: "POST", body: { username, password }, auth: false }),
  logout: () => apiRequest("/auth/logout", { method: "POST" }),
  me: () => apiRequest("/auth/me"),

  updateProfile: (payload) => apiRequest("/user/profile", { method: "PUT", body: payload }),
  changePassword: (payload) => apiRequest("/user/change-password", { method: "POST", body: payload }),
  exportProgress: () => apiRequest("/user/export"),
  importProgress: (data) => apiRequest("/user/import", { method: "POST", body: data }),

  listHiragana: () => apiRequest("/hiragana", { auth: !!Auth.getToken() }),
  listKatakana: () => apiRequest("/katakana", { auth: !!Auth.getToken() }),
  getCharacter: (id) => apiRequest(`/character/${id}`, { auth: !!Auth.getToken() }),
  search: (q) => apiRequest("/search", { params: { q }, auth: !!Auth.getToken() }),
  toggleFavorite: (id) => apiRequest(`/character/${id}/favorite`, { method: "POST" }),
  toggleBookmark: (id) => apiRequest(`/character/${id}/bookmark`, { method: "POST" }),

  randomQuestion: (params) => apiRequest("/quiz/random", { params }),
  checkAnswer: (payload) => apiRequest("/quiz/check", { method: "POST", body: payload }),

  getProgress: () => apiRequest("/progress"),
  logSession: (payload) => apiRequest("/progress", { method: "POST", body: payload }),

  getMistakes: (script) => apiRequest("/mistakes", { params: { script } }),
  clearMistake: (id) => apiRequest(`/mistakes/${id}`, { method: "DELETE" }),

  getDashboard: () => apiRequest("/dashboard"),
};
