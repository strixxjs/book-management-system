from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.author import AuthorRepository
from app.repositories.book import BookRepository
from app.schemas.book import BookCreate, BookUpdate, BookFilters


class BookService:
    def __init__(self, session: AsyncSession) -> None:
        self._book_repo = BookRepository(session)
        self._author_repo = AuthorRepository(session)

    async def create(self, data: BookCreate):
        author = await self._author_repo.get_or_create(data.author)
        try:
            return await self._book_repo.create(
                author_id=author.id,
                title=data.title,
                genre=data.genre.value,
                year=data.year,
            )
        except IntegrityError:
            raise ValueError("Book with this title already exists for this author")

    async def get_by_id(self, book_id: UUID):
        book = await self._book_repo.get_by_id(book_id)
        if book is None:
            raise LookupError(f"Book {book_id} not found")
        return book

    async def update(self, book_id: UUID, data: BookUpdate):
        book = await self._book_repo.get_by_id(book_id)
        if book is None:
            raise LookupError(f"Book {book_id} not found")

        fields = data.model_dump(exclude_unset=True)

        if "author" in fields:
            author = await self._author_repo.get_or_create(fields.pop("author"))
            fields["author_id"] = author.id

        if "genre" in fields:
            fields["genre"] = fields["genre"].value

        return await self._book_repo.update(book, fields)

    async def delete(self, book_id: UUID) -> None:
        book = await self._book_repo.get_by_id(book_id)
        if book is None:
            raise LookupError(f"Book {book_id} not found")
        await self._book_repo.delete(book)

    async def list(self, filters: BookFilters) -> tuple[list, int]:
        return await self._book_repo.list(
            title=filters.title,
            author_name=filters.author_name,
            genre=filters.genre.value if filters.genre else None,
            year_from=filters.year_from,
            year_to=filters.year_to,
            sort=filters.sort,
            limit=filters.limit,
            offset=filters.offset,
        )