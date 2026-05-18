async def test_get_garden_ring_returns_geojson(client):
    r = await client.get("/api/garden-ring")
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "Feature"
    assert body["geometry"]["type"] == "Polygon"
    assert body["properties"]["name"] == "Садовое кольцо"
    coords = body["geometry"]["coordinates"][0]
    assert len(coords) >= 4
