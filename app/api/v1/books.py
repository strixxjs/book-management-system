from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.book import (
    BookCreate,
    BookFilters,
    BookRead,
    BookUpdate,
    BookListResponse,
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
