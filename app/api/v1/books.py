from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.file_parsers import parse_upload
from app.db.session import get_db
from app.models.user import User
from app.schemas.book import (
    BookCreate,
    BookFilters,
    BookListResponse,
    BookRead,
    BookUpdate,
    BulkImportResponse,
)

from app.services.book import BookService

router = APIRouter(prefix="/books", tags=["books"])


def get_book_service(session: AsyncSession = Depends(get_db)) -> BookService:
    return BookService(session)


@router.post("/", response_model=BookRead, status_code=status.HTTP_201_CREATED)
async def create_book(
    data: BookCreate,
    service: BookService = Depends(get_book_service),
    _: User = Depends(get_current_user),
):
    try:
        return await service.create(data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/", response_model=BookListResponse)
async def list_books(
    filters: BookFilters = Depends(),
    service: BookService = Depends(get_book_service),
    _: User = Depends(get_current_user),
):
    items, total = await service.list(filters)
    return BookListResponse(
        items=items,
        total=total,
        limit=filters.limit,
        offset=filters.offset,
    )


@router.post(
    "/import",
    response_model=BulkImportResponse,
    status_code=200,
    summary="Bulk import books from JSON or CSV file",
)
async def import_books(
    file: UploadFile = File(...),
    service: BookService = Depends(get_book_service),
    _: User = Depends(get_current_user),
) -> BulkImportResponse:
    """
    Accepts a .json or .csv file and imports books.
    Strategy: all-or-nothing — if at least one row is invalid,
    nothing is saved and a list of errors is returned with status 200.

    Why 200 and not 207 Multi-Status?
    We are all-or-nothing: either full success (imported > 0, errors = [])
    or full failure (imported = 0, errors != []). 207 implies partial success
    which never happens here, so 200 is the correct and simpler choice.
    """
    rows = await parse_upload(file)
    return await service.bulk_import(rows)


@router.get("/export", summary="Export all books as JSON or CSV")
async def export_books(
    format: str = Query("json", pattern="^(json|csv)$"),
    service: BookService = Depends(get_book_service),
    _: User = Depends(get_current_user),
) -> StreamingResponse:
    """
    Returns all books as a downloadable file.
    format=json (default) or format=csv.

    StreamingResponse streams content instead of buffering the full
    response in memory. For our scale the difference is small, but
    the pattern is correct for file downloads.
    """
    if format == "csv":
        content = await service.export_books_csv()
        media_type = "text/csv"
        filename = "books.csv"
    else:
        content = await service.export_books_json()
        media_type = "application/json"
        filename = "books.json"

    return StreamingResponse(
        content=iter([content]),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/{book_id}", response_model=BookRead)
async def get_book(
    book_id: UUID,
    service: BookService = Depends(get_book_service),
    _: User = Depends(get_current_user),
):
    try:
        return await service.get_by_id(book_id)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/{book_id}", response_model=BookRead)
async def update_book(
    book_id: UUID,
    data: BookUpdate,
    service: BookService = Depends(get_book_service),
    _: User = Depends(get_current_user),
):
    try:
        return await service.update(book_id, data)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(
    book_id: UUID,
    service: BookService = Depends(get_book_service),
    _: User = Depends(get_current_user),
):
    try:
        await service.delete(book_id)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
