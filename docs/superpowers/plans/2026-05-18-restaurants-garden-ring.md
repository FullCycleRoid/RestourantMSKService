# Restaurants in Garden Ring — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Web-service that shows Moscow restaurants with rating ≥ 4.9 located inside the Garden Ring on a Yandex Map, with a left sidebar for adding custom map points by lat/lon.

**Architecture:** FastAPI (async) serves JSON API and static HTML/JS frontend. Postgres stores restaurants and user-added points. The Garden Ring polygon is loaded once into memory as a `shapely.Polygon` and used to filter restaurants and to render the contour on the map.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0 async + asyncpg, Alembic, shapely, pydantic-settings, Jinja2, pytest, Postgres 15 via docker-compose, plain HTML/CSS/JS + Yandex Maps JS API v3.

**Spec:** [`docs/superpowers/specs/2026-05-18-restaurants-garden-ring-design.md`](../specs/2026-05-18-restaurants-garden-ring-design.md)

---

## Task 0: Project scaffold

**Files:**
- Delete: `main.py` (old PyCharm stub)
- Create: `.gitignore`
- Create: `pyproject.toml`
- Create: `docker-compose.yml`
- Create: `docker/init-test-db.sql`
- Create: `.env.example`
- Create: `README.md`

- [ ] **Step 1: Initialize git**

Run from project root `/home/comp/Desktop/test-service`:
```bash
git init -b main
git config user.email "you@example.com"
git config user.name "You"
```

- [ ] **Step 2: Delete old stub**

```bash
rm main.py
```

- [ ] **Step 3: Write `.gitignore`**

```
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
env/
.env
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
dist/
build/
node_modules/
.idea/
.vscode/
*.swp
```

- [ ] **Step 4: Write `pyproject.toml`**

```toml
[project]
name = "test-service"
version = "0.1.0"
description = "Restaurants in Garden Ring on Yandex Maps"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.27",
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.29",
    "alembic>=1.13",
    "pydantic>=2.6",
    "pydantic-settings>=2.2",
    "shapely>=2.0",
    "jinja2>=3.1",
    "httpx>=0.27",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "anyio>=4.3",
]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["app*"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 5: Write `docker-compose.yml`**

```yaml
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app
      POSTGRES_DB: app
    ports:
      - "5433:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./docker/init-test-db.sql:/docker-entrypoint-initdb.d/init-test-db.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app -d app"]
      interval: 2s
      timeout: 2s
      retries: 10

volumes:
  pgdata:
```

- [ ] **Step 6: Write `docker/init-test-db.sql`**

```sql
CREATE DATABASE app_test;
GRANT ALL PRIVILEGES ON DATABASE app_test TO app;
```

- [ ] **Step 7: Write `.env.example`**

```
DATABASE_URL=postgresql+asyncpg://app:app@localhost:5433/app
TEST_DATABASE_URL=postgresql+asyncpg://app:app@localhost:5433/app_test
YANDEX_JS_API_KEY=
YANDEX_API_KEY=
```

- [ ] **Step 8: Write `README.md`**

```markdown
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
```

- [ ] **Step 9: First commit**

```bash
git add .gitignore pyproject.toml docker-compose.yml docker/init-test-db.sql .env.example README.md
git commit -m "chore: scaffold project (deps, docker-compose, gitignore)"
```

- [ ] **Step 10: Bring up Postgres and install deps**

```bash
cp .env.example .env
docker compose up -d
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .[dev]
```

Expected: `docker compose ps` shows postgres healthy.

---

## Task 1: Settings (config.py)

**Files:**
- Create: `app/__init__.py`
- Create: `app/config.py`
- Create: `tests/__init__.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Create empty package markers**

```bash
mkdir -p app tests
touch app/__init__.py tests/__init__.py
```

- [ ] **Step 2: Write failing test `tests/test_config.py`**

```python
import os

from app.config import Settings


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h:5432/d")
    monkeypatch.setenv("YANDEX_JS_API_KEY", "abc-123")
    s = Settings()
    assert s.database_url == "postgresql+asyncpg://u:p@h:5432/d"
    assert s.yandex_js_api_key == "abc-123"


def test_settings_yandex_api_key_optional(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h:5432/d")
    monkeypatch.delenv("YANDEX_API_KEY", raising=False)
    s = Settings()
    assert s.yandex_api_key is None
```

- [ ] **Step 3: Run test (expect failure)**

```bash
pytest tests/test_config.py -v
```
Expected: `ModuleNotFoundError: No module named 'app.config'`.

- [ ] **Step 4: Implement `app/config.py`**

```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    test_database_url: str | None = None
    yandex_js_api_key: str = ""
    yandex_api_key: str | None = None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 5: Run tests (expect pass)**

```bash
pytest tests/test_config.py -v
```
Expected: both tests pass.

- [ ] **Step 6: Commit**

```bash
git add app/__init__.py app/config.py tests/__init__.py tests/test_config.py
git commit -m "feat(config): pydantic-settings loader for env vars"
```

---

## Task 2: Database engine and session

**Files:**
- Create: `app/db.py`

- [ ] **Step 1: Implement `app/db.py`**

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _make_engine(url: str):
    return create_async_engine(url, future=True, pool_pre_ping=True)


_engine = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine():
    global _engine, _sessionmaker
    if _engine is None:
        _engine = _make_engine(get_settings().database_url)
        _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    get_engine()
    assert _sessionmaker is not None
    return _sessionmaker


async def get_session() -> AsyncIterator[AsyncSession]:
    async with get_sessionmaker()() as session:
        yield session


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    async with get_sessionmaker()() as session:
        yield session
```

- [ ] **Step 2: Smoke check the import**

```bash
python -c "from app.db import Base, get_engine; print('ok')"
```
Expected: `ok`.

- [ ] **Step 3: Commit**

```bash
git add app/db.py
git commit -m "feat(db): async SQLAlchemy engine, session factory, Base"
```

