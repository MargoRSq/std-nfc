# std-cards backend

FastAPI + SQLAlchemy 2 async + Postgres + Alembic.

## Local dev (rye)

```bash
rye sync                                     # install deps
rye run dev-api                              # uvicorn --reload :8000
rye run dev-worker                           # NATS consumers
rye run test
rye run lint
```

## Local dev (uv, без rye)

```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
uvicorn std_cards.main:app --reload
```

## Migrations

```bash
DATABASE_URL=postgresql://std_cards:std_cards_dev@localhost:5435/std_cards \
  alembic revision --autogenerate -m "add foo"
alembic upgrade head
```
