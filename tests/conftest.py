import pytest
import pytest_asyncio

from httpx import ASGITransport, AsyncClient

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    if not settings.test_database_url:
        pytest.skip("TEST_DATABASE_URL is not set")

    engine = create_async_engine(settings.test_database_url, poolclass=NullPool)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()

    # if not settings.test_database_url:
    #     pytest.skip("TEST_DATABASE_URL is not set")
    #
    # engine = create_async_engine(settings.test_database_url, poolclass=NullPool)
    #
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)
    #     await conn.run_sync(Base.metadata.drop_all)
    #
    # connection = await engine.connect()
    # transaction = await connection.begin()
    # db = AsyncSession(
    #     bind=connection,
    #     expire_on_commit=False,
    #     join_transaction_mode="create_savepoint",
    # )


@pytest_asyncio.fixture
async def session(test_engine):
    connection = await test_engine.connect()
    transaction = await connection.begin()
    db = AsyncSession(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield db
    finally:
        await db.close()
        if transaction.is_active:
            await transaction.rollback()
        await connection.close()


@pytest_asyncio.fixture
async def client(test_engine):
    connection = await test_engine.connect()
    transaction = await connection.begin()
    db = AsyncSession(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    async def override_get_db():
        try:
            yield db
            await db.commit()
        except Exception:
            await db.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.pop(get_db, None)
    await db.close()
    if transaction.is_active:
        await transaction.rollback()
    await connection.close()