---

## Task 3: ORM models

**Files:**
- Create: `app/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write failing test `tests/test_models.py`**

```python
from app.models import Restaurant, UserPoint


def test_restaurant_tablename():
    assert Restaurant.__tablename__ == "restaurants"


def test_restaurant_columns():
    cols = {c.name for c in Restaurant.__table__.columns}
    assert cols == {"id", "name", "address", "rating", "lat", "lon", "yandex_id", "created_at"}


def test_user_point_tablename():
    assert UserPoint.__tablename__ == "user_points"


def test_user_point_columns():
    cols = {c.name for c in UserPoint.__table__.columns}
    assert cols == {"id", "name", "lat", "lon", "created_at"}
```

- [ ] **Step 2: Run test (expect failure)**

```bash
pytest tests/test_models.py -v
```
Expected: `ModuleNotFoundError: No module named 'app.models'`.

- [ ] **Step 3: Implement `app/models.py`**

```python
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    Identity,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Restaurant(Base):
    __tablename__ = "restaurants"
    __table_args__ = (
        CheckConstraint("rating >= 4.9", name="restaurants_rating_min"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    address: Mapped[str | None] = mapped_column(String, nullable=True)
    rating: Mapped[Decimal] = mapped_column(Numeric(2, 1), nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    yandex_id: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class UserPoint(Base):
    __tablename__ = "user_points"
    __table_args__ = (
        CheckConstraint("lat >= -90 AND lat <= 90", name="user_points_lat_range"),
        CheckConstraint("lon >= -180 AND lon <= 180", name="user_points_lon_range"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

- [ ] **Step 4: Run tests (expect pass)**

```bash
pytest tests/test_models.py -v
```
Expected: all 4 pass.

- [ ] **Step 5: Commit**

```bash
git add app/models.py tests/test_models.py
git commit -m "feat(models): Restaurant and UserPoint ORM"
```

---

## Task 4: Alembic initial migration

**Files:**
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/script.py.mako`
- Create: `alembic/versions/.gitkeep`

- [ ] **Step 1: Init alembic**

```bash
alembic init -t async alembic
```
This generates `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako`, and an empty `alembic/versions/`.

- [ ] **Step 2: Edit `alembic.ini`**

Change the `sqlalchemy.url` line so we don't hard-code a URL (we set it from env in `env.py`):
```ini
sqlalchemy.url =
```

- [ ] **Step 3: Replace `alembic/env.py`**

Overwrite the generated file with:

```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import get_settings
from app.db import Base
from app import models  # noqa: F401  (register tables)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 4: Generate the initial migration**

```bash
alembic revision --autogenerate -m "initial restaurants and user_points"
```
Expected: a new file under `alembic/versions/<hash>_initial_restaurants_and_user_points.py` with `op.create_table('restaurants', ...)` and `op.create_table('user_points', ...)`.

- [ ] **Step 5: Apply migration**

```bash
alembic upgrade head
```
Expected: `INFO ... Running upgrade -> <hash>, initial restaurants and user_points`.

- [ ] **Step 6: Apply migration to test DB**

```bash
DATABASE_URL=postgresql+asyncpg://app:app@localhost:5433/app_test alembic upgrade head
```

- [ ] **Step 7: Verify schema**

```bash
docker compose exec postgres psql -U app -d app -c '\d restaurants'
docker compose exec postgres psql -U app -d app -c '\d user_points'
```
Expected: both tables present with the listed columns and CHECK constraints.

- [ ] **Step 8: Commit**

```bash
git add alembic.ini alembic/
git commit -m "feat(alembic): async migration env + initial schema"
```

---

## Task 5: Garden Ring geometry

**Files:**
- Create: `data/garden_ring.geojson`
- Create: `app/geo.py`
- Create: `tests/test_geo.py`

- [ ] **Step 1: Write `data/garden_ring.geojson`**

Approximate clockwise polygon of the Garden Ring (15 vertices, sufficient for filtering). The implementer may refine later by exporting OSM relation 1064305.

```json
{
  "type": "Feature",
  "properties": {"name": "Садовое кольцо"},
  "geometry": {
    "type": "Polygon",
    "coordinates": [[
      [37.6478, 55.7700],
      [37.6577, 55.7677],
      [37.6597, 55.7507],
      [37.6358, 55.7376],
      [37.6093, 55.7339],
      [37.5860, 55.7345],
      [37.5825, 55.7497],
      [37.5839, 55.7616],
      [37.5895, 55.7706],
      [37.5982, 55.7733],
      [37.6066, 55.7755],
      [37.6203, 55.7745],
      [37.6312, 55.7724],
      [37.6403, 55.7710],
      [37.6478, 55.7700]
    ]]
  }
}
```

Note: GeoJSON uses `[lon, lat]` order; `shapely.Point(lon, lat)`.

- [ ] **Step 2: Write failing test `tests/test_geo.py`**

```python
import pytest

from app.geo import GardenRing


@pytest.fixture
def ring() -> GardenRing:
    return GardenRing.load_default()


def test_contains_center_of_moscow(ring: GardenRing):
    # Red Square area
    assert ring.contains(55.7539, 37.6208) is True


def test_does_not_contain_point_far_south(ring: GardenRing):
    assert ring.contains(55.6000, 37.6000) is False


def test_does_not_contain_point_far_north(ring: GardenRing):
    assert ring.contains(55.9000, 37.6000) is False


def test_contains_smolenskaya(ring: GardenRing):
    # Inside the western part of the ring
    assert ring.contains(55.7480, 37.5830) is True


def test_geojson_feature_shape(ring: GardenRing):
    feature = ring.as_geojson()
    assert feature["type"] == "Feature"
    assert feature["geometry"]["type"] == "Polygon"
    assert feature["properties"]["name"] == "Садовое кольцо"


def test_rejects_invalid_lat(ring: GardenRing):
    with pytest.raises(ValueError):
        ring.contains(200.0, 37.0)


def test_rejects_invalid_lon(ring: GardenRing):
    with pytest.raises(ValueError):
        ring.contains(55.7, 300.0)
```

- [ ] **Step 3: Run test (expect failure)**

```bash
pytest tests/test_geo.py -v
```
Expected: `ModuleNotFoundError: No module named 'app.geo'`.

- [ ] **Step 4: Implement `app/geo.py`**

```python
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shapely.geometry import Point, shape
from shapely.geometry.polygon import Polygon

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "garden_ring.geojson"


@dataclass(frozen=True)
class GardenRing:
    polygon: Polygon
    feature: dict[str, Any]

    @classmethod
    def load(cls, path: Path) -> "GardenRing":
        feature = json.loads(path.read_text(encoding="utf-8"))
        poly = shape(feature["geometry"])
        if not isinstance(poly, Polygon):
            raise ValueError("GeoJSON geometry must be a Polygon")
        return cls(polygon=poly, feature=feature)

    @classmethod
    def load_default(cls) -> "GardenRing":
        return cls.load(DEFAULT_PATH)

    def contains(self, lat: float, lon: float) -> bool:
        if not (-90.0 <= lat <= 90.0):
            raise ValueError(f"lat out of range: {lat}")
        if not (-180.0 <= lon <= 180.0):
            raise ValueError(f"lon out of range: {lon}")
        return self.polygon.contains(Point(lon, lat))

    def as_geojson(self) -> dict[str, Any]:
        return self.feature
```

- [ ] **Step 5: Run tests (expect pass)**

```bash
pytest tests/test_geo.py -v
```
Expected: all 7 tests pass.

- [ ] **Step 6: Commit**

```bash
git add data/garden_ring.geojson app/geo.py tests/test_geo.py
git commit -m "feat(geo): GardenRing polygon loader with contains() check"
```

---

## Task 6: Pydantic schemas

**Files:**
- Create: `app/schemas.py`
- Create: `tests/test_schemas.py`

- [ ] **Step 1: Write failing test `tests/test_schemas.py`**

```python
import pytest
from pydantic import ValidationError

from app.schemas import RestaurantOut, UserPointIn, UserPointOut


def test_user_point_in_accepts_valid():
    p = UserPointIn(lat=55.75, lon=37.62, name="Home")
    assert p.lat == 55.75
    assert p.lon == 37.62
    assert p.name == "Home"


def test_user_point_in_name_optional():
    p = UserPointIn(lat=55.75, lon=37.62)
    assert p.name is None


def test_user_point_in_rejects_lat_out_of_range():
    with pytest.raises(ValidationError):
        UserPointIn(lat=200, lon=37.62)


def test_user_point_in_rejects_lon_out_of_range():
    with pytest.raises(ValidationError):
        UserPointIn(lat=55.75, lon=300)


def test_user_point_in_rejects_long_name():
    with pytest.raises(ValidationError):
        UserPointIn(lat=55.75, lon=37.62, name="x" * 101)


def test_restaurant_out_serializes():
    r = RestaurantOut(
        id=1, name="X", address="addr", rating=4.9, lat=55.75, lon=37.62
    )
    assert r.model_dump()["rating"] == 4.9
```

- [ ] **Step 2: Run test (expect failure)**

```bash
pytest tests/test_schemas.py -v
```
Expected: `ModuleNotFoundError: No module named 'app.schemas'`.

- [ ] **Step 3: Implement `app/schemas.py`**

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RestaurantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    address: str | None = None
    rating: float
    lat: float
    lon: float


class UserPointIn(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    name: str | None = Field(default=None, max_length=100)


class UserPointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str | None
    lat: float
    lon: float
    created_at: datetime
```

- [ ] **Step 4: Run tests (expect pass)**

```bash
pytest tests/test_schemas.py -v
```
Expected: all 6 tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/schemas.py tests/test_schemas.py
git commit -m "feat(schemas): Pydantic input/output models"
```

---

## Task 7: FastAPI app skeleton + test infra

**Files:**
- Create: `app/main.py`
- Create: `app/routers/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/test_app.py`

- [ ] **Step 1: Create routers package**

```bash
mkdir -p app/routers
touch app/routers/__init__.py
```

- [ ] **Step 2: Write `app/main.py`**

```python
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import get_settings
from app.geo import GardenRing

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.garden_ring = GardenRing.load_default()
    app.state.jinja = Environment(
        loader=FileSystemLoader(str(FRONTEND_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Restaurants in Garden Ring", lifespan=lifespan)

    if (FRONTEND_DIR / "static").exists():
        app.mount(
            "/static",
            StaticFiles(directory=FRONTEND_DIR / "static"),
            name="static",
        )

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    async def index():
        tpl = app.state.jinja.get_template("index.html")
        html = tpl.render(yandex_js_api_key=get_settings().yandex_js_api_key)
        return HTMLResponse(html)

    # Routers registered in later tasks
    from app.routers import garden_ring, restaurants, user_points
    app.include_router(garden_ring.router, prefix="/api")
    app.include_router(restaurants.router, prefix="/api")
    app.include_router(user_points.router, prefix="/api")

    return app


app = create_app()
```

Note: `from app.routers import garden_ring, restaurants, user_points` will fail until Tasks 8-10 create those modules. That is expected — the failing test in Step 5 will surface this, and we fix it as part of Task 7 by writing minimal router stubs.

- [ ] **Step 3: Write minimal router stubs**

Create `app/routers/restaurants.py`:
```python
from fastapi import APIRouter

router = APIRouter()
```

Create `app/routers/user_points.py`:
```python
from fastapi import APIRouter

router = APIRouter()
```

Create `app/routers/garden_ring.py`:
```python
from fastapi import APIRouter

router = APIRouter()
```

Each task that follows will fill in the actual endpoints.

- [ ] **Step 4: Write `tests/conftest.py`**

```python
import os
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Force test DB before importing anything from app
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://app:app@localhost:5433/app_test",
)


from app import db as db_module  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import Restaurant, UserPoint  # noqa: E402


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
def engine():
    eng = create_async_engine(os.environ["DATABASE_URL"], future=True)
    yield eng


@pytest.fixture(scope="session")
def sessionmaker(engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def _truncate(sessionmaker):
    async with sessionmaker() as session:
        await session.execute(
            UserPoint.__table__.delete()
        )
        await session.execute(
            Restaurant.__table__.delete()
        )
        await session.commit()
    yield


@pytest.fixture
async def app_instance(engine, sessionmaker):
    # Override the global sessionmaker/engine in app.db with our test ones
    db_module._engine = engine
    db_module._sessionmaker = sessionmaker
    app = create_app()
    async with app.router.lifespan_context(app):
        yield app


@pytest.fixture
async def client(app_instance) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app_instance)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

- [ ] **Step 5: Write `tests/test_app.py`**

```python
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
```

- [ ] **Step 6: Apply migrations to test DB (one-off)**

If not already done in Task 4 Step 6:
```bash
DATABASE_URL=postgresql+asyncpg://app:app@localhost:5433/app_test alembic upgrade head
```

- [ ] **Step 7: Run tests (expect pass)**

```bash
pytest tests/test_app.py -v
```
Expected: `test_health` passes.

- [ ] **Step 8: Run all tests so far**

```bash
pytest -v
```
Expected: all tests pass.

- [ ] **Step 9: Commit**

```bash
git add app/main.py app/routers/ tests/conftest.py tests/test_app.py
git commit -m "feat(app): FastAPI skeleton with lifespan, static, jinja, test fixtures"
```

---

## Task 8: Garden Ring router

**Files:**
- Modify: `app/routers/garden_ring.py`
- Create: `tests/test_garden_ring_router.py`

- [ ] **Step 1: Write failing test `tests/test_garden_ring_router.py`**

```python
async def test_get_garden_ring_returns_geojson(client):
    r = await client.get("/api/garden-ring")
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "Feature"
    assert body["geometry"]["type"] == "Polygon"
    assert body["properties"]["name"] == "Садовое кольцо"
    coords = body["geometry"]["coordinates"][0]
    assert len(coords) >= 4
```

- [ ] **Step 2: Run test (expect failure)**

```bash
pytest tests/test_garden_ring_router.py -v
```
Expected: 404.

- [ ] **Step 3: Implement `app/routers/garden_ring.py`**

Replace its contents with:
```python
from fastapi import APIRouter, Request

router = APIRouter(tags=["garden-ring"])


@router.get("/garden-ring")
async def get_garden_ring(request: Request) -> dict:
    return request.app.state.garden_ring.as_geojson()
```

- [ ] **Step 4: Run tests (expect pass)**

```bash
pytest tests/test_garden_ring_router.py -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/routers/garden_ring.py tests/test_garden_ring_router.py
git commit -m "feat(api): GET /api/garden-ring returns polygon as GeoJSON"
```

---

## Task 9: Restaurants router

**Files:**
- Modify: `app/routers/restaurants.py`
- Create: `tests/test_restaurants_router.py`

- [ ] **Step 1: Write failing test `tests/test_restaurants_router.py`**

```python
from decimal import Decimal

from sqlalchemy import insert

from app.models import Restaurant


async def _insert(session, **kw):
    await session.execute(insert(Restaurant).values(**kw))
    await session.commit()


async def test_empty_returns_empty_list(client):
    r = await client.get("/api/restaurants")
    assert r.status_code == 200
    assert r.json() == []


async def test_returns_restaurant_inside_ring(client, sessionmaker):
    async with sessionmaker() as s:
        await _insert(
            s,
            name="Inside Place",
            address="Red Square 1",
            rating=Decimal("4.9"),
            lat=55.7539,
            lon=37.6208,
            yandex_id="inside-1",
        )

    r = await client.get("/api/restaurants")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["name"] == "Inside Place"
    assert body[0]["rating"] == 4.9


async def test_filters_out_restaurant_outside_ring(client, sessionmaker):
    async with sessionmaker() as s:
        await _insert(
            s,
            name="Far South",
            rating=Decimal("4.9"),
            lat=55.6000,
            lon=37.6000,
            yandex_id="south-1",
        )
        await _insert(
            s,
            name="Inside",
            rating=Decimal("4.9"),
            lat=55.7539,
            lon=37.6208,
            yandex_id="inside-1",
        )

    r = await client.get("/api/restaurants")
    body = r.json()
    names = [x["name"] for x in body]
    assert "Inside" in names
    assert "Far South" not in names


async def test_db_rejects_low_rating(sessionmaker):
    import pytest
    from sqlalchemy.exc import IntegrityError

    async with sessionmaker() as s:
        with pytest.raises(IntegrityError) as exc_info:
            await s.execute(
                insert(Restaurant).values(
                    name="Mediocre",
                    rating=Decimal("4.8"),
                    lat=55.75,
                    lon=37.62,
                )
            )
            await s.commit()
        assert "restaurants_rating_min" in str(exc_info.value).lower() or "rating" in str(exc_info.value).lower()
```

- [ ] **Step 2: Run test (expect failure)**

```bash
pytest tests/test_restaurants_router.py -v
```
Expected: failures (router still empty / returns 404).

- [ ] **Step 3: Implement `app/routers/restaurants.py`**

```python
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Restaurant
from app.schemas import RestaurantOut

router = APIRouter(tags=["restaurants"])


@router.get("/restaurants", response_model=list[RestaurantOut])
async def list_restaurants(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> list[RestaurantOut]:
    ring = request.app.state.garden_ring
    result = await session.execute(select(Restaurant).order_by(Restaurant.id))
    rows = result.scalars().all()
    return [
        RestaurantOut.model_validate(r)
        for r in rows
        if ring.contains(r.lat, r.lon)
    ]
```

- [ ] **Step 4: Run tests (expect pass)**

```bash
pytest tests/test_restaurants_router.py -v
```
Expected: all 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/routers/restaurants.py tests/test_restaurants_router.py
git commit -m "feat(api): GET /api/restaurants filtered by Garden Ring"
```

---

## Task 10: User points router

**Files:**
- Modify: `app/routers/user_points.py`
- Create: `tests/test_user_points_router.py`

- [ ] **Step 1: Write failing test `tests/test_user_points_router.py`**

```python
async def test_get_empty(client):
    r = await client.get("/api/user-points")
    assert r.status_code == 200
    assert r.json() == []


async def test_post_creates_point(client):
    r = await client.post(
        "/api/user-points",
        json={"lat": 55.75, "lon": 37.62, "name": "Home"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["id"] > 0
    assert body["name"] == "Home"
    assert body["lat"] == 55.75
    assert body["lon"] == 37.62
    assert "created_at" in body


async def test_post_no_name(client):
    r = await client.post("/api/user-points", json={"lat": 1.0, "lon": 2.0})
    assert r.status_code == 201
    assert r.json()["name"] is None


async def test_post_validation(client):
    r = await client.post("/api/user-points", json={"lat": 200, "lon": 37.62})
    assert r.status_code == 422

    r = await client.post("/api/user-points", json={"lat": 55, "lon": 999})
    assert r.status_code == 422

    r = await client.post(
        "/api/user-points",
        json={"lat": 55, "lon": 37, "name": "x" * 101},
    )
    assert r.status_code == 422


async def test_post_then_get(client):
    await client.post("/api/user-points", json={"lat": 1.0, "lon": 2.0, "name": "A"})
    await client.post("/api/user-points", json={"lat": 3.0, "lon": 4.0, "name": "B"})
    r = await client.get("/api/user-points")
    body = r.json()
    assert {x["name"] for x in body} == {"A", "B"}


async def test_delete(client):
    created = await client.post(
        "/api/user-points", json={"lat": 1.0, "lon": 2.0}
    )
    point_id = created.json()["id"]

    r = await client.delete(f"/api/user-points/{point_id}")
    assert r.status_code == 204

    after = await client.get("/api/user-points")
    assert after.json() == []


async def test_delete_missing(client):
    r = await client.delete("/api/user-points/99999")
    assert r.status_code == 404


async def test_point_outside_ring_is_allowed(client):
    r = await client.post(
        "/api/user-points", json={"lat": 55.6, "lon": 37.6, "name": "Outside"}
    )
    assert r.status_code == 201
```

- [ ] **Step 2: Run test (expect failure)**

```bash
pytest tests/test_user_points_router.py -v
```
Expected: failures (router empty).

- [ ] **Step 3: Implement `app/routers/user_points.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import UserPoint
from app.schemas import UserPointIn, UserPointOut

router = APIRouter(tags=["user-points"])


@router.get("/user-points", response_model=list[UserPointOut])
async def list_points(
    session: AsyncSession = Depends(get_session),
) -> list[UserPointOut]:
    result = await session.execute(select(UserPoint).order_by(UserPoint.id))
    return [UserPointOut.model_validate(p) for p in result.scalars().all()]


@router.post(
    "/user-points",
    response_model=UserPointOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_point(
    payload: UserPointIn,
    session: AsyncSession = Depends(get_session),
) -> UserPointOut:
    point = UserPoint(lat=payload.lat, lon=payload.lon, name=payload.name)
    session.add(point)
    await session.commit()
    await session.refresh(point)
    return UserPointOut.model_validate(point)


@router.delete("/user-points/{point_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_point(
    point_id: int,
    session: AsyncSession = Depends(get_session),
) -> Response:
    result = await session.execute(
        delete(UserPoint).where(UserPoint.id == point_id)
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="point not found")
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

- [ ] **Step 4: Run tests (expect pass)**

```bash
pytest tests/test_user_points_router.py -v
```
Expected: all 8 tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/routers/user_points.py tests/test_user_points_router.py
git commit -m "feat(api): user-points CRUD endpoints"
```

---

## Task 11: Seed data and seed script

**Files:**
- Create: `data/restaurants_seed.json`
- Create: `scripts/__init__.py`
- Create: `scripts/seed_restaurants.py`

- [ ] **Step 1: Write `data/restaurants_seed.json`**

Eight curated restaurants whose coordinates lie inside the Garden Ring polygon defined in Task 5. Ratings claimed as 4.9 are illustrative; refine when real data is sourced.

```json
[
  {"yandex_id": "seed-1", "name": "White Rabbit",        "address": "Смоленская пл., 3",      "rating": 4.9, "lat": 55.7480, "lon": 37.5830},
  {"yandex_id": "seed-2", "name": "Pushkin Cafe",        "address": "Тверской бул., 26а",     "rating": 4.9, "lat": 55.7655, "lon": 37.6066},
  {"yandex_id": "seed-3", "name": "Sakhalin",            "address": "Тверская, 15",           "rating": 4.9, "lat": 55.7625, "lon": 37.6080},
  {"yandex_id": "seed-4", "name": "Selfie",              "address": "Новинский б-р, 31",      "rating": 4.9, "lat": 55.7570, "lon": 37.5840},
  {"yandex_id": "seed-5", "name": "Saviva",              "address": "Б. Никитская, 7",        "rating": 4.9, "lat": 55.7570, "lon": 37.6080},
  {"yandex_id": "seed-6", "name": "Ugolek",              "address": "Б. Никитская, 12",       "rating": 4.9, "lat": 55.7572, "lon": 37.6072},
  {"yandex_id": "seed-7", "name": "Khachapuri",          "address": "Б. Грузинская, 12",      "rating": 4.9, "lat": 55.7700, "lon": 37.5870},
  {"yandex_id": "seed-8", "name": "Lavkalavka",          "address": "Петровка, 21",           "rating": 4.9, "lat": 55.7670, "lon": 37.6195}
]
```

- [ ] **Step 2: Create scripts package**

```bash
mkdir -p scripts
touch scripts/__init__.py
```

- [ ] **Step 3: Write `scripts/seed_restaurants.py`**

```python
"""Idempotent upsert of curated restaurants from data/restaurants_seed.json.

Filters: rating >= 4.9 AND inside Garden Ring polygon.
"""
from __future__ import annotations

import asyncio
import json
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.db import session_scope
from app.geo import GardenRing
from app.models import Restaurant

SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "restaurants_seed.json"


async def run() -> None:
    ring = GardenRing.load_default()
    items = json.loads(SEED_PATH.read_text(encoding="utf-8"))

    inserted = 0
    updated = 0
    skipped = 0

    async with session_scope() as session:
        for it in items:
            rating = Decimal(str(it["rating"]))
            lat = float(it["lat"])
            lon = float(it["lon"])

            if rating < Decimal("4.9"):
                skipped += 1
                continue
            if not ring.contains(lat, lon):
                skipped += 1
                continue

            stmt = (
                insert(Restaurant)
                .values(
                    name=it["name"],
                    address=it.get("address"),
                    rating=rating,
                    lat=lat,
                    lon=lon,
                    yandex_id=it["yandex_id"],
                )
                .on_conflict_do_update(
                    index_elements=["yandex_id"],
                    set_={
                        "name": it["name"],
                        "address": it.get("address"),
                        "rating": rating,
                        "lat": lat,
                        "lon": lon,
                    },
                )
                .returning(Restaurant.id, Restaurant.created_at)
            )
            res = await session.execute(stmt)
            row = res.one()
            # SQLAlchemy doesn't tell us insert-vs-update directly here;
            # count distinct rows present pre-op below.
            _ = row

        await session.commit()

        # Re-count to report totals (simpler than tracking per-row)
        total = (await session.execute(select(Restaurant))).scalars().all()

    print(
        f"Seed done. In DB: {len(total)} restaurants. "
        f"Skipped (rating/ring): {skipped}."
    )


if __name__ == "__main__":
    asyncio.run(run())
```

- [ ] **Step 4: Run seed script**

```bash
python scripts/seed_restaurants.py
```
Expected output: `Seed done. In DB: 8 restaurants. Skipped (rating/ring): 0.` (Or if any seed coords lie outside the polygon, the skipped count reflects that — adjust seed coords until 8 are in.)

- [ ] **Step 5: Verify via psql**

```bash
docker compose exec postgres psql -U app -d app -c 'SELECT id, name, rating FROM restaurants;'
```
Expected: 8 rows, each with rating 4.9.

- [ ] **Step 6: Verify via API**

```bash
uvicorn app.main:app --port 8000 &
sleep 2
curl -s http://localhost:8000/api/restaurants | python -m json.tool
kill %1
```
Expected: JSON array of 8 restaurants.

- [ ] **Step 7: Commit**

```bash
git add data/restaurants_seed.json scripts/__init__.py scripts/seed_restaurants.py
git commit -m "feat(seed): curated restaurants and idempotent seed script"
```

---

## Task 12: Optional Yandex Geosearch seed script

**Files:**
- Create: `scripts/seed_from_yandex.py`

- [ ] **Step 1: Write `scripts/seed_from_yandex.py`**

```python
"""Optional: pull restaurants from Yandex Geosearch HTTP API.

Skips silently if YANDEX_API_KEY is not set. Best-effort, no retries.
"""
from __future__ import annotations

import asyncio
import os
import sys
from decimal import Decimal

import httpx
from sqlalchemy.dialects.postgresql import insert

from app.db import session_scope
from app.geo import GardenRing
from app.models import Restaurant

GEOSEARCH_URL = "https://search-maps.yandex.ru/v1/"
GRID_STEP = 0.005  # ~500m


def _bbox_of(ring: GardenRing) -> tuple[float, float, float, float]:
    minx, miny, maxx, maxy = ring.polygon.bounds  # lon, lat
    return minx, miny, maxx, maxy


def _grid(bbox: tuple[float, float, float, float]):
    minx, miny, maxx, maxy = bbox
    x = minx
    while x < maxx:
        y = miny
        while y < maxy:
            yield (x, y, min(x + GRID_STEP, maxx), min(y + GRID_STEP, maxy))
            y += GRID_STEP
        x += GRID_STEP


async def fetch(client: httpx.AsyncClient, api_key: str, cell) -> list[dict]:
    minx, miny, maxx, maxy = cell
    params = {
        "text": "ресторан",
        "type": "biz",
        "lang": "ru_RU",
        "bbox": f"{minx},{miny}~{maxx},{maxy}",
        "results": 50,
        "apikey": api_key,
    }
    r = await client.get(GEOSEARCH_URL, params=params, timeout=10.0)
    r.raise_for_status()
    return r.json().get("features", [])


async def run() -> None:
    api_key = os.environ.get("YANDEX_API_KEY")
    if not api_key:
        print("YANDEX_API_KEY not set — skipping.")
        return

    ring = GardenRing.load_default()
    bbox = _bbox_of(ring)

    found = 0
    written = 0
    async with httpx.AsyncClient() as http, session_scope() as session:
        for cell in _grid(bbox):
            try:
                features = await fetch(http, api_key, cell)
            except httpx.HTTPError as e:
                print(f"warning: {e}", file=sys.stderr)
                continue
            for feat in features:
                props = feat.get("properties", {})
                meta = props.get("CompanyMetaData", {})
                rating = meta.get("rating")
                if rating is None:
                    continue
                if Decimal(str(rating)) < Decimal("4.9"):
                    continue
                coords = feat["geometry"]["coordinates"]
                lon, lat = float(coords[0]), float(coords[1])
                if not ring.contains(lat, lon):
                    continue

                yandex_id = meta.get("id") or props.get("name")
                stmt = (
                    insert(Restaurant)
                    .values(
                        name=meta.get("name") or props.get("name") or "?",
                        address=meta.get("address"),
                        rating=Decimal(str(rating)),
                        lat=lat,
                        lon=lon,
                        yandex_id=str(yandex_id),
                    )
                    .on_conflict_do_nothing(index_elements=["yandex_id"])
                )
                res = await session.execute(stmt)
                if res.rowcount:
                    written += 1
                found += 1
        await session.commit()

    print(f"Yandex seed: {found} candidates, {written} new rows.")


if __name__ == "__main__":
    asyncio.run(run())
```

- [ ] **Step 2: Smoke run without key (should skip)**

```bash
unset YANDEX_API_KEY
python scripts/seed_from_yandex.py
```
Expected: `YANDEX_API_KEY not set — skipping.`

- [ ] **Step 3: Commit**

```bash
git add scripts/seed_from_yandex.py
git commit -m "feat(seed): optional Yandex Geosearch importer"
```

---

## Task 13: Frontend HTML + CSS

**Files:**
- Create: `frontend/index.html`
- Create: `frontend/static/styles.css`

- [ ] **Step 1: Write `frontend/index.html`**

```html
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Рестораны 4.9 в Садовом кольце</title>
  <link rel="stylesheet" href="/static/styles.css" />
  <script src="https://api-maps.yandex.ru/v3/?apikey={{ yandex_js_api_key }}&lang=ru_RU"></script>
</head>
<body>
  <aside class="sidebar">
    <header>
      <h1>Рестораны 4.9</h1>
      <p class="subtitle">в Садовом кольце</p>
      <p class="counter">Найдено: <span id="rest-count">…</span></p>
    </header>

    <section class="form-block">
      <h2>Добавить точку</h2>
      <form id="add-point-form">
        <label>Название (опц.)
          <input type="text" name="name" maxlength="100" />
        </label>
        <label>Широта (lat)
          <input type="number" name="lat" step="0.000001" min="-90" max="90" required />
        </label>
        <label>Долгота (lon)
          <input type="number" name="lon" step="0.000001" min="-180" max="180" required />
        </label>
        <button type="submit">Добавить</button>
      </form>
    </section>

    <section class="list-block">
      <h2>Мои точки (<span id="points-count">0</span>)</h2>
      <ul id="user-points-list"></ul>
    </section>
  </aside>

  <main id="map"></main>

  <script type="module" src="/static/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Write `frontend/static/styles.css`**

```css
* { box-sizing: border-box; }
html, body { margin: 0; height: 100%; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }
body { display: flex; }

.sidebar {
  width: 320px;
  flex-shrink: 0;
  background: #f5f5f7;
  border-right: 1px solid #d0d0d5;
  padding: 16px;
  overflow-y: auto;
  height: 100vh;
}

.sidebar header h1 { margin: 0 0 4px; font-size: 18px; }
.sidebar header .subtitle { margin: 0; color: #666; font-size: 13px; }
.sidebar header .counter { margin-top: 8px; font-size: 13px; color: #444; }

.sidebar h2 { font-size: 14px; text-transform: uppercase; color: #555; margin: 24px 0 8px; letter-spacing: 0.5px; }

.form-block form { display: flex; flex-direction: column; gap: 8px; }
.form-block label { display: flex; flex-direction: column; font-size: 12px; color: #555; }
.form-block input {
  margin-top: 4px;
  padding: 6px 8px;
  font-size: 14px;
  border: 1px solid #c8c8cf;
  border-radius: 4px;
}
.form-block button {
  margin-top: 4px;
  padding: 8px;
  font-size: 14px;
  background: #2d7ff9;
  color: #fff;
  border: 0;
  border-radius: 4px;
  cursor: pointer;
}
.form-block button:hover { background: #1d6ae0; }

.list-block ul { list-style: none; padding: 0; margin: 0; }
.list-block li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 8px;
  border-radius: 4px;
  font-size: 13px;
}
.list-block li:nth-child(odd) { background: #ececef; }
.list-block li .meta { color: #777; font-size: 11px; }
.list-block li button {
  background: transparent;
  border: 0;
  color: #d23;
  cursor: pointer;
  font-size: 16px;
}

#map {
  flex: 1;
  height: 100vh;
}

#map .map-error {
  padding: 20px;
  color: #b00;
  font-weight: bold;
}
```

- [ ] **Step 3: Smoke check (template renders)**

Frontend won't work yet without `app.js`, but the template should at least render:
```bash
uvicorn app.main:app --port 8000 &
sleep 2
curl -s http://localhost:8000/ | grep -c "Рестораны 4.9"
kill %1
```
Expected: `1`.

- [ ] **Step 4: Commit**

```bash
git add frontend/index.html frontend/static/styles.css
git commit -m "feat(frontend): HTML template and stylesheet"
```

---

## Task 14: Frontend JavaScript

**Files:**
- Create: `frontend/static/app.js`

- [ ] **Step 1: Write `frontend/static/app.js`**

```javascript
const $ = (sel) => document.querySelector(sel);

const state = {
  map: null,
  restaurantsLayer: null,
  userPointsLayer: null,
  ringLayer: null,
  userPoints: new Map(), // id -> {marker, data}
};

async function fetchJSON(url, opts = {}) {
  const res = await fetch(url, opts);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {}
    throw new Error(`${res.status}: ${detail}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

async function init() {
  if (typeof ymaps3 === "undefined") {
    $("#map").innerHTML = '<div class="map-error">Карта недоступна (Yandex Maps не загрузился)</div>';
    return;
  }
  await ymaps3.ready;
  const { YMap, YMapDefaultSchemeLayer, YMapDefaultFeaturesLayer, YMapMarker, YMapFeature } = ymaps3;

  state.map = new YMap($("#map"), {
    location: { center: [37.6173, 55.7558], zoom: 12 },
  });
  state.map.addChild(new YMapDefaultSchemeLayer());
  state.map.addChild(new YMapDefaultFeaturesLayer());

  await Promise.all([loadRing(), loadRestaurants(), loadUserPoints()]);
  bindForm();
}

async function loadRing() {
  const feature = await fetchJSON("/api/garden-ring");
  const { YMapFeature } = ymaps3;
  const ringFeature = new YMapFeature({
    geometry: feature.geometry,
    style: {
      stroke: [{ color: "#ff8a00", width: 3 }],
      fill: "rgba(255, 138, 0, 0.10)",
    },
  });
  state.map.addChild(ringFeature);
  state.ringLayer = ringFeature;
}

async function loadRestaurants() {
  const items = await fetchJSON("/api/restaurants");
  $("#rest-count").textContent = items.length;
  const { YMapMarker } = ymaps3;
  for (const r of items) {
    const el = document.createElement("div");
    el.style.cssText = "width:14px;height:14px;background:#d23;border:2px solid #fff;border-radius:50%;box-shadow:0 0 3px rgba(0,0,0,0.4);cursor:pointer;";
    el.title = `${r.name} ★${r.rating}\n${r.address || ""}`;
    const m = new YMapMarker({ coordinates: [r.lon, r.lat] }, el);
    state.map.addChild(m);
  }
}

async function loadUserPoints() {
  const items = await fetchJSON("/api/user-points");
  for (const p of items) addUserPointToUI(p);
}

function addUserPointToUI(p) {
  const { YMapMarker } = ymaps3;
  const el = document.createElement("div");
  el.style.cssText = "width:18px;height:18px;background:#2d7ff9;color:#fff;font-size:12px;line-height:18px;text-align:center;border:2px solid #fff;border-radius:50%;box-shadow:0 0 3px rgba(0,0,0,0.4);cursor:pointer;";
  el.textContent = "★";
  el.title = `${p.name || "(без имени)"} ${p.lat.toFixed(5)}, ${p.lon.toFixed(5)}`;
  const marker = new YMapMarker({ coordinates: [p.lon, p.lat] }, el);
  state.map.addChild(marker);
  state.userPoints.set(p.id, { marker, data: p });
  renderUserPointsList();
}

function removeUserPointFromUI(id) {
  const entry = state.userPoints.get(id);
  if (!entry) return;
  state.map.removeChild(entry.marker);
  state.userPoints.delete(id);
  renderUserPointsList();
}

function renderUserPointsList() {
  const ul = $("#user-points-list");
  ul.innerHTML = "";
  $("#points-count").textContent = state.userPoints.size;
  for (const { data } of state.userPoints.values()) {
    const li = document.createElement("li");
    li.innerHTML = `
      <span>
        <strong>${escapeHTML(data.name || "(без имени)")}</strong><br>
        <span class="meta">${data.lat.toFixed(5)}, ${data.lon.toFixed(5)}</span>
      </span>
      <button type="button" data-id="${data.id}" title="Удалить">×</button>
    `;
    li.querySelector("button").addEventListener("click", () => deletePoint(data.id));
    ul.appendChild(li);
  }
}

function bindForm() {
  $("#add-point-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const fd = new FormData(ev.target);
    const body = {
      lat: parseFloat(fd.get("lat")),
      lon: parseFloat(fd.get("lon")),
    };
    const name = (fd.get("name") || "").trim();
    if (name) body.name = name;
    try {
      const created = await fetchJSON("/api/user-points", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body),
      });
      addUserPointToUI(created);
      ev.target.reset();
    } catch (e) {
      alert(`Не удалось добавить точку: ${e.message}`);
    }
  });
}

async function deletePoint(id) {
  try {
    await fetchJSON(`/api/user-points/${id}`, { method: "DELETE" });
    removeUserPointFromUI(id);
  } catch (e) {
    alert(`Не удалось удалить точку: ${e.message}`);
  }
}

function escapeHTML(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
}

init();
```

- [ ] **Step 2: Browser smoke check**

```bash
uvicorn app.main:app --port 8000 &
sleep 2
echo "Open http://localhost:8000 in a browser."
```
Manual verification checklist:
- Map renders, centered on Moscow
- Orange contour of Garden Ring visible
- Red markers for 8 restaurants visible inside the contour
- Sidebar shows "Найдено: 8"
- Submit form with `lat=55.75 lon=37.62 name=Test` → blue ★ marker appears, "Мои точки (1)" updates
- Reload page → blue marker persists
- Click `×` next to the point → marker disappears, list shrinks to (0)
- Submit form with `lat=200` → browser blocks (HTML5 input validation); if bypassed, alert with 422 error

When done, kill the server: `kill %1`.

- [ ] **Step 3: Commit**

```bash
git add frontend/static/app.js
git commit -m "feat(frontend): app.js renders map, restaurants, ring, user points CRUD"
```

---

## Task 15: Full test sweep and final commit

- [ ] **Step 1: Truncate test DB and run the full suite**

```bash
pytest -v
```
Expected: all tests pass (config 2, models 4, geo 7, schemas 6, app 1, garden-ring 1, restaurants 4, user-points 8 = 33 tests).

- [ ] **Step 2: End-to-end manual check**

```bash
uvicorn app.main:app --port 8000 --reload
```
Open http://localhost:8000 and walk through the spec's §15 acceptance criteria.

- [ ] **Step 3: Update README with the final commands (if anything drifted)**

Verify `README.md` quick-start is accurate. If anything changed (e.g. test DB setup, extra env vars), update.

- [ ] **Step 4: Final commit if README changed**

```bash
git status
# if README modified:
git add README.md
git commit -m "docs: align README with final commands"
```

- [ ] **Step 5: Done**

Print a summary in the conversation:
- Number of tasks completed
- Number of commits
- URL to open: http://localhost:8000
