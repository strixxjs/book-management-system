# 011. Integration tests run against real Postgres with rollback-per-test isolation

## Context
The repository layer relies on ON CONFLICT, a unique index as the conflict
arbiter, and RETURNING - none of which behave the same on SQLite, and some don't
exist there. We need tests that exercise the actual database we ship against.

## Decision
Tests run against a dedicated bookdb_test Postgres database (same Docker Compose
instance). Each test runs inside a transaction that is rolled back at teardown via
join_transaction_mode="create_savepoint". Schema is created with create_all once
per test (idempotent); data never persists between tests.

## Why
- A get_or_create test on SQLite would prove nothing about the code that ships.
  Testing against the same engine we run in production is the point.
- Rollback-per-test is fast: no truncation, no drop/recreate, just ROLLBACK.
  The savepoint mode lets code inside the test flush and even commit without
  escaping the outer transaction.

## Cost we accept
- Tests need a Postgres running. TEST_DATABASE_URL gates it: if unset, the suite
  skips integration tests cleanly.
- Schema is built with create_all, not by running migrations. Model/migration
  drift is caught separately by running alembic upgrade head on a clean DB.
  Running migrations in the fixture would close the gap at the cost of complexity
  we judged not worth it here.
- We did not write a concurrent creation test (two sessions racing on the same
  author). A deterministic test can't prove true concurrency; a probabilistic one
  needs committed transactions across connections and is flaky. The correctness
  argument lives in the database's atomic upsert (010). If the signal is wanted
  later: asyncio.gather over two separate sessions, assert one row, no error,
  marked explicitly as non-deterministic.