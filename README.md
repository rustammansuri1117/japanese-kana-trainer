# Japanese Kana Trainer

A full-stack web app for learning Hiragana and Katakana — flashcards, six quiz
modes, spaced repetition, mistake review, XP/levels/streaks/achievements, and
full progress tracking. Built to be extended with Kanji later without
restructuring anything.

**Stack:** FastAPI + SQLAlchemy + SQLite (backend), vanilla HTML/CSS/JS (frontend, no framework, no build step).

---

## 1. Project structure

```
japanese-kana-trainer/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app, CORS, router registration
│   │   ├── database.py        # SQLAlchemy engine/session setup
│   │   ├── models.py          # ORM models (Users, Characters progress, Quiz history, Mistakes, Sessions, Achievements)
│   │   ├── schemas.py         # Pydantic request/response models
│   │   ├── auth.py            # Password hashing + JWT
│   │   ├── routes/            # One router per feature area
│   │   ├── services/          # Business logic: SRS, gamification, stats
│   │   ├── utils/             # data_loader.py — loads kana JSON into memory
│   │   └── data/              # hiragana.json, katakana.json (46 characters each)
│   ├── alembic/                # DB migrations
│   ├── requirements.txt
│   └── .env.example
│
└── frontend/
    ├── index.html, login.html, register.html, dashboard.html
    ├── hiragana.html, katakana.html, flashcards.html, quiz.html
    ├── progress.html, profile.html
    ├── css/ (styles.css — design system, pages.css — page-specific)
    ├── js/  (api.js, app.js, + one file per page)
    ├── manifest.json, sw.js   # PWA / offline shell support
    └── images/, audio/         # (audio pronunciation is generated in-browser via Web Speech API — no files needed)
```

---

## 2. Backend setup

### Requirements
- Python 3.12+

### Steps

```bash
cd backend

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy the env file and (optionally) edit it — a JWT secret is required for production
cp .env.example .env

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn app.main:app --reload --port 8000
```

The API is now running at `http://localhost:8000`. Interactive docs (Swagger UI)
are auto-generated at `http://localhost:8000/docs`.

> **Note:** the app also auto-creates tables on startup via `init_db()` as a
> convenience for first-time runs, but `alembic upgrade head` is the correct,
> repeatable way to manage schema changes going forward. If you change
> `models.py`, generate a new revision with:
> `alembic revision --autogenerate -m "describe your change"` then `alembic upgrade head`.

### Environment variables

| Variable         | Default                          | Purpose                                  |
|-------------------|-----------------------------------|-------------------------------------------|
| `DATABASE_URL`    | `sqlite:///./kana_trainer.db`     | Any SQLAlchemy-compatible connection string |
| `JWT_SECRET_KEY`  | insecure dev default              | **Must** be changed in production          |

---

## 3. Frontend setup

No build step, no npm install — it's plain HTML/CSS/JS.

### Steps

```bash
cd frontend

# Serve the folder with any static file server, e.g.:
python3 -m http.server 5500
```

Then open `http://localhost:5500` in your browser.

### Pointing the frontend at a non-default backend URL

By default the frontend calls the API at `http://localhost:8000`
(see `js/api.js`). To point it elsewhere (e.g. a deployed backend), add this
one line **before** the `<script src="js/api.js">` tag on every page:

```html
<script>window.KANA_API_BASE_URL = "https://your-backend-domain.com";</script>
```

---

## 4. Project features at a glance

- **Auth:** register / login / logout (JWT), edit profile, change password
- **Learning:** full Hiragana + Katakana tables (46 + 46), searchable, each
  with stroke count, writing tips, memory tips, an example word, and
  in-browser audio pronunciation (Web Speech API, `ja-JP` voice)
- **Flashcards:** flip animation, shuffle, previous/next, keyboard shortcuts
- **Quiz:** 6 modes — Character→Romaji, Romaji→Character (multiple choice),
  Multiple Choice, Timed (5/10/15/unlimited seconds), Mixed Modes, and Review
  Mistakes — with instant "hanko stamp" ✅ / brush-stroke ❌ feedback
- **Spaced repetition:** a simplified SM-2-style algorithm drives which
  characters show up most; mastery score per character, per user
- **Mistake review:** every wrong answer is logged and can be drilled
  separately, split by script
