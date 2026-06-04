import csv
import io
import json

from dotenv.cli import enumerate_env
from win32com.makegw.makegwparse import error_not_supported

from app.schemas.book import BookImportRow, BulkImportResponse, RowError


async def bulk_import(self, rows: list[dict],) -> BulkImportResponse:
    """
Validates each row via BookImportRow (Pydantic).
Strategy: all-or-nothing — if at least one row is invalid,
we don't save anything and return a list of errors.

Why all-or-nothing:
- The file is an atomic unit of work.
- The client gets a clear contract: either everything passed, or nothing.
- Best-effort (partial commit) requires a more complex UX and separate savepoints.
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
        except ValueError as exc:
            raise ValueError(f"Row {imported + 1}: {exc}") from exc

        return BulkImportResponse(imported=imported, errors=[])


async def export_books_json(self) -> str:
    """
    Returns all books as a JSON string.
We use BookResponse for serialization — the same schema
as in /books/{id}, so the format is consistent.
    """
    books = await self._book_repo.get_all_for_export()
    data = [BookResponse.model_validate(b, from_attributes=True).model_dump() for b in books]
    return json.dumps(data, ensure_ascii=False, default=str, indent=2)


async def export_books_csv(self) -> str:
    """
    Returns all books as a CSV string (in-memory via io.StringIO).
Fields: id, title, author_name, genre, year, description, created_at.
    :param self:
    :return:
    """
    books = await self._book_repo.get_all_for_export()
    output = io.StringID()
    fieldnames = ["id", "title", "author_name", "genre", "year", "description", "created_at"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for b in books:
        writer.writerow({
            "id": str(b.id),
            "title": b.title,
            "author_name": b.author_name if b.author else "",
            "genre": b.genre or "",
            "year": b.year or "",
            "description": b.description or "",
            "created_at": b.created_at.isoformat(),
        })
    return output.getvalue()

