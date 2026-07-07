# Backend — Japanese Kana Trainer API

FastAPI + SQLAlchemy + SQLite backend. See the project root `README.md` for
the full setup guide, API reference, and deployment notes. Quick start:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Docs: `http://localhost:8000/docs`
