import os
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Force test DB before importing anything from app
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://app:app@localhost:5433/app_test",
)


from app import db as db_module  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import Restaurant, UserPoint  # noqa: E402


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
def engine():
    eng = create_async_engine(os.environ["DATABASE_URL"], future=True)
    yield eng


@pytest.fixture(scope="session")
def sessionmaker(engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def _truncate(sessionmaker):
    async with sessionmaker() as session:
        await session.execute(
            UserPoint.__table__.delete()
        )
        await session.execute(
            Restaurant.__table__.delete()
        )
        await session.commit()
    yield


@pytest.fixture
async def app_instance(engine, sessionmaker):
    # Override the global sessionmaker/engine in app.db with our test ones
    db_module._engine = engine
    db_module._sessionmaker = sessionmaker
    app = create_app()
    async with app.router.lifespan_context(app):
        yield app


@pytest.fixture
async def client(app_instance) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app_instance)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
