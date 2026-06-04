async def get_all_for_export(self) -> list[Book]:
    """
    Returns all books with author (joined load).
No pagination - for export only.
ORDER BY created_at for deterministic order in the file.
    """

    result = await self._session.execute(
        select(Book)
        .options(selectinload(Book.author))
        .order_by(Book.created_at)
    )
    return list(result.scalars().all())