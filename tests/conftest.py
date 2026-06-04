import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

import app.models
from app.core.config import settings
from app.db.base import Base


@pytest_asyncio.fixture
async def session():
    if not settings.test_database_url:
        pytest.skip("TEST_DATABASE_URL is not set")

    engine = create_async_engine(settings.test_database_url, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    connection = await engine.connect()
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
        await engine.dispose()