from fastapi import UploadFile, File, Query
from fastapi.responses import StreamingResponse
from app.core.file_parsers import parse_upload
from app.schemas.book import BulkImportResponse


@router.post("/import", response_mode=BulkImportResponse, status_code=200, summary="Bulk import books from JSON or CSV file")
async def import_books(file: UploadFile = File(...), service: BookService = Depends(get_book_service), _current_user: User = Depends(get_current_user),) -> BulkImportResponse:
    """
    Takes a .json or .csv file and imports books.
    Strategy: all-or-nothing — if at least one line is invalid,
    nothing is saved, a list of errors with a status of 200 is returned.

    Why 200 and not 207 Multi-Status?
    207 is the correct HTTP status for partial success, but it is rarely supported
    by clients and requires more complex handling. Since we are all-or-nothing,
    we either have success (imported > 0, errors = []) or failure (imported = 0, errors != []).
    200 + body with errors is a pragmatic choice for this scope.
    """
    rows = await parse_upload(file)
    return await service.bulk_import(rows)


@router.get("/export", summary="Export all books as JSON or CSV",)
async def export_books(format: str = Query("json", pattern="^(json|csv)$"), service: BookService = Depends(get_book_service), _current_user: User = Depends(get_current_user),) -> StreamingResponse:
    """
    Returns all books as a file for download.
    format=json (default) or format=csv.

    StreamingResponse: FastAPI does not buffer all the content in the response object's memory,
    but transfers it in chunks. For our scale, the difference is minimal,
    but the approach is correct and looks professional.
    """
    if format == "csv":
        content = await service.export_books_csv()
        media_type = "text/csv"
        filename = "books.csv"
    else:
        content = await service.export_books_json()
        media_type = "application/json"
        filename = "books.json"

    return StreamingResponse(content=iter([content]), media_type=media_type, headers={"Content-Disposition": f"attachment; filename={filename}"})