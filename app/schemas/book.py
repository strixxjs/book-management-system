from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, StringConstraints

from app.core.enums import Genre
from app.schemas.author import AuthorRead

MIN_YEAR = 1800


def _current_year() -> int:
    return datetime.now(timezone.utc).year


def _validate_year(value: int) -> int:
    upper = _current_year()
    if not (MIN_YEAR <= value <= upper):
        raise ValueError(f"year must be between {MIN_YEAR} and {upper}")
    return value


Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
AuthorName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
Year = Annotated[int, AfterValidator(_validate_year)]


class BookCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Title
    author: AuthorName
    genre: Genre
    year: Year


class BookUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Title | None = None
    author: AuthorName | None = None
    genre: Genre | None = None
    year: Year | None = None


class BookRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    genre: Genre
    year: int
    author: AuthorRead
    created_at: datetime
    updated_at: datetime