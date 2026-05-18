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
