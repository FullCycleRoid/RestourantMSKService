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

The `docker compose up -d` step creates two databases via `docker/init-test-db.sql`:
`app` (for the running service) and `app_test` (for pytest). The `alembic upgrade head`
above only migrates `app`; run the migration once against the test DB too:

```
DATABASE_URL=postgresql+asyncpg://app:app@localhost:5433/app_test alembic upgrade head
pytest
```

## Endpoints

- `GET /` — index page (map + sidebar)
- `GET /api/garden-ring` — Garden Ring polygon as GeoJSON Feature
- `GET /api/restaurants` — list of restaurants inside the ring with rating ≥ 4.9
- `GET /api/user-points` — list of user-pinned points
- `POST /api/user-points` — create a point `{lat, lon, name?}`
- `DELETE /api/user-points/{id}` — delete a point

## Project layout

```
app/         FastAPI application (routers, models, geo, config)
alembic/     Database migrations
scripts/     Data seeding (static fixtures + optional Yandex geocoder)
frontend/    Static HTML/CSS/JS served at /
tests/       Pytest suite (unit + router integration)
docker/      Postgres init scripts
```
