# Restaurants in Garden Ring — Design Spec

**Date:** 2026-05-18
**Status:** Approved
**Owner:** andrewthechf@gmail.com

## 1. Цель

Веб-сервис, который на Яндекс-карте показывает все рестораны с рейтингом ≥ 4.9, находящиеся внутри Садового кольца Москвы. В левом сайдбаре пользователь может добавить произвольную точку на карту по широте и долготе; точки сохраняются в БД и отображаются маркерами.

## 2. Технологический стек

| Слой | Выбор |
|---|---|
| Backend | FastAPI (Python 3.11+), uvicorn |
| ORM / драйвер | SQLAlchemy 2.0 (async) + asyncpg |
| Миграции | Alembic |
| БД | PostgreSQL 15 |
| Геометрия | shapely (point-in-polygon в памяти) |
| Frontend | HTML + ванильный JS + Yandex Maps JS API v3 |
| Конфиг | pydantic-settings, .env |
| Тесты | pytest + httpx.AsyncClient |
| Локальная среда | docker-compose (только postgres) |

PostGIS не используется: полигон Садового кольца один, ресторанов десятки/сотни — геометрия в памяти на Python проще и быстрее по времени разработки.

## 3. Архитектура

```
Browser (index.html + app.js + Yandex Maps v3)
        │  JSON over HTTP
        ▼
FastAPI (uvicorn) ── shapely-полигон Садового кольца в памяти
        │  SQLAlchemy async
        ▼
Postgres 15  (таблицы restaurants, user_points)
```

Garden Ring грузится один раз из `data/garden_ring.geojson` в FastAPI lifespan, держится в памяти как `shapely.Polygon`. Используется:
- сервером — фильтр на выдаче `/api/restaurants` (страховка от мусора в БД);
- сервером — фильтр при сидинге;
- клиентом — рендеринг контура (отдаётся через `/api/garden-ring`).

## 4. Структура репозитория

```
test-service/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, static mount, lifespan
│   ├── config.py            # pydantic-settings
│   ├── db.py                # async engine, session, Base
│   ├── models.py            # ORM: Restaurant, UserPoint
│   ├── schemas.py           # Pydantic: входные/выходные модели
│   ├── geo.py               # GardenRing: load + contains(lat, lon)
│   └── routers/
│       ├── __init__.py
│       ├── restaurants.py
│       ├── user_points.py
│       └── garden_ring.py
├── data/
│   ├── garden_ring.geojson      # Полигон Садового кольца (OSM relation 1064305)
│   └── restaurants_seed.json    # ~20 курированных ресторанов 4.9
├── scripts/
│   ├── seed_restaurants.py      # upsert seed.json в БД
│   └── seed_from_yandex.py      # опц.: тянет из Yandex Geosearch API
├── frontend/
│   ├── index.html               # Jinja2-шаблон (вставляется YANDEX_JS_API_KEY)
│   └── static/
│       ├── app.js
│       └── styles.css
├── alembic/
│   ├── env.py
│   └── versions/
├── tests/
│   ├── conftest.py
│   ├── test_geo.py
│   ├── test_restaurants.py
│   └── test_user_points.py
├── alembic.ini
├── docker-compose.yml           # postgres:15
├── pyproject.toml
├── .env.example
└── README.md
```

Старый stub `main.py` в корне удаляется.

## 5. Модель данных

### Таблица `restaurants`

| col | type | constraint |
|---|---|---|
| id | SERIAL PK | |
| name | TEXT | NOT NULL |
| address | TEXT | nullable |
| rating | NUMERIC(2,1) | NOT NULL, CHECK (rating >= 4.9) |
| lat | DOUBLE PRECISION | NOT NULL |
| lon | DOUBLE PRECISION | NOT NULL |
| yandex_id | TEXT | UNIQUE, nullable |
| created_at | TIMESTAMPTZ | DEFAULT now() |

### Таблица `user_points`

