from uuid import UUID

from sqlalchemy import select, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.book import Book
from app.models.author import Author


SORT_FIELDS = {
    "title": Book.title,
    "year": Book.year,
    "created_at": Book.created_at,
}


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
            select(Book).options(selectinload(Book.author)).where(Book.id == book_id)
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

    async def list(
        self,
        title: str | None = None,
        author_name: str | None = None,
        genre: str | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
        sort: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Book], int]:
        query = select(Book).options(selectinload(Book.author)).join(Book.author)

        if title:
            query = query.where(Book.title.ilike(f"%{title}%"))
        if author_name:
            query = query.where(Author.name.ilike(f"%{author_name}%"))
        if genre:
            query = query.where(Book.genre == genre)
        if year_from:
            query = query.where(Book.year >= year_from)
        if year_to:
            query = query.where(Book.year <= year_to)

        sort_column = SORT_FIELDS.get(sort, Book.created_at)
        query = query.order_by(asc(sort_column), asc(Book.id))

        from sqlalchemy import func, select as sa_select

        count_query = sa_select(func.count()).select_from(query.subquery())
        total = (await self.session.execute(count_query)).scalar_one()

        query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        return result.scalars().all(), total

    async def get_all_for_export(self) -> list[Book]:
        """
        Returns all books with their author eagerly loaded.
        Uses selectinload instead of joinedload: when author cardinality
        is low relative to book count, two queries transfer less data
        than one wide JOIN with repeated author columns.
        Ordered by created_at for deterministic output in the exported file.
        """
        result = await self.session.execute(
            select(Book).options(selectinload(Book.author)).order_by(Book.created_at)
        )
        return list(result.scalars().all())
