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
