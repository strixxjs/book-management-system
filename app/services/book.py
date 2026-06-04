import csv
import io
import json

from pydantic import ValidationError
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.author import AuthorRepository
from app.repositories.book import BookRepository
from app.schemas.book import (
    BookCreate,
    BookFilters,
    BookImportRow,
    BookRead,
    BulkImportResponse,
    BookUpdate,
    RowError,
)


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

    async def get_list(self, filters: BookFilters) -> tuple[list, int]:
        return await self._book_repo.get_list(
            title=filters.title,
            author_name=filters.author_name,
            genre=filters.genre.value if filters.genre else None,
            year_from=filters.year_from,
            year_to=filters.year_to,
            sort=filters.sort,
            limit=filters.limit,
            offset=filters.offset,
        )

    async def bulk_import(self, rows: list[dict]) -> BulkImportResponse:
        """
        Validates every row via BookImportRow (Pydantic) before any INSERT.
        Strategy: all-or-nothing - if any row is invalid, nothing is written.

        Why all-or-nothing:
        The file is treated as a single atomic unit. The caller gets a clear
        contract: either everything landed or nothing did. Best-effort with
        partial commits would need savepoints and a more complex response
        schema - out of scope here, and intentionally so.
        """
        errors: list[RowError] = []
        validated: list[BookImportRow] = []

        for i, raw in enumerate(rows, start=1):
            try:
                validated.append(BookImportRow.model_validate(raw))
            except ValidationError as exc:
                for e in exc.errors():
                    field = ".".join(str(loc) for loc in e["loc"]) if e["loc"] else None
                    errors.append(RowError(row=i, field=field, message=e["msg"]))

        if errors:
            return BulkImportResponse(imported=0, errors=errors)

        imported = 0
        for book_in in validated:
            try:
                await self.create(book_in)
                imported += 1
            except ValueError as exc:
                raise ValueError(f"Row {imported + 1}: {exc}") from exc

        return BulkImportResponse(imported=imported, errors=[])

    async def export_books_json(self) -> str:
        """
        Serialises all books to a JSON string using BookRead schema.
        The same schema is used by GET /books/{id}, so the export format
        is consistent with the REST API response.
        default=str handles UUID and datetime serialisation.
        """
        books = await self._book_repo.get_all_for_export()
        data = [
            BookRead.model_validate(b, from_attributes=True).model_dump() for b in books
        ]
        return json.dumps(data, ensure_ascii=False, default=str, indent=2)

    async def export_books_csv(self) -> str:
        """
        Serialises all books to a CSV string via io.StringIO.
        StringIO keeps everything in memory — no filesystem, no cleanup needed.
        Fields match the BookRead schema so the CSV is consistent with the API.
        """
        books = await self._book_repo.get_all_for_export()
        output = io.StringIO()
        fieldnames = ["id", "title", "author", "genre", "year", "created_at"]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for b in books:
            writer.writerow(
                {
                    "id": str(b.id),
                    "title": b.title,
                    "author": b.author.name if b.author else "",
                    "genre": b.genre or "",
                    "year": b.year or "",
                    "created_at": b.created_at.isoformat(),
                }
            )
        return output.getvalue()
