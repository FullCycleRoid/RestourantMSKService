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
