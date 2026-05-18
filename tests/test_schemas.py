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