| col | type | constraint |
|---|---|---|
| id | SERIAL PK | |
| name | TEXT | nullable, ≤ 100 chars (валидация Pydantic) |
| lat | DOUBLE PRECISION | NOT NULL, CHECK (-90 <= lat <= 90) |
| lon | DOUBLE PRECISION | NOT NULL, CHECK (-180 <= lon <= 180) |
| created_at | TIMESTAMPTZ | DEFAULT now() |

PostGIS-типы не используются. Координаты хранятся как `DOUBLE PRECISION`.

## 6. API

Все JSON-эндпоинты под префиксом `/api`. Ошибки возвращаются как `{"detail": "..."}` с подходящим HTTP-кодом. Валидация — через Pydantic-схемы (`422` на невалидный body).

### `GET /api/restaurants` → 200

Возвращает все рестораны с `rating >= 4.9`, попадающие внутрь полигона Садового кольца.
```json
[
  {
    "id": 1,
    "name": "White Rabbit",
    "address": "Смоленская пл., 3",
    "rating": 4.9,
    "lat": 55.7480,
    "lon": 37.5830
  }
]
```

### `GET /api/garden-ring` → 200

GeoJSON `Feature` с полигоном Садового кольца (для отрисовки на карте).
```json
{"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[[lon,lat],...]]}, "properties": {"name": "Садовое кольцо"}}
```

### `GET /api/user-points` → 200

```json
[{"id": 1, "name": "Home", "lat": 55.75, "lon": 37.62, "created_at": "2026-05-18T12:34:56Z"}]
```

### `POST /api/user-points` → 201

Тело:
```json
{"lat": 55.75, "lon": 37.62, "name": "Home"}
```
Ответ: созданная запись со всеми полями.

Валидация: `-90 ≤ lat ≤ 90`, `-180 ≤ lon ≤ 180`, `name` опционально (≤ 100 символов). Точка может быть **вне** Садового кольца — это пользовательская точка, не ресторан.

### `DELETE /api/user-points/{id}` → 204 или 404

### Статика

- `GET /` → `frontend/index.html` (рендерится Jinja2 с переменной `yandex_js_api_key`)
- `GET /static/*` → `frontend/static/*`

## 7. Frontend

Один экран, flex-лейаут: `aside.sidebar` шириной 320px + `main.map` (flex: 1).

**Sidebar:**
- Заголовок "Рестораны 4.9 в Садовом кольце" + счётчик
- Форма «Добавить точку»: `name` (опц.), `lat`, `lon`, кнопка «Добавить»
- Список «Мои точки»: имя/координаты + кнопка `×` (удалить)

**Map:**
- Yandex Maps JS API v3, центр `(55.7558, 37.6173)`, zoom 12
- Полигон Садового кольца — полупрозрачный оранжевый
- Маркеры ресторанов — красные, balloon: `name + rating ★ + address`
- Маркеры пользовательских точек — синие со звёздочкой, balloon: `name + lat,lon`

**Flow:**
1. На загрузке: параллельно `GET /api/restaurants`, `/api/garden-ring`, `/api/user-points` → отрисовать
2. На сабмит формы: `POST /api/user-points` → добавить маркер и строку
3. На клик `×`: `DELETE /api/user-points/{id}` → убрать маркер и строку
4. На ошибку запроса: `alert(...)` с сообщением

Без фреймворков. Без бандлера. Один `app.js` (≤ 200 строк ожидается).

## 8. Загрузка данных (seed)

### `data/restaurants_seed.json`

Курированный список ~20 ресторанов Москвы с рейтингом 4.9, внутри Садового кольца. Формат:
```json
[
  {
    "yandex_id": "1234567890",
    "name": "White Rabbit",
    "address": "Смоленская пл., 3",
    "rating": 4.9,
    "lat": 55.7480,
    "lon": 37.5830
  }
]
```

### `scripts/seed_restaurants.py`

1. Парсит JSON
2. Грузит `garden_ring.geojson`
3. Для каждой записи: проверяет `rating >= 4.9` и `polygon.contains(Point(lon, lat))`
4. `INSERT ... ON CONFLICT (yandex_id) DO UPDATE` (upsert)
5. Лог: сколько добавлено / обновлено / отфильтровано

### `scripts/seed_from_yandex.py` (опционально)

