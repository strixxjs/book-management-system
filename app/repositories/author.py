from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.author import Author


class AuthorRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create(self, name: str) -> Author:
        insert_stmt = pg_insert(Author).values(name=name)
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=[Author.name],
            set_={"name": insert_stmt.excluded.name},
        ).returning(Author)
        result = await self.session.execute(upsert_stmt)
        return result.scalar_one()
