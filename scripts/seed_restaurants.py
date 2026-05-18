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
            )
            await session.execute(stmt)

        await session.commit()

        total = (await session.execute(select(Restaurant))).scalars().all()

    print(
        f"Seed done. In DB: {len(total)} restaurants. "
        f"Skipped (rating/ring): {skipped}."
    )


if __name__ == "__main__":
    asyncio.run(run())