- **Progress dashboard:** accuracy, streaks, response time, characters
  learned/mastered, daily practice chart, XP/level, achievements
- **Gamification:** XP, levels, daily streaks, 10 unlockable achievements,
  a deterministic daily challenge, confetti + sound effects on level-up
- **Import/Export:** download your progress as JSON, restore it later
- **PWA:** installable, works offline for the app shell (`manifest.json` + `sw.js`)
- **Dark / light themes:** washi-paper light theme, sumi-ink dark theme,
  persisted per-user and locally

---

## 5. API reference (summary)

Full interactive docs live at `/docs` once the server is running. Summary:

| Method | Path                          | Description                          |
|--------|-------------------------------|----------------------------------------|
| POST   | `/auth/register`              | Create an account, returns a JWT       |
| POST   | `/auth/login`                 | Log in, returns a JWT                  |
| POST   | `/auth/logout`                | Stateless logout (client discards JWT) |
| GET    | `/auth/me`                    | Current user info                      |
| GET    | `/user/profile`, PUT `/user/profile` | View/edit profile                |
| POST   | `/user/change-password`       | Change password                        |
| GET    | `/user/export`, POST `/user/import` | Backup / restore progress        |
| GET    | `/hiragana`, `/katakana`      | List all characters (enriched if logged in) |
| GET    | `/character/{id}`             | Single character lesson                |
| GET    | `/search?q=`                  | Search by character/romaji/word/meaning|
| POST   | `/character/{id}/favorite`    | Toggle favorite                        |
| POST   | `/character/{id}/bookmark`    | Toggle bookmark                        |
| GET    | `/quiz/random`                | Get next question (see query params below) |
| POST   | `/quiz/check`                 | Submit an answer                       |
| GET    | `/progress`, POST `/progress` | View / log progress                    |
| GET    | `/mistakes`                   | List unresolved mistakes                |
| DELETE | `/mistakes/{id}`              | Mark a mistake resolved                 |
| GET    | `/dashboard`                  | Combined dashboard payload              |

`GET /quiz/random` query params: `script` (hiragana/katakana/mixed),
`quiz_type` (char_to_romaji/romaji_to_char/multiple_choice/timed/mixed),
`review_mistakes` (bool), `timer_seconds` (5/10/15/omit).

---

## 6. Deployment notes

- **Backend:** any ASGI host works (Render, Railway, Fly.io, a VM with
  gunicorn+uvicorn workers, etc). Set `DATABASE_URL` to a real Postgres
  instance and `JWT_SECRET_KEY` to a long random value. Restrict
  `allow_origins` in `app/main.py` to your real frontend domain(s) instead of `"*"`.
- **Frontend:** it's static — deploy to Netlify, Vercel, GitHub Pages, S3 +
  CloudFront, or any static host. Just remember to set `window.KANA_API_BASE_URL`
  to your deployed backend's URL (see section 3).
- **Database:** SQLite is fine for local dev and small deployments; swap
  `DATABASE_URL` for Postgres/MySQL for anything with concurrent writers.

---

## 7. Future improvements

- Kanji support (the data loader and models were designed so a `kanji.json`
  + a new script value is enough — no schema changes needed)
- Real recorded native-speaker audio instead of the browser's speech synthesis
  (drop files into `frontend/audio/` and swap the `speak()` call in `library.js`)
- Native stroke-order animation (currently a static practice grid + written
  writing tips; an SVG stroke-order animation library could be layered in)
- A study calendar heatmap (the data — `daily_practice` — is already tracked;
  this is a rendering addition on the Progress page)
- Push notifications for daily-streak reminders (would need a backend job +
  the Push API, on top of the existing PWA service worker)
- Social/leaderboard features (would need a new `leaderboard` read model)

---

## 8. Code quality notes

- Backend follows a layered architecture: **routes** (HTTP concerns only) →
  **services** (business logic: SRS, gamification, stats aggregation) →
  **models** (persistence). Character data is loaded from JSON once and
  cached in memory (`utils/data_loader.py`) rather than re-queried per request.
- All request/response shapes are validated with Pydantic; all DB models
  use SQLAlchemy's typed `Column` declarations.
- The frontend has zero external JS dependencies — `api.js` centralizes all
  network calls and error handling so page scripts stay declarative.