Запускается, только если задан `YANDEX_API_KEY`. Делит bbox Садового кольца на сетку 0.005°×0.005°, по каждой ячейке вызывает `https://search-maps.yandex.ru/v1/?text=ресторан&type=biz&bbox=...&results=50&apikey=...`, отбирает по `properties.CompanyMetaData.rating >= 4.9`, дедупит по `yandex_id`, делает `ON CONFLICT DO NOTHING`. Если ключа нет — скрипт печатает «skip» и завершает с кодом 0.

## 9. Конфигурация

`.env.example`:
```
DATABASE_URL=postgresql+asyncpg://app:app@localhost:5432/app
YANDEX_JS_API_KEY=    # ключ для JS API v3 (фронт)
YANDEX_API_KEY=       # ключ для Geosearch HTTP API (опц., только сидинг)
```

`app/config.py` — `Settings` через `pydantic-settings`.

## 10. Обработка ошибок

- Pydantic-схемы валидируют входные данные → FastAPI отдаёт 422
- `404` при удалении/чтении несуществующей `user_points`
- Глобальный exception handler возвращает `{"detail": "Internal error"}` с 500
- Фронт: на любой не-2xx ответ показывает `alert()` (для теста достаточно)
- Если Yandex Maps JS не загрузился — в `<div id="map">` пишется текст «Карта недоступна»

## 11. Тестирование

`pytest` + `httpx.AsyncClient(ASGITransport(app))`.

**Фикстуры (`conftest.py`):**
- engine на отдельную тестовую БД (`app_test`), создаваемую через docker-compose
- `TRUNCATE restaurants, user_points RESTART IDENTITY CASCADE` перед каждым тестом
- httpx async client против ASGI

**`test_geo.py`**
- Точка `(55.7558, 37.6173)` (центр Москвы) — внутри
- Точка `(55.6, 37.6)` (южнее МКАД ну явно вне) — вне
- Точка `(55.9, 37.6)` — вне
- Невалидные lat/lon — `ValueError`

**`test_restaurants.py`**
- Вставляем один валидный ресторан внутри Садового кольца → `GET /api/restaurants` возвращает 1 запись с этим именем
- Вставляем ресторан с координатами вне Садового кольца → `GET /api/restaurants` его НЕ возвращает (фильтрация полигоном на выдаче)
- Прямой INSERT в БД ресторана с рейтингом 4.8 → падает по CHECK-констрейнту `rating >= 4.9`

**`test_user_points.py`**
- POST с валидными данными → 201, появляется в GET
- POST с `lat=200` → 422
- DELETE существующего → 204, исчезает из GET
- DELETE несуществующего → 404

Фронт — smoke вручную через браузер.

## 12. Локальный запуск

```
cp .env.example .env       # вписать YANDEX_JS_API_KEY
docker compose up -d postgres
pip install -e .[dev]
alembic upgrade head
python scripts/seed_restaurants.py
uvicorn app.main:app --reload
# открыть http://localhost:8000
```

## 13. Вне scope (YAGNI)

- Аутентификация / пользователи
- PostGIS, спатиальные индексы
- Кластеризация маркеров (включить, если ресторанов окажется > 100)
- WebSocket / real-time
- CI/CD конфиги
- localStorage / клиентский кэш
- Кеширование на сервере
- Поиск, фильтры, пагинация
- i18n
- Production-grade обработка ошибок Yandex API (retries, backoff) в seed-скрипте

## 14. Открытые/отложенные вопросы

- Финальный список 20 ресторанов в seed.json подбирается на этапе реализации (вручную из открытых источников)
- Точные координаты полигона Садового кольца — экспортируются один раз из OSM и коммитятся как файл

## 15. Критерии готовности

- `docker compose up -d` + миграции + сидинг → сервис стартует
- Открытие `http://localhost:8000` показывает карту, оранжевый контур Садового кольца, красные маркеры ресторанов
- Через форму в сайдбаре добавляется точка `(55.75, 37.62)` → синий маркер на карте + строка в списке
- Перезагрузка страницы — точка остаётся (хранится в БД)
- Удаление точки → маркер и строка исчезают
- `pytest` зелёный
