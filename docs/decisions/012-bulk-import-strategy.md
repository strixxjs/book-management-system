# 012. Bulk Import Strategy - All-or-Nothing

## Status
Accepted

## Context
POST /books/import must process files with tens to hundreds of lines
Question: What to do if some of the lines are invalid?

## Decision
All-or-nothing: validate all rows before any INSERT
If at least one line does not pass pydantic validation, we return a list of errors, we do not save anything

## Consequences
Good:
- Simple implementation — one transaction, no savepoints.
- Predictable contract: the file either lands completely or not at all.
- Error list covers the whole file, so the caller can fix everything in
  one round trip.

Bad:
- Painful for large files. One bad row in 10 000 rejects everything.
  At that scale the right answer is an async job (Celery, ARQ) with a
  status-polling endpoint and row-level error tracking. That is out of
  scope here and the trade-off is intentional.

## Alternatives Considered
Best-effort with partial commit was considered and explicitly rejected for
this scope. It is the correct production choice for bulk ETL pipelines, but
it adds enough complexity (savepoints, partial-success HTTP semantics,
richer response schema) that it would obscure the rest of the codebase
without adding meaningful signal for a take-home review.