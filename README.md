# Restaurants in Garden Ring

Service that shows Moscow restaurants with rating ≥ 4.9 inside the Garden Ring on a Yandex Map. Left sidebar lets you pin custom points by lat/lon.

## Quick start

```
cp .env.example .env       # fill in YANDEX_JS_API_KEY
docker compose up -d
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev]
alembic upgrade head
python scripts/seed_restaurants.py
uvicorn app.main:app --reload
```

Open http://localhost:8000

## Tests

```
pytest
```
