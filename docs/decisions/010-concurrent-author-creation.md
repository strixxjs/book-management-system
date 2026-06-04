# 010. Concurrent author creation handled by ON CONFLICT, not read-then-write

## Context
Creating a book find-or-creates its author by name. The naive way - SELECT, then
INSERT if nothing comes back - has a race: two concurrent requests for the same
new author both see nothing, both INSERT, and one hits the unique index. One
request errors, or you get duplicate authors if the index weren't there.

## Decision
get_or_create issues one statement:

    INSERT INTO authors (name) VALUES (:name)
    ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
    RETURNING ...

Atomic in the database. The conflict target is the unique index on name (008),
which ON CONFLICT (name) infers automatically. There is no separate SELECT, so
there is no window to lose.

## Why
- The database resolves the race, not application code. Both concurrent inserts
  return the same row; neither errors.
- DO UPDATE, not DO NOTHING. DO NOTHING ... RETURNING returns nothing on conflict,
  forcing a second SELECT. DO UPDATE SET name = EXCLUDED.name is a harmless no-op
  that makes RETURNING hand back the row every time.
- We considered try-INSERT / except IntegrityError / SELECT. It works, but in
  Postgres a failed statement aborts the whole transaction, requiring a SAVEPOINT
  (begin_nested) to recover. One ON CONFLICT statement is simpler for the same
  result.

## Cost we accept
- Postgres-specific. ON CONFLICT and EXCLUDED aren't portable SQL. We are already
  committed to Postgres (002), so this is not a new constraint.
- DO UPDATE writes a row version on every call even when nothing changes (MVCC).
  At our write volume this is noise. updated_at is not in the SET clause, so its
  value stays unchanged on a no-op conflict.