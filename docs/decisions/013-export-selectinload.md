# 013. Selectinload over joinedload for Export Query

## Status
Accepted

## Context
The export endpoint fetches every book together with its author so the
author name can appear in the output. SQLAlchemy offers two eager-loading
strategies for this kind of relationship:

**joinedload**: a single SQL query with a JOIN. The result set has one row
per book, but every row carries a full copy of the author columns. If the
same author wrote 200 books, their name and id are repeated 200 times on
the wire between PostgreSQL and the application.

**selectinload**: two separate SQL queries — first all books, then
`SELECT ... WHERE author_id IN (...)` for the authors that were actually
found. No column duplication.

## Decision
Use `selectinload(Book.author)` for the export query.

When the number of distinct authors (M) is much smaller than the number
of books (N), selectinload transfers less data. In an export scenario where
we load the entire table, that difference is meaningful. Two small queries
are also easier to reason about in EXPLAIN output than one wide JOIN.

## Consequences
Good:
- Less data transferred from the database when author cardinality is low
  relative to book count.
- Each query is simple and shows up cleanly in slow-query logs.

Bad:
- Two round trips to the database instead of one. For a small dataset the
  overhead is negligible, but it is worth noting.
- joinedload would be the better choice if we were paginating (small page
  size, high author cardinality per page) — we are not paginating here.

## Alternatives Considered
joinedload was not chosen for the export path for the reason above.
It remains a valid choice for paginated list queries where the page is
small and a JOIN does not produce significant duplication.