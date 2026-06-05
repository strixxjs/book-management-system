import asyncio
import pytest

from sqlalchemy.ext.asyncio import AsyncSession
from app.models.author import Author
from app.repositories.author import AuthorRepository

pytestmark = pytest.mark.asyncio


async def test_get_or_create_creates_new_author(session):
    repo = AuthorRepository(session)
    author = await repo.get_or_create("George Orwell")
    assert author.id is not None
    assert author.name == "George Orwell"


async def test_get_or_create_returns_existing_author_without_error(session):
    existing = Author(name="George Orwell")
    session.add(existing)
    await session.flush()

    repo = AuthorRepository(session)
    result = await repo.get_or_create("George Orwell")

    assert result.id == existing.id


@pytest.mark.asyncio
async def test_get_or_create_is_concurrent_safe(test_engine):
    async def create_author():
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            repo = AuthorRepository(session)
            author = await repo.get_or_create("Concurrent Author")
            await session.commit()
            return author.id

    id1, id2 = await asyncio.gather(create_author(), create_author())
    assert id1 == id2