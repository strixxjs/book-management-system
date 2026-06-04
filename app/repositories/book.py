from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.book import Book
from app.models.author import Author


class BookRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, author_id: UUID, title: str, genre: str, year: int) -> Book:
        book = Book(author_id=author_id, title=title, genre=genre, year=year)
        self.session.add(book)
        await self.session.flush()
        await self.session.refresh(book, ["author"])
        return book

    async def get_by_id(self, book_id: UUID) -> Book | None:
        result = await self.session.execute(
            select(Book)
            .options(selectinload(Book.author))
            .where(Book.id == book_id)
        )
        return result.scalar_one_or_none()

    async def update(self, book: Book, fields: dict) -> Book:
        for key, value in fields.items():
            setattr(book, key, value)
        await self.session.flush()
        return await self.get_by_id(book.id)

    async def delete(self, book: Book) -> None:
        await self.session.delete(book)
        await self.session.flush()