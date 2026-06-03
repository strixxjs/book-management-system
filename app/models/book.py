import uuid

from sqlalchemy import (
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Book(Base, TimestampMixin):
    __tablename__ = "books"

    author_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("authors.id", ondelete="RESTRICT"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)

    genre: Mapped[str] = mapped_column(String(100), nullable=False)

    year: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    author: Mapped["Author"] = relationship(
        "Author",
        back_populates="books",
        lazy="raise",
    )

    __table_args__ = (
        UniqueConstraint("title", "author_id", name="uq_books_title_author"),
        Index("ix_books_author_id", "author_id"),
        Index("ix_books_genre", "genre"),
        Index("ix_books_year", "year"),
    )