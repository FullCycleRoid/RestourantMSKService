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
