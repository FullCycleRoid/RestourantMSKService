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
