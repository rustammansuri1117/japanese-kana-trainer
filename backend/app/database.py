"""
Database configuration for the Japanese Kana Trainer application.

Uses SQLAlchemy with SQLite by default. The DATABASE_URL can be overridden
via an environment variable to point at any SQLAlchemy-compatible database
(e.g. PostgreSQL in production).
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./kana_trainer.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# check_same_thread is only needed for SQLite
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a database session and ensures it is closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. Called once on application startup."""
    # Import models here so they are registered on Base.metadata before create_all
    from app import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
