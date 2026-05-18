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
