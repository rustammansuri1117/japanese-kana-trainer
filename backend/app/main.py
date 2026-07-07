"""
Japanese Kana Trainer — FastAPI application entry point.

Run with:
    uvicorn app.main:app --reload --port 8000
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routes import (
    auth_routes,
    user_routes,
    learning_routes,
    quiz_routes,
    progress_routes,
    mistakes_routes,
    dashboard_routes,
)

app = FastAPI(
    title="Japanese Kana Trainer API",
    description="Backend API for learning Hiragana and Katakana — flashcards, quizzes, spaced repetition, and progress tracking.",
    version="1.0.0",
)

# CORS: wide-open by default for local development. Restrict allow_origins
# to your real frontend domain(s) before deploying to production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


app.include_router(auth_routes.router)
app.include_router(user_routes.router)
app.include_router(learning_routes.router)
app.include_router(quiz_routes.router)
app.include_router(progress_routes.router)
app.include_router(mistakes_routes.router)
app.include_router(dashboard_routes.router)


@app.get("/", tags=["Health"])
def root():
    return {
        "message": "Japanese Kana Trainer API is running",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}
