import pytest
from pydantic import ValidationError

from app.core.enums import Genre
from app.schemas import book as book_schema
from app.schemas.book import BookCreate, BookUpdate


def _valid(**overrides):
    data = {
        "title": "1984",
        "author": "George Orwell",
        "genre": "fiction",
        "year": 1949,
    }
    data.update(overrides)
    return data


def test_year_rejects_below_min():
    with pytest.raises(ValidationError):
        BookCreate(**_valid(year=1799))


def test_year_accepts_min_boundary():
    assert BookCreate(**_valid(year=1800)).year == 1800


def test_year_rejects_future(monkeypatch):
    monkeypatch.setattr(book_schema, "_current_year", lambda: 2025)
    with pytest.raises(ValidationError):
        BookCreate(**_valid(year=2026))


def test_year_uses_current_year_dynamically(monkeypatch):
    monkeypatch.setattr(book_schema, "_current_year", lambda: 2050)
    assert BookCreate(**_valid(year=2050)).year == 2050


def test_title_whitespace_only_rejected():
    with pytest.raises(ValidationError):
        BookCreate(**_valid(title="   "))


def test_genre_invalid_rejected():
    with pytest.raises(ValidationError):
        BookCreate(**_valid(genre="cookbook"))


def test_update_dump_excludes_unset():
    payload = BookUpdate(genre="fiction")
    dumped = payload.model_dump(exclude_unset=True)
    assert set(dumped.keys()) == {"genre"}  # title/author/year missing
    assert dumped["genre"] is Genre.FICTION
