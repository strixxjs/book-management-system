import pytest

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